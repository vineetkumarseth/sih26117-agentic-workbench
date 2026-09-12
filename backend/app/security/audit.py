from __future__ import annotations

import hashlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


def hash_content(text: str) -> str:
    """
    We log a SHA-256 hash of message content rather than the raw text.
    That's enough to prove *that* a specific input was processed (you can
    recompute the hash from the original document/query to verify) without
    the audit table itself becoming a second copy of confidential data.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def log_event(
    db: AsyncSession,
    *,
    event_type: str,
    user_id: str | None = None,
    username: str | None = None,
    route: str | None = None,
    input_text: str | None = None,
    detail: str | None = None,
    allowed: bool = True,
    client_ip: str | None = None,
) -> None:
    entry = AuditLog(
        event_type=event_type,
        user_id=user_id,
        username=username,
        route=route,
        input_hash=hash_content(input_text) if input_text else None,
        detail=detail,
        allowed=allowed,
        client_ip=client_ip,
    )
    db.add(entry)
    await db.commit()
