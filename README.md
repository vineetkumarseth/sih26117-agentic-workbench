# Sovereign Agentic Workbench (SIH26117)

A multi-agent, on-premise AI assistant for confidential industrial
documents — inspection reports, engineering diagrams, maintenance logs —
built for **SIH26117: Sovereign On-Premise Agentic AI Workbench using
Open-Weight Multimodal LLMs for Confidential Industrial Work** (MRPL).

Every model, every vector, every stored document lives on the machine
this runs on. There is no external API call in the answer path — see
`docs/ARCHITECTURE.md` for exactly what that means and how it's enforced.

## What's here

```
backend/    FastAPI + LangGraph multi-agent orchestration, Qdrant retrieval,
            local LLM client (Ollama), guardrails, auth, audit log
frontend/   React + Vite + Tailwind dashboard (chat, agent trace panel,
            document upload)
docker-compose.yml   backend + Qdrant (+ optional Ollama) in one command
scripts/    setup.sh (first-time setup), pull_models.sh (fetch open-weight models)
docs/       architecture and security notes
```

## Quickstart (fastest path to a demo)

The backend runs in **mock LLM mode** out of the box — no GPU, no model
download, no wait. This is enough to demo the full pipeline (routing,
retrieval, guardrails, the agent trace panel) before you've pulled any
model weights.

```bash
./scripts/setup.sh                       # creates backend/.venv, backend/.env
cd backend && . .venv/bin/activate
uvicorn app.main:app --reload            # http://localhost:8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev                              # http://localhost:5173
```

Open `http://localhost:5173`. The backend's startup log prints a
generated admin password the first time it runs — copy it from the
terminal, it's shown exactly once.

## Turning on real, grounded answers

Mock mode answers are clearly labelled placeholders. For the real thing:

```bash
./scripts/pull_models.sh        # ollama pull llama3.1:8b && ollama pull llava
```

Then set `MOCK_LLM=false` in `backend/.env` and restart uvicorn. Upload a
document (the sidebar's **Documents** panel) and ask about it — the
document agent will retrieve real chunks and ground the LLM's answer in
them.

## One-command backend (Docker)

```bash
docker compose up --build               # backend + Qdrant
docker compose --profile llm up --build  # + a local Ollama container
```

The frontend isn't containerized here on purpose — `npm run dev` gives
faster iteration for a hackathon demo than rebuilding an image each time.

## Demo script (suggested)

1. Show `/api/health` — point out `on_premise_only: true` and
   `external_network_calls: "none"`.
2. Upload a sample inspection report (Documents panel).
3. Ask a question about it — watch the **agent trace** panel show
   Supervisor → Document agent → Synthesizer, with real timestamps.
4. Attach an image of a gauge/diagram, ask a question about it — trace
   now shows the Vision agent firing too.
5. Ask something with "pressure reading" / "last inspection date" — the
   Structured-data agent fires against `app/seed_data/equipment_readings.csv`.
6. Try a prompt-injection line ("ignore previous instructions...") — show
   it getting blocked, then open the **admin audit log**
   (`GET /api/audit`) and point at the logged `guardrail_block` row as
   proof the system is auditable, not just permissive-with-extra-steps.

## Tests

```bash
cd backend && . .venv/bin/activate && pytest
```

## Where the real project ends and the scaffold begins

Being upfront about this matters more than pretending otherwise — see
`docs/ARCHITECTURE.md`'s "Honest scope" section for exactly what's
production-shaped vs. what's a deliberately simple stand-in for the
hackathon (e.g. the structured-data agent reads a sample CSV, not a real
historian; retrieval routing is keyword-based, not a fan-out graph).
Both docs also list the natural next steps if you have build time left.
