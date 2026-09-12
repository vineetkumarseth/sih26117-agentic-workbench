"""
Records what each agent did for a given chat turn, so the frontend's
Agent Trace panel can show "Supervisor routed to Document + Vision agents
at 10:42:03, Document agent retrieved 3 chunks from inspection_report.pdf"
rather than a black-box answer.

This is intentionally self-contained (an in-memory + in-request list, no
extra service required) so the trace panel works out of the box. If
LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are set in .env, each trace is
additionally pushed to Langfuse for cross-session observability —
best-effort, and never allowed to break a chat request if Langfuse is
unreachable.
"""
from __future__ import annotations

import datetime as dt
import logging

from app.config import get_settings

logger = logging.getLogger("workbench.trace")
settings = get_settings()

_langfuse_client = None
_langfuse_init_attempted = False


def _get_langfuse():
    global _langfuse_client, _langfuse_init_attempted
    if _langfuse_init_attempted:
        return _langfuse_client
    _langfuse_init_attempted = True
    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        return None
    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST or "https://cloud.langfuse.com",
        )
        logger.info("Langfuse observability export enabled.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Langfuse init failed (%s); continuing without export.", exc)
        _langfuse_client = None
    return _langfuse_client


class Trace:
    def __init__(self, session_id: str, query: str) -> None:
        self.session_id = session_id
        self.query = query
        self.steps: list[dict] = []

    def add(self, agent: str, action: str, detail: str) -> None:
        self.steps.append(
            {
                "agent": agent,
                "action": action,
                "detail": detail,
                "timestamp": dt.datetime.now(dt.UTC),
            }
        )

    def export(self) -> None:
        client = _get_langfuse()
        if client is None:
            return
        try:
            trace = client.trace(name="workbench-chat", session_id=self.session_id, input=self.query)
            for step in self.steps:
                trace.span(name=f"{step['agent']}:{step['action']}", output=step["detail"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Langfuse export failed (%s); trace was still logged locally.", exc)
