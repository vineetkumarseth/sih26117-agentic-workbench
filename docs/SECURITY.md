# Security notes

## What's implemented and why

| Concern | Implementation | Where |
|---|---|---|
| Passwords | bcrypt via the `bcrypt` package directly (not `passlib` — see below) | `app/security/auth.py` |
| Sessions | JWT, HS256, expires after `ACCESS_TOKEN_EXPIRE_MINUTES` | `app/security/auth.py` |
| Authorization | Role check (`operator` / `admin`) on sensitive routes | `require_admin` in `app/security/auth.py` |
| Self-registration | Disabled — only an existing admin can create a user | `app/routers/auth.py` |
| Login timing | Wrong-username and wrong-password take the same code path (a dummy bcrypt check always runs) | `app/routers/auth.py` |
| Rate limiting | Per-IP limits on login/chat/upload | `app/security/rate_limit.py`, `.env` |
| Secrets | Everything from environment vars; `SECRET_KEY` auto-generates a throwaway value if unset (logged as a warning) rather than defaulting to a fixed string | `app/config.py` |
| Admin bootstrap | Random password generated and logged once at first boot — never hardcoded, never stored in plaintext | `app/main.py` |
| Uploads | Extension allow-list, size cap, sanitized filename, content-addressed storage path (not the client-supplied name) | `app/routers/documents.py` |
| Audit trail | Every login, query, upload, and guardrail block is logged with a SHA-256 hash of the content (not the raw text) — admin-readable via `GET /api/audit` | `app/security/audit.py`, `app/db/models.py::AuditLog` |
| HTTP headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, a conservative CSP | `app/security/headers.py` |
| CORS | Explicit origin allow-list, never `*` | `app/config.py`, `.env` |
| Prompt injection / secret-leak requests | Regex-based input guardrail, always on | `app/guardrails/guard.py` |
| Credential-shaped output | Output scanned for API-key/private-key/AWS-key patterns before it reaches the user | `app/guardrails/guard.py` |

## Why `bcrypt` directly instead of `passlib`

`passlib` 1.7.x's bcrypt backend probes an attribute (`bcrypt.__about__`)
that the `bcrypt` package removed in 4.1+. With any reasonably current
`bcrypt` installed, `passlib` crashes at first use — which is exactly
what happened the first time this backend was booted end-to-end during
development (see the comment at the top of `app/security/auth.py`).
`passlib` hasn't had a release address this, so this project calls
`bcrypt.hashpw` / `bcrypt.checkpw` directly instead — one fewer dependency
and no version-compatibility gamble.

## Before a real (non-hackathon) deployment, change these

- **Put this behind TLS.** Nothing here terminates HTTPS — that's a
  reverse proxy's job (nginx, Caddy, or your cloud provider's load
  balancer). The security headers here assume TLS is handled upstream.
- **Set `SECRET_KEY` explicitly** in `.env` (a fresh
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`) rather
  than relying on the auto-generated one, which changes every restart and
  invalidates all issued tokens.
- **Point `QDRANT_URL` at a real Qdrant deployment** with its own auth if
  more than one backend instance needs to share a collection — embedded
  mode is single-process by design.
- **Rotate the seeded admin password** immediately after first boot if
  you didn't set `ADMIN_PASSWORD` yourself, and create named accounts per
  operator rather than sharing the admin login.
- **Review `CORS_ORIGINS`** — it should list exactly the frontend
  origin(s) that need access, on the plant's internal network, never a
  public URL.
- **Decide on log retention for the audit table** — it currently grows
  unbounded in SQLite. Fine for a hackathon demo; for anything longer-
  lived, add rotation or move it to a proper log store.

## Pre-downloading the embedding model for an air-gapped deployment

`fastembed` needs one successful internet connection to cache
`BAAI/bge-small-en-v1.5` from Hugging Face
(`~/.cache/fastembed/` by default). To prepare a machine that will run
fully offline afterward:

1. On a machine with internet, run the backend once with the same
   `EMBEDDING_MODEL` setting — this triggers the download and populates
   the cache.
2. Copy `~/.cache/fastembed/` to the same path on the target machine (or
   mount it into the container in `docker-compose.yml`).

Without this, retrieval still works — `app/retrieval/embeddings.py` falls
back to a deterministic hash-based embedding — but similarity ranking
won't be semantically meaningful. That fallback is meant to keep the
*pipeline* demoable offline, not to be a substitute for the real model in
a demo where retrieval quality is being judged.
