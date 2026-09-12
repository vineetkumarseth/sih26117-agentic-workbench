from __future__ import annotations


def chunk_text(text: str, *, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    """
    Word-based sliding-window chunker. Good enough for hackathon-scale
    documents (inspection reports, manuals, SOPs); swap for a
    structure-aware splitter (headings/tables) if you have time left.
    """
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(words), step):
        piece = words[start : start + chunk_size]
        if not piece:
            continue
        chunks.append(" ".join(piece))
        if start + chunk_size >= len(words):
            break
    return chunks
