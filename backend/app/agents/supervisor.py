"""
Supervisor node: the entry point of the graph. Decides which specialist
agents a given turn needs, before any of them run.

Vision routing is deterministic (an image was attached, or it wasn't).
Structured-data routing uses a small keyword heuristic tuned for the
plant-maintenance domain this PS targets (readings, logs, dates,
thresholds). A real deployment would likely swap this for an LLM-based
intent classifier — the hook is exactly here, in `_needs_structured` — but
a heuristic is faster, free, and fully deterministic for a live demo,
where "why did it route there" needs a one-line answer.
"""
from __future__ import annotations

import re

from app.agents.state import WorkbenchState, make_trace_entry

_STRUCTURED_HINTS = re.compile(
    r"\b(reading|log|record|threshold|value|sensor|last \d+ days|history|trend|"
    r"pressure|temperature|vibration|inspection date|batch)",
    re.I,
)


def supervisor_node(state: WorkbenchState) -> dict:
    needs_vision = bool(state.get("image_base64"))
    needs_structured = bool(_STRUCTURED_HINTS.search(state["query"]))

    route = ["document_agent"]
    if needs_vision:
        route.append("vision_agent")
    if needs_structured:
        route.append("structured_agent")

    detail = f"needs_vision={needs_vision}, needs_structured={needs_structured}, route={route}"
    return {
        "needs_vision": needs_vision,
        "needs_structured": needs_structured,
        "route": route,
        "trace": state["trace"] + [make_trace_entry("supervisor", "classify", detail)],
    }
