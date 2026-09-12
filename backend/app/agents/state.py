from __future__ import annotations

import datetime as dt
from typing import Optional, TypedDict


class DocChunk(TypedDict):
    text: str
    filename: str
    score: float


class Citation(TypedDict):
    id: str  # short, stable id used to de-duplicate across agents, e.g. "d1", "s2"
    source_type: str  # "document" | "structured" | "vision"
    label: str  # human-readable: filename, or "PUMP-104 · 2026-08-29"
    snippet: str  # the actual retrieved text/row this citation backs


class TraceEntry(TypedDict):
    agent: str
    action: str
    detail: str
    timestamp: dt.datetime


def make_trace_entry(agent: str, action: str, detail: str) -> TraceEntry:
    """Every agent node should append via this helper rather than a raw
    dict literal, so the timestamp field required by the API response
    schema (models/schemas.py::TraceStep) is never accidentally missing."""
    return {"agent": agent, "action": action, "detail": detail, "timestamp": dt.datetime.now(dt.UTC)}


class WorkbenchState(TypedDict):
    # --- input ---
    session_id: str
    owner_id: str
    query: str
    image_base64: Optional[str]

    # --- supervisor decision ---
    needs_vision: bool
    needs_structured: bool
    route: list[str]

    # --- per-agent outputs ---
    doc_chunks: list[DocChunk]
    doc_answer: Optional[str]
    vision_answer: Optional[str]
    structured_answer: Optional[str]

    # --- citations, code-computed (never trust the LLM alone to format these) ---
    citations: list[Citation]

    # --- final ---
    answer: Optional[str]
    trace: list[TraceEntry]