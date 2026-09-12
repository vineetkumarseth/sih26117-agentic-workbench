from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select

from app.config import get_settings
from app.db.models import User
from app.db.session import SessionLocal, init_db
from app.llm.ollama_client import get_llm_client
from app.retrieval import vector_store
from app.routers import admin, audit, auth, chat, documents
from app.security.auth import hash_password
from app.security.headers import SecurityHeadersMiddleware
from app.security.rate_limit import limiter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("workbench.main")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # Seed the first admin account if the user table is empty. Generates a
    # random password rather than shipping a default one — printed to the
    # log exactly once so it can't be silently missed, and never written
    # to disk or to the database in plaintext.
    async with SessionLocal() as db:
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none() is None:
            password = settings.ADMIN_PASSWORD or secrets.token_urlsafe(12)
            admin = User(username=settings.ADMIN_USERNAME, hashed_password=hash_password(password), role="admin")
            db.add(admin)
            await db.commit()
            if settings.ADMIN_PASSWORD:
                logger.info("Seeded admin user '%s' using ADMIN_PASSWORD from .env.", settings.ADMIN_USERNAME)
            else:
                logger.warning(
                    "Seeded admin user '%s' with a GENERATED password (shown once): %s "
                    "— store it now, e.g. in your password manager; it is not saved anywhere in plaintext.",
                    settings.ADMIN_USERNAME,
                    password,
                )

    # Touch the vector store once so collection creation happens at boot,
    # not on the first request from a demo audience.
    vector_store.get_client()
    logger.info("Vector store ready (collection=%s).", settings.QDRANT_COLLECTION)

    if settings.MOCK_LLM:
        logger.warning(
            "MOCK_LLM=true — chat responses are canned placeholders. Set MOCK_LLM=false "
            "and run Ollama with the configured models to get real, grounded answers."
        )

    yield
    # (no shutdown-time cleanup needed — Qdrant embedded mode and SQLite
    # close their own connections when the process exits)


app = FastAPI(
    title=settings.APP_NAME,
    description="Sovereign, on-premise, agentic AI workbench for confidential industrial documents (SIH26117).",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(audit.router)
app.include_router(admin.router)


@app.get("/api/health")
async def health() -> dict:
    llm_ok = await get_llm_client().health()
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "mock_llm": settings.MOCK_LLM,
        "llm_reachable": llm_ok,
        "on_premise_only": True,
        "external_network_calls": "none — all inference, retrieval and storage run on this host",
    }
