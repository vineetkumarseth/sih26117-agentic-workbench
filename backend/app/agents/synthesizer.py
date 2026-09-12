from __future__ import annotations

from app.agents.state import WorkbenchState, make_trace_entry
from app.llm.ollama_client import get_llm_client

_SYSTEM_PROMPT = (
    "You combine findings from specialist agents (document retrieval, vision, "
    "structured records) into one clear, direct answer for a plant operator. "
    "Don't mention 'agents' or your own process — just answer the question. "
    "If the sources disagree, point that out explicitly rather than picking one silently."
    "Each finding may contain citation tags like [d1] or [s2] — keep those tags "
    "attached to the sentences that use them when you rewrite; don't drop them "
    "and don't invent new ones."
)


async def synthesizer_node(state: WorkbenchState) -> dict:
    parts = []
    if state.get("doc_answer"):
        parts.append(f"[Document findings]\n{state['doc_answer']}")
    if state.get("vision_answer"):
        parts.append(f"[Image findings]\n{state['vision_answer']}")
    if state.get("structured_answer"):
        parts.append(f"[Records findings]\n{state['structured_answer']}")

    if not parts:
        answer = "I couldn't find anything relevant in the ingested documents, images, or records for that question."
    elif len(parts) == 1:
        # Only one specialist fired — its answer already *is* the answer,
        # no need to spend another LLM call rephrasing it.
        answer = parts[0].split("\n", 1)[1]
    else:
        combined = "\n\n".join(parts)
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {state['query']}\n\n{combined}"},
        ]
        answer = await get_llm_client().chat(messages)

    trace = state["trace"] + [
        make_trace_entry("synthesizer", "combine", f"merged {len(parts)} specialist output(s)")
    ]
    return {"answer": answer, "trace": trace}
