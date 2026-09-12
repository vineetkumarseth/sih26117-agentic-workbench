from __future__ import annotations

from collections import Counter
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import AuditLog, Document, User
from app.db.session import get_db
from app.models.schemas import AdminStatsOut, DocumentAdminOut, UserAdminOut, UserUpdate
from app.retrieval import vector_store
from app.security.auth import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])
settings = get_settings()


@router.get("/stats", response_model=AdminStatsOut)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Aggregate counters for the admin dashboard's overview tab. Reads
    are cheap (COUNT/SUM queries, no full table scans into Python) so this
    is safe to poll on a timer from the frontend."""
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    active_users = (
        await db.execute(select(func.count()).select_from(User).where(User.is_active.is_(True)))
    ).scalar_one()
    total_documents = (await db.execute(select(func.count()).select_from(Document))).scalar_one()
    total_chunks = (await db.execute(select(func.coalesce(func.sum(Document.chunk_count), 0)))).scalar_one()

    total_queries = (
        await db.execute(select(func.count()).select_from(AuditLog).where(AuditLog.event_type == "query"))
    ).scalar_one()
    total_blocked = (
        await db.execute(select(func.count()).select_from(AuditLog).where(AuditLog.event_type == "guardrail_block"))
    ).scalar_one()
    total_uploads = (
        await db.execute(select(func.count()).select_from(AuditLog).where(AuditLog.event_type == "upload"))
    ).scalar_one()

    route_rows = (
        await db.execute(select(AuditLog.route).where(AuditLog.event_type == "query"))
    ).scalars().all()
    agent_usage: Counter[str] = Counter()
    for route in route_rows:
        if not route:
            continue
        for agent in route.split(","):
            agent = agent.strip()
            if agent:
                agent_usage[agent] += 1

    return AdminStatsOut(
        total_users=total_users,
        active_users=active_users,
        total_documents=total_documents,
        total_chunks=int(total_chunks or 0),
        total_queries=total_queries,
        total_blocked=total_blocked,
        total_uploads=total_uploads,
        agent_usage=dict(agent_usage),
        mock_llm=settings.MOCK_LLM,
        ollama_text_model=settings.OLLAMA_TEXT_MODEL,
        ollama_vision_model=settings.OLLAMA_VISION_MODEL,
        embedding_model=settings.EMBEDDING_MODEL,
        qdrant_collection=settings.QDRANT_COLLECTION,
    )


@router.get("/users", response_model=list[UserAdminOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    result = await db.execute(select(User).order_by(User.created_at.asc()))
    return [
        UserAdminOut(id=u.id, username=u.username, role=u.role, is_active=u.is_active, created_at=u.created_at)
        for u in result.scalars().all()
    ]


@router.patch("/users/{user_id}", response_model=UserAdminOut)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Toggle a user's active status or change their role. An admin can't
    deactivate or demote their own account through this endpoint — that
    would be an easy way to accidentally lock yourself out with no other
    admin left to undo it."""
    if user_id == admin.id and (payload.is_active is False or (payload.role and payload.role != "admin")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can't deactivate or demote your own account.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role is not None:
        user.role = payload.role

    await db.commit()
    await db.refresh(user)
    return UserAdminOut(id=user.id, username=user.username, role=user.role, is_active=user.is_active, created_at=user.created_at)


@router.get("/documents", response_model=list[DocumentAdminOut])
async def list_all_documents(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Unlike GET /api/documents (which only returns the caller's own
    uploads), this returns every document across every user — the whole
    point of an admin view."""
    result = await db.execute(
        select(Document, User.username)
        .join(User, Document.owner_id == User.id)
        .order_by(Document.uploaded_at.desc())
    )
    return [
        DocumentAdminOut(
            id=d.id,
            filename=d.filename,
            content_type=d.content_type,
            chunk_count=d.chunk_count,
            uploaded_at=d.uploaded_at,
            owner_username=owner_username,
        )
        for d, owner_username in result.all()
    ]


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Deletes the DB row, the stored file on disk, and every indexed
    chunk in Qdrant (including any vision-caption chunk derived from it)
    so a removed document is actually gone from retrieval, not just
    hidden from the document list."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    vector_store.delete_document(document_id)

    for stored_file in Path(settings.UPLOAD_DIR).glob(f"{document_id}.*"):
        stored_file.unlink(missing_ok=True)

    await db.delete(doc)
    await db.commit()
