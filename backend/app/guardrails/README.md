# Guardrails

Two layers, both defined in this folder:

## 1. Lightweight rules (`guard.py`) — always on

Regex/keyword checks for prompt injection ("ignore previous
instructions"), requests to dump secrets or the system prompt, a few
off-topic patterns on input, and API-key/private-key-shaped strings on
output. Zero dependencies, zero network calls — this is what the tests
in `backend/tests/` exercise, and what's active by default.

## 2. Full NeMo Guardrails engine (`config.yml`, `rails.co`) — opt-in

A real, valid NeMo Guardrails configuration defining the same policy at
the semantic/LLM level rather than just keyword matching. It's off by
default (`USE_NEMO_GUARDRAILS=false` in `.env`) because getting it fully
working needs two extra things this scaffold doesn't set up for you:

1. **An embedding model it can download.** NeMo Guardrails' default
   canonical-form matching needs an embedding model from Hugging Face on
   first run — same category of dependency as `fastembed` in
   `app/retrieval/embeddings.py`, just a separate download.
2. **An LLM engine it can actually reach.** `config.yml`'s `models:`
   block is pre-filled to point at a local Ollama instance
   (`engine: ollama`, `base_url: http://localhost:11434`) — confirm your
   NeMo Guardrails version's Ollama integration matches this shape before
   flipping the flag; NeMo Guardrails' supported-engine list changes
   between versions.

To turn it on:

```bash
# in backend/.env
USE_NEMO_GUARDRAILS=true
```

Restart the backend. `app/guardrails/guard.py::_try_init_nemo()` will
attempt to initialize it; if that fails for any reason (no network, a
misconfigured engine), it logs a warning and the app keeps running on
layer 1 only — a broken NeMo Guardrails setup can never take the whole
API down.

## Editing the policy

Both layers should stay in sync conceptually even though they're
enforced independently:

- Add a new keyword/pattern to block → edit the relevant list in
  `guard.py` (`_SECRET_LEAK_PATTERNS`, `_OFF_TOPIC_SMALLTALK`, or
  `_CREDENTIAL_LOOKALIKE`).
- Add the equivalent semantic rail → edit `rails.co` (a new `define user
  ...` / `define bot ...` / `define flow ...` block) and, if the
  assistant's overall behavior should change, `config.yml`'s
  `instructions:` block.
