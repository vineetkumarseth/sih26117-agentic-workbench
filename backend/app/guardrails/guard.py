"""
Input/output guardrails for the workbench.

Two layers ship in this project:

1. A lightweight, dependency-free rules layer (this file) — regex/keyword
   checks for prompt-injection ("ignore previous instructions"), requests
   to dump secrets/system-prompt, and a handful of obviously-off-topic
   patterns. It has zero external dependencies and zero network calls, so
   it is always on and can never be the reason your demo breaks.

2. The full NeMo Guardrails engine (config.yml + rails.co), which layers
   in semantic / LLM-based checks rather than just keyword matching. It's
   real and wired up here — but NeMo Guardrails' default setup pulls an
   embedding model from Hugging Face on first run and needs its `models:`
   block pointed at a reachable LLM, so it's opt-in via
   USE_NEMO_GUARDRAILS=true rather than the default. If it fails to
   initialize for any reason (no network, misconfigured engine), we log a
   warning and silently continue on layer 1 rather than taking the whole
   API down.

Both layers write every decision to the audit log via the caller
(routers/chat.py), so "why did the assistant refuse this" is always
answerable after the fact.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger("workbench.guardrails")
settings = get_settings()

_RAILS_DIR = Path(__file__).parent

# --- Layer 1: lightweight, always-on rules -------------------------------

_SECRET_LEAK_PATTERNS = [
    re.compile(r"ignore (all|any|the)? ?(previous|prior|above) instructions", re.I),
    re.compile(r"disregard (all|any|the)? ?(previous|prior|above|rules)", re.I),
    re.compile(r"reveal (your|the) (system prompt|instructions|api key)", re.I),
    re.compile(r"what is (your|the) (system prompt|api key|secret key)", re.I),
    re.compile(r"print (your|the) (configuration|system prompt|env)", re.I),
    re.compile(r"you are now (dan|jailbroken|unrestricted)", re.I),
]

_OFF_TOPIC_SMALLTALK = [
    re.compile(r"^\s*(tell me a joke|write me a poem|what'?s the weather)", re.I),
    re.compile(r"who (won|win)s? the (cricket|football|match)", re.I),
]

# Looks-like-a-real-credential patterns, used on OUTPUT to stop the model
# accidentally echoing something that resembles a live secret it picked
# up from an ingested document.
_CREDENTIAL_LOOKALIKE = [
    re.compile(r"\b(sk|pk)-[A-Za-z0-9]{20,}\b"),  # API-key-shaped strings
    re.compile(r"-----BEGIN (RSA |EC )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key shape
]


@dataclass
class GuardResult:
    allowed: bool
    reason: str | None = None
    redacted_text: str | None = None


def check_input(text: str) -> GuardResult:
    for pattern in _SECRET_LEAK_PATTERNS:
        if pattern.search(text):
            return GuardResult(allowed=False, reason="prompt_injection_or_secret_request")
    for pattern in _OFF_TOPIC_SMALLTALK:
        if pattern.search(text):
            return GuardResult(allowed=False, reason="off_topic")
    return GuardResult(allowed=True)


def check_output(text: str) -> GuardResult:
    for pattern in _CREDENTIAL_LOOKALIKE:
        if pattern.search(text):
            redacted = pattern.sub("[REDACTED]", text)
            return GuardResult(allowed=False, reason="possible_credential_leak", redacted_text=redacted)
    return GuardResult(allowed=True, redacted_text=text)


# --- Layer 2: optional full NeMo Guardrails engine ------------------------

_nemo_rails = None
_nemo_init_attempted = False


def _try_init_nemo():
    global _nemo_rails, _nemo_init_attempted
    if _nemo_init_attempted:
        return _nemo_rails
    _nemo_init_attempted = True
    if not settings.USE_NEMO_GUARDRAILS:
        return None
    try:
        from nemoguardrails import LLMRails, RailsConfig

        config = RailsConfig.from_path(str(_RAILS_DIR))
        _nemo_rails = LLMRails(config)
        logger.info("NeMo Guardrails engine initialized from %s", _RAILS_DIR)
    except Exception as exc:  # noqa: BLE001 - never let guardrail setup crash the API
        logger.warning(
            "USE_NEMO_GUARDRAILS=true but the engine failed to initialize (%s). "
            "Continuing on the lightweight rules layer only.",
            exc,
        )
        _nemo_rails = None
    return _nemo_rails


async def check_input_full(text: str) -> GuardResult:
    """Layer 1 always runs; layer 2 (NeMo) runs on top of it if enabled and healthy."""
    layer1 = check_input(text)
    if not layer1.allowed:
        return layer1

    rails = _try_init_nemo()
    if rails is None:
        return layer1

    try:
        response = await rails.generate_async(messages=[{"role": "user", "content": text}])
        content = (response or {}).get("content", "") if isinstance(response, dict) else str(response)
        if "refuse" in content.lower() or "can't" in content.lower():
            return GuardResult(allowed=False, reason="nemo_guardrails_refusal")
    except Exception as exc:  # noqa: BLE001
        logger.warning("NeMo Guardrails check failed at runtime (%s); allowing on layer 1 result.", exc)
    return layer1
