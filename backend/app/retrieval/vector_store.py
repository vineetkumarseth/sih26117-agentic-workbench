from __future__ import annotations

import os
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

from app.config import get_settings
from app.retrieval.embeddings import embed_query, embed_texts, embedding_dim

settings = get_settings()

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    """
    QDRANT_URL unset (the default) -> embedded mode: Qdrant runs in-process
    and persists to QDRANT_LOCAL_PATH on disk. No server, no open port,
    nothing to secure on the network — the simplest possible answer to
    "does document data ever leave this machine".

    Set QDRANT_URL (e.g. http://qdrant:6333 from docker-compose.yml) to
    point at a real Qdrant server for a multi-instance deployment.
    """
    global _client
    if _client is not None:
        return _client
    if settings.QDRANT_URL:
        _client = QdrantClient(url=settings.QDRANT_URL)
    else:
        os.makedirs(settings.QDRANT_LOCAL_PATH, exist_ok=True)
        _client = QdrantClient(path=settings.QDRANT_LOCAL_PATH)
    _ensure_collection(_client)
    return _client


def _ensure_collection(client: QdrantClient) -> None:
    if not client.collection_exists(settings.QDRANT_COLLECTION):
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=embedding_dim(), distance=Distance.COSINE),
        )


def add_chunks(*, document_id: str, owner_id: str, filename: str, chunks: list[str], source: str = "document") -> int:
    if not chunks:
        return 0
    client = get_client()
    vectors = embed_texts(chunks)
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "document_id": document_id,
                "owner_id": owner_id,
                "filename": filename,
                "text": chunk,
                "source": source,  # "document" | "vision_caption"
            },
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points)
    return len(points)


def delete_document(document_id: str) -> None:
    """Remove every chunk (including a vision caption chunk, if any) that
    belongs to this document_id. Used by the admin document-delete
    endpoint so a removed document actually stops being retrievable,
    rather than just disappearing from the SQL row."""
    client = get_client()
    client.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]),
    )


def search(*, query: str, owner_id: str, top_k: int = 5) -> list[dict]:
    client = get_client()
    vector = embed_query(query)
    results = client.query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=vector,
        limit=top_k,
        query_filter=Filter(must=[FieldCondition(key="owner_id", match=MatchValue(value=owner_id))]),
    )
    return [
        {"text": p.payload.get("text", ""), "filename": p.payload.get("filename", ""), "score": p.score}
        for p in results.points
    ]
