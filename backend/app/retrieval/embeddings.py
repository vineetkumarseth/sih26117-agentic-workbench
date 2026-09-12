"""
Text embeddings for the retrieval layer.

Uses fastembed (https://github.com/qdrant/fastembed) to run a small
open-weight embedding model (default: BAAI/bge-small-en-v1.5) locally on
CPU via ONNX Runtime — no external embedding API, consistent with the
"nothing leaves this machine" pitch. The model weights are pulled once
from Hugging Face on first use and cached under ~/.cache/fastembed; after
that, embedding is fully offline.

If that first download can't happen (no internet at grading/demo time,
or a fully air-gapped box that hasn't been pre-seeded with the model
cache), we fall back to a deterministic hash-based pseudo-embedding so
ingestion and retrieval keep working end-to-end for development and
demoing the pipeline shape. It is NOT semantically meaningful — swap in
the real model (or pre-download the cache — see docs/SECURITY.md) before
you rely on retrieval quality for a real demo.
"""
from __future__ import annotations

import hashlib
import logging
import struct
import threading

from app.config import get_settings

logger = logging.getLogger("workbench.embeddings")
settings = get_settings()

_EMBED_DIM = 384  # matches BAAI/bge-small-en-v1.5
_lock = threading.Lock()
_model = None
_model_load_failed = False


def _model_cache_exists() -> bool:
    """True if fastembed has already cached this model from a previous
    run with internet access. If so, loading it is instant and fully
    offline — no network check needed."""
    from pathlib import Path

    cache_root = Path.home() / ".cache" / "fastembed" / "models"
    if not cache_root.exists():
        return False
    slug = settings.EMBEDDING_MODEL.split("/")[-1].lower()
    return any(slug in p.name.lower() for p in cache_root.glob("*"))


def _huggingface_reachable(timeout_seconds: float = 2.0) -> bool:
    """
    A fast (2s) reachability probe, so an air-gapped or firewalled network
    fails in ~2 seconds rather than fastembed's own retry loop (which
    backs off up to ~40s before giving up). This is exactly the
    "sovereign, on-prem, maybe fully disconnected" scenario the PS is
    built around, so failing fast here matters as much as the fallback
    itself.
    """
    try:
        import httpx

        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.head("https://huggingface.co")
            # Deliberately strict: a non-2xx (e.g. a 403 from a corporate/
            # plant egress proxy blocking the host outright, which is
            # indistinguishable from "no internet" for our purposes) is
            # treated the same as a connection failure — either way, the
            # download that follows won't succeed, so don't wait for it
            # to prove that the slow way.
            return 200 <= resp.status_code < 300
    except Exception:  # noqa: BLE001
        return False


def _get_model():
    global _model, _model_load_failed
    if _model is not None or _model_load_failed:
        return _model
    with _lock:
        if _model is not None or _model_load_failed:
            return _model
        if settings.LOW_MEMORY_MODE:
            logger.info(
                "LOW_MEMORY_MODE=true — skipping fastembed entirely and using the "
                "hash-based fallback embedding to keep this process's memory "
                "footprint small on a constrained host."
            )
            _model_load_failed = True
            return None
        if not _model_cache_exists() and not _huggingface_reachable():
            logger.warning(
                "Embedding model %s isn't cached locally and huggingface.co isn't reachable "
                "(expected on an air-gapped network) — using the hash-based fallback embedding "
                "for this run. Pre-download the model once while online to get real semantic "
                "retrieval on a disconnected deployment: see docs/SECURITY.md.",
                settings.EMBEDDING_MODEL,
            )
            _model_load_failed = True
            return None

        try:
            from fastembed import TextEmbedding

            _model = TextEmbedding(model_name=settings.EMBEDDING_MODEL)
            logger.info("Loaded local embedding model %s", settings.EMBEDDING_MODEL)
        except Exception as exc:  # noqa: BLE001 - deliberately broad, this is a soft fallback
            logger.warning(
                "Could not load embedding model %s (%s). Falling back to a "
                "non-semantic hash embedding — retrieval will run but won't "
                "be meaningfully ranked. See docs/SECURITY.md.",
                settings.EMBEDDING_MODEL,
                exc,
            )
            _model_load_failed = True
    return _model


def _hash_embedding(text: str, dim: int = _EMBED_DIM) -> list[float]:
    """Deterministic, dependency-free fallback — same text -> same vector."""
    vec: list[float] = []
    chunk = hashlib.sha256(text.encode("utf-8")).digest()
    while len(vec) < dim:
        chunk = hashlib.sha256(chunk).digest()
        vec.extend(v / 255.0 - 0.5 for v in chunk)
    return vec[:dim]


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    if model is None:
        return [_hash_embedding(t) for t in texts]
    return [list(v) for v in model.embed(texts)]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


def embedding_dim() -> int:
    return _EMBED_DIM
