from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field, field_validator


# --- Auth ---------------------------------------------------------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: str = "operator"

    @field_validator("role")
    @classmethod
    def _role_valid(cls, v: str) -> str:
        if v not in ("operator", "admin"):
            raise ValueError("role must be 'operator' or 'admin'")
        return v


class UserOut(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool


# --- Chat / agents --------------------------------------------------------
class TraceStep(BaseModel):
    agent: str
    action: str
    detail: str
    timestamp: dt.datetime


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(min_length=1, max_length=128)
    image_base64: str | None = Field(default=None, description="Optional base64-encoded image for the vision agent")

    @field_validator("message")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class CitationOut(BaseModel):
    id: str
    source_type: str
    label: str
    snippet: str

    
class ChatResponse(BaseModel):
    answer: str
    route: list[str]
    trace: list[TraceStep]
    citations: list[CitationOut] = []
    blocked: bool = False
    block_reason: str | None = None


# --- Documents --------------------------------------------------------
class DocumentOut(BaseModel):
    id: str
    filename: str
    content_type: str
    chunk_count: int
    uploaded_at: dt.datetime


# --- Admin --------------------------------------------------------------
class UserAdminOut(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool
    created_at: dt.datetime


class UserUpdate(BaseModel):
    is_active: bool | None = None
    role: str | None = None

    @field_validator("role")
    @classmethod
    def _role_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in ("operator", "admin"):
            raise ValueError("role must be 'operator' or 'admin'")
        return v


class DocumentAdminOut(BaseModel):
    id: str
    filename: str
    content_type: str
    chunk_count: int
    uploaded_at: dt.datetime
    owner_username: str | None = None


class AdminStatsOut(BaseModel):
    total_users: int
    active_users: int
    total_documents: int
    total_chunks: int
    total_queries: int
    total_blocked: int
    total_uploads: int
    agent_usage: dict[str, int]
    mock_llm: bool
    ollama_text_model: str
    ollama_vision_model: str
    embedding_model: str
    qdrant_collection: str


# --- Audit --------------------------------------------------------------
class AuditEntryOut(BaseModel):
    id: str
    timestamp: dt.datetime
    username: str | None
    event_type: str
    route: str | None
    allowed: bool
    detail: str | None
    client_ip: str | None
