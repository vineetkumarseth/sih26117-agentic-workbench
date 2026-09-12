from __future__ import annotations

import hashlib
import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Document, User
from app.db.session import get_db
from app.models.schemas import DocumentOut
from app.retrieval import vector_store
from app.retrieval.chunking import chunk_text
from app.security.audit import log_event
from app.security.auth import get_current_user
from app.security.rate_limit import limiter

router = APIRouter(prefix="/api/documents", tags=["documents"])
settings = get_settings()

_SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]")


def _sanitize_filename(name: str) -> str:
    """Strip directory components and anything but a conservative
    character set, so a crafted filename can't path-traverse or collide
    with something on disk."""
    base = os.path.basename(name)
    base = _SAFE_NAME.sub("_", base)
    return base[-200:] or "upload"


def _extract_text(path: Path, content_type: str) -> str:
    if content_type == "application/pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8", errors="ignore")


_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_document(
    request: Request,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.allowed_upload_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Extension '{ext}' not allowed. Allowed: {settings.allowed_upload_extensions}",
        )

    raw = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(raw) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.MAX_UPLOAD_MB} MB limit",
        )
    if len(raw) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    sha256 = hashlib.sha256(raw).hexdigest()

    # If this exact content is already ingested for this user, don't
    # index it again -- re-uploading the same file (easy to do by
    # accident) previously created a second, third, fourth... copy of the
    # same chunks in Qdrant, surfacing as multiple "different" citations
    # for what was really one source.
    existing = await db.execute(
        select(Document).where(Document.owner_id == current_user.id, Document.sha256 == sha256)
    )
    existing_doc = existing.scalar_one_or_none()
    if existing_doc is not None:
        return DocumentOut(
            id=existing_doc.id,
            filename=existing_doc.filename,
            content_type=existing_doc.content_type,
            chunk_count=existing_doc.chunk_count,
            uploaded_at=existing_doc.uploaded_at,
        )

    safe_name = _sanitize_filename(file.filename or "upload")
    document_id = str(uuid.uuid4())
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    # Store under a generated id, never the raw client-supplied name --
    # avoids overwrite races and keeps the sanitized name as metadata only.
    stored_path = Path(settings.UPLOAD_DIR) / f"{document_id}{ext}"
    stored_path.write_bytes(raw)

    content_type = _CONTENT_TYPES.get(ext, "application/octet-stream")
    sha256 = hashlib.sha256(raw).hexdigest()

    chunk_count = 0
    if ext in (".pdf", ".txt", ".md"):
        text = _extract_text(stored_path, content_type)
        chunks = chunk_text(text)
        chunk_count = vector_store.add_chunks(
            document_id=document_id,
            owner_id=current_user.id,
            filename=safe_name,
            chunks=chunks,
            source="document",
        )
    # Image uploads (.png/.jpg/.jpeg) are stored but indexed lazily: they
    # get embedded into the knowledge base the first time the vision
    # agent looks at them in a chat turn (see agents/vision_agent.py),
    # rather than being captioned automatically at upload time.

    doc = Document(
        id=document_id,
        owner_id=current_user.id,
        filename=safe_name,
        content_type=content_type,
        sha256=sha256,
        chunk_count=chunk_count,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    await log_event(
        db,
        event_type="upload",
        user_id=current_user.id,
        username=current_user.username,
        detail=f"{safe_name} ({chunk_count} chunks)",
        allowed=True,
        client_ip=request.client.host if request.client else None,
    )

    return DocumentOut(
        id=doc.id,
        filename=doc.filename,
        content_type=doc.content_type,
        chunk_count=doc.chunk_count,
        uploaded_at=doc.uploaded_at,
    )


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).where(Document.owner_id == current_user.id).order_by(Document.uploaded_at.desc())
    )
    docs = result.scalars().all()
    return [
        DocumentOut(
            id=d.id, filename=d.filename, content_type=d.content_type, chunk_count=d.chunk_count, uploaded_at=d.uploaded_at
        )
        for d in docs
    ]
