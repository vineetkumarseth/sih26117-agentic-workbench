from __future__ import annotations

from app.agents.state import WorkbenchState, make_trace_entry
from app.llm.ollama_client import get_llm_client
from app.retrieval import vector_store
from app.retrieval.chunking import chunk_text


async def vision_agent_node(state: WorkbenchState) -> dict:
    if not state.get("needs_vision") or not state.get("image_base64"):
        trace = state["trace"] + [make_trace_entry("vision_agent", "skip", "no image attached to this turn")]
        return {"vision_answer": None, "trace": trace}

    prompt = (
        "You are the vision agent inside an on-premise industrial assistant. "
        "Describe the relevant parts of this image (diagram, gauge, nameplate, "
        f"or photo) and answer the operator's question: {state['query']}"
    )
    answer = await get_llm_client().chat_vision(prompt, state["image_base64"])

    # Fold what the vision agent saw back into the knowledge base as a
    # short "vision caption" chunk, tagged with its source, so a later
    # *text-only* question can retrieve something that was only ever seen
    # in an image — a small but real piece of agentic memory.
    for chunk in chunk_text(answer, chunk_size=200, overlap=0):
        vector_store.add_chunks(
            document_id=f"vision:{state['session_id']}",
            owner_id=state["owner_id"],
            filename="(image attached in chat)",
            chunks=[chunk],
            source="vision_caption",
        )

        trace = state["trace"] + [
        make_trace_entry("vision_agent", "analyze+index", "described image, indexed caption for future recall")
    ]
    citation = {
        "id": "v1",
        "source_type": "vision",
        "label": "Image attached in chat",
        "snippet": answer,
    }
    return {"vision_answer": answer, "citations": state["citations"] + [citation], "trace": trace}