"""
Structured-data sub-agent: answers questions grounded in tabular plant
records — equipment readings, inspection logs, threshold breaches —
rather than free-text documents. In this scaffold it reads a sample CSV
(app/seed_data/equipment_readings.csv, standing in for a historian/SCADA
export). Swap `_load_rows()` for a real query against your plant's data
historian and the rest of the agent — filtering, LLM summarization,
tracing — keeps working unchanged.

This lives under app/seed_data/ rather than backend/data/ deliberately:
backend/data/ is wipeable runtime state (uploads, the SQLite DB, the
vector store — see backend/.gitignore), and this sample dataset ships
with the project rather than being generated at runtime, so it needs to
survive a "clear my local data" reset instead of being deleted by one.
"""
from __future__ import annotations

import csv
from pathlib import Path

from app.agents.state import WorkbenchState, make_trace_entry
from app.llm.ollama_client import get_llm_client

_CSV_PATH = Path(__file__).resolve().parents[1] / "seed_data" / "equipment_readings.csv"

_SYSTEM_PROMPT = (
    "You are the structured-data agent inside an on-premise industrial assistant. "
    "You are given rows from a plant readings log as CSV, each labelled with a "
    "citation tag like [s1]. Answer using only these rows. When a sentence relies "
    "on a specific row, end it with that row's tag, e.g. 'Pressure reached 181 psi "
    "on 2026-08-29 [s3].' Use a tag only when you actually used that row."
)


def _load_rows() -> list[dict]:
    if not _CSV_PATH.exists():
        return []
    with _CSV_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _filter_rows(query: str, rows: list[dict]) -> list[dict]:
    tokens = [t.lower() for t in query.replace("-", " ").split() if len(t) > 2]
    if not tokens:
        return rows[:10]

    def matches(row: dict) -> bool:
        haystack = " ".join(row.values()).lower()
        return any(tok in haystack for tok in tokens)

    filtered = [r for r in rows if matches(r)]
    return filtered or rows[:5]  # fall back to a small sample rather than nothing


async def structured_agent_node(state: WorkbenchState) -> dict:
    if not state.get("needs_structured"):
        trace = state["trace"] + [
            make_trace_entry("structured_agent", "skip", "query didn't reference logs/readings/records")
        ]
        return {"structured_answer": None, "trace": trace}

    rows = _filter_rows(state["query"], _load_rows())
    if not rows:
        trace = state["trace"] + [
            make_trace_entry("structured_agent", "query", "no matching rows in equipment_readings.csv")
        ]
        return {"structured_answer": "No matching structured records were found.", "trace": trace}

    csv_snippet = "\n".join(",".join(row.values()) for row in rows[:15])
    header = "equipment_id,date,reading_type,value,unit,notes"

    # Same principle as document_agent: citations are built here from the
    # rows that actually matched, not left to the LLM to remember or
    # reformat — the [sN] tags handed to the model are exactly these ids.
    citations = [
        {
            "id": f"s{i + 1}",
            "source_type": "structured",
            "label": f"{row['equipment_id']} · {row['date']}",
            "snippet": f"{row['reading_type']}: {row['value']} {row['unit']} — {row['notes']}",
        }
        for i, row in enumerate(rows[:15])
    ]
    tagged_snippet = "\n".join(f"[{c['id']}] {','.join(row.values())}" for c, row in zip(citations, rows[:15], strict=True))

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"{header}\n{tagged_snippet}\n\nQuestion: {state['query']}"},
    ]
    answer = await get_llm_client().chat(messages)

    trace = state["trace"] + [
        make_trace_entry("structured_agent", "query+answer", f"matched {len(rows)} row(s) in equipment_readings.csv")
    ]
    return {"structured_answer": answer, "citations": state["citations"] + citations, "trace": trace}