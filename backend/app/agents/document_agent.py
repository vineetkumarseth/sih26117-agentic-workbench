from __future__ import annotations

from app.agents.state import WorkbenchState, make_trace_entry
from app.llm.ollama_client import get_llm_client
from app.retrieval import vector_store

_SYSTEM_PROMPT = (
    "You are the document-retrieval agent inside an on-premise industrial "
    "assistant. Answer ONLY using the provided excerpts from ingested plant "
    "documents. If the excerpts don't contain the answer, say so plainly — "
    "never invent a reading, a date, or a specification that isn't in the text. "
    "Each excerpt is labelled with a citation tag like [d1]. When a sentence in "
    "your answer relies on a specific excerpt, end that sentence with its tag, "
    "e.g. 'Bearing replacement was recommended [d1].' Use a tag only when you "
    "actually used that excerpt — never invent a tag that wasn't given to you."
)


async def document_agent_node(state: WorkbenchState) -> dict:
    # Fetch a wider candidate pool than we need, then dedupe by exact text
    # match down to 5. Without this, the *same* uploaded document shows up
    # as multiple separate "sources" if it was ever ingested more than
    # once (re-uploaded during testing, etc.) -- which looks like padding,
    # not grounding, the moment anyone actually reads two "different"
    # citations and notices they're identical. Uploads are now also
    # deduped at ingest time (routers/documents.py), but this stays as a
    # second line of defense for anything already indexed before that.
    raw_results = vector_store.search(query=state["query"], owner_id=state["owner_id"], top_k=10)
    seen_text: set[str] = set()
    results = []
    for r in raw_results:
        if r["text"] in seen_text:
            continue
        seen_text.add(r["text"])
        results.append(r)
        if len(results) == 5:
            break

    if not results:
        detail = "No ingested documents matched this query (upload documents first)."
        trace = state["trace"] + [make_trace_entry("document_agent", "retrieve", detail)]
        return {
            "doc_chunks": [],
            "doc_answer": "No ingested documents were found to answer this from yet.",
            "trace": trace,
        }

    # Citations are built here, in code, from what was actually retrieved —
    # never left to the LLM to remember or reformat correctly. The [dN] tags
    # handed to the model below are exactly these ids, so any tag it uses in
    # its answer is guaranteed to resolve to a real citation.
    citations = [
        {"id": f"d{i + 1}", "source_type": "document", "label": r["filename"], "snippet": r["text"]}
        for i, r in enumerate(results)
    ]

    context = "\n\n".join(f"[{c['id']}] ({r['filename']}) {r['text']}" for c, r in zip(citations, results, strict=True))
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"Excerpts:\n{context}\n\nQuestion: {state['query']}"},
    ]
    answer = await get_llm_client().chat(messages)

    filenames = sorted({r["filename"] for r in results})
    detail = f"retrieved {len(results)} chunk(s) from {', '.join(filenames)}"
    trace = state["trace"] + [make_trace_entry("document_agent", "retrieve+answer", detail)]

    return {
        "doc_chunks": [{"text": r["text"], "filename": r["filename"], "score": r["score"]} for r in results],
        "doc_answer": answer,
        "citations": state["citations"] + citations,
        "trace": trace,
    }