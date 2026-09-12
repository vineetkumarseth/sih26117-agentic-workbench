from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="operator")  # operator | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(64))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow)

    owner: Mapped["User"] = relationship()


class AuditLog(Base):
    """
    Append-only trail of everything the system did: who asked what, which
    agents fired, what the guardrail layer decided, and what went back to
    the user. This is the concrete answer to "how do we audit an AI that
    touches confidential plant data" — every row is queryable via
    GET /api/audit (admin-only).
    """

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    timestamp: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(32))  # login | query | upload | guardrail_block | error
    route: Mapped[str | None] = mapped_column(String(64), nullable=True)  # which agent(s) handled it
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
