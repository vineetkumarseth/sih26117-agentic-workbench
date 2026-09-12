# Architecture

## Request flow

```
Browser (React)
   │  JWT in Authorization header
   ▼
FastAPI  ── security headers, CORS allow-list, rate limiting
   │
   ├─ /api/auth/*        JWT issue/verify, admin-only user creation
   ├─ /api/documents/*   validated upload → chunk → embed → Qdrant
   ├─ /api/audit         admin-only read of the append-only audit log
   │
   └─ /api/chat
        │
        ▼
   guardrails.check_input_full()   ── lightweight rules, always on
        │  (blocked?  →  log + return early, agents never run)
        ▼
   LangGraph:  supervisor → document_agent → vision_agent →
               structured_agent → synthesizer
        │
        ▼
   guardrails.check_output()       ── credential-lookalike scan
        │
        ▼
   audit log write  +  JSON response {answer, route, trace}
```

## Why a sequential graph with self-skipping nodes, not a fan-out

`document_agent` always runs; `vision_agent` and `structured_agent` each
check `state["needs_vision"]` / `state["needs_structured"]` (set once by
the supervisor) and either do real work or append a one-line "skip" trace
entry and pass the state through unchanged.

That's a deliberate simplicity trade-off: LangGraph's `Send` API supports
true parallel fan-out (only invoking the agents that are needed,
concurrently), which would save a little wall-clock time. For a
hackathon-judged codebase, a fixed graph shape that's easy to read
top-to-bottom — and that always produces a full, explainable trace, even
for the agents that didn't fire — was worth more than the latency win.
The node functions are already independent enough that swapping in `Send`
later is a contained change, not a rewrite.

## Why retrieval routing is keyword-based, not an LLM classifier

`app/agents/supervisor.py` decides `needs_structured` with a regex over
words like "reading", "threshold", "pressure". An LLM-based intent
classifier is the obvious next step and the hook is exactly there — but a
regex is free, instant, and fully deterministic, which matters a lot when
a judge asks "why did it route there" mid-demo and you need a one-line
answer instead of "the model decided to."

## The three specialist agents

| Agent | Grounds answers in | Demo data |
|---|---|---|
| `document_agent` | Text chunks retrieved from Qdrant | Whatever you upload via the Documents panel |
| `vision_agent` | A local vision-language model reading an attached image | Any diagram/gauge photo you attach in chat |
| `structured_agent` | Row-filtered CSV | `backend/data/seed/equipment_readings.csv` (swap for a real historian/SCADA export) |

The vision agent has one extra trick worth pointing out in a demo: after
describing an image, it chunks that description and indexes it into the
same Qdrant collection (tagged `source: vision_caption`). Ask a
text-only follow-up later in the session and it can retrieve something
that was only ever seen in a picture — a small, concrete piece of
cross-modal memory, not just a one-shot image Q&A.

## What "on-premise" actually means here, concretely

- **LLM inference**: `app/llm/ollama_client.py` calls only
  `OLLAMA_BASE_URL` (default `http://localhost:11434`). No API key
  field exists in config because there's no external API to key into.
- **Vector store**: `app/retrieval/vector_store.py` defaults to Qdrant's
  *embedded* mode — an in-process library, not a server — persisting to
  a local folder. No open port unless you deliberately set `QDRANT_URL`
  to point at a container.
- **Embeddings**: `fastembed` runs an ONNX model on CPU, locally. It
  needs internet **once** to download the model from Hugging Face; after
  that it's fully offline. If that download can't happen (no internet,
  or a genuinely air-gapped box), `app/retrieval/embeddings.py` falls
  back to a deterministic hash-based embedding automatically, and fails
  fast (~2s, via a pre-flight reachability check) instead of retrying for
  40 seconds — see the comments there for why that mattered enough to
  build explicitly.
- **`GET /api/health`** reports `on_premise_only` and
  `external_network_calls` directly, so this claim is something you can
  point at live during a demo, not just a slide.

## Honest scope — what's a hackathon stand-in vs. production-shaped

Being upfront about this is worth more than it costs:

- **`structured_agent`** reads a sample CSV
  (`app/seed_data/equipment_readings.csv`), not a real plant historian. The
  filtering is keyword matching, not a real query engine. Swapping
  `_load_rows()` for a real data-historian query is the natural next
  step — the rest of the agent (LLM summarization, tracing) doesn't need
  to change.
- **NeMo Guardrails** (`app/guardrails/config.yml`, `rails.co`) is a real,
  parseable config, but it's off by default (`USE_NEMO_GUARDRAILS=false`)
  because its default setup needs an embedding model download and an
  LLM engine it can reach. The lightweight rules layer in `guard.py` is
  what's actually enforced by default, and is what the tests exercise.
- **Auth** is real JWT + bcrypt, but there's no refresh-token flow or
  password reset — tokens simply expire after
  `ACCESS_TOKEN_EXPIRE_MINUTES` and the user logs in again.
- **CSS/design**: hand-built Tailwind, no component library — deliberate,
  so the look isn't a recognizable template, but it also means it hasn't
  been audited against every screen size beyond a standard laptop
  viewport.

None of this is hidden in the code — every item above has a comment at
the point it matters, not just here.
