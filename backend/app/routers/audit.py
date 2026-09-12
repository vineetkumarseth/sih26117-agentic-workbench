from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog, User
from app.db.session import get_db
from app.models.schemas import AuditEntryOut
from app.security.auth import require_admin

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditEntryOut])
async def list_audit_entries(
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    result = await db.execute(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit))
    entries = result.scalars().all()
    return [
        AuditEntryOut(
            id=e.id,
            timestamp=e.timestamp,
            username=e.username,
            event_type=e.event_type,
            route=e.route,
            allowed=e.allowed,
            detail=e.detail,
            client_ip=e.client_ip,
        )
        for e in entries
    ]
