"""
Central configuration for the Sovereign Agentic Workbench backend.

Every secret and every environment-specific value is read from the
environment (via a .env file in development). Nothing here is a hardcoded
credential, model key, or endpoint — that's what makes the same image
deployable on a laptop, a lab server, or an air-gapped plant network.
"""
from __future__ import annotations

import secrets
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Identity of this deployment -----------------------------------
    APP_NAME: str = "Sovereign Agentic Workbench"
    ENVIRONMENT: str = "development"  # development | production

    # --- Auth -------------------------------------------------------------
    # Auto-generates a throwaway dev secret if none is supplied so the app
    # never *silently* runs on a hardcoded key — but always set SECRET_KEY
    # explicitly in production (docs/SECURITY.md explains why).
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Seed admin account — password is generated at first boot and printed
    # once to the server log if you don't set one yourself. See main.py.
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str | None = None

    # --- CORS ---------------------------------------------------------
    # Explicit allow-list, comma-separated in the environment. Never "*" —
    # this app assumes it is reachable only from the plant's internal
    # network / VPN, not the open internet.
    #
    # Stored as a plain str (see cors_origins property below) rather than
    # List[str]: pydantic-settings tries to JSON-decode complex-typed env
    # vars before any custom validator runs, which rejects a plain
    # comma-separated value like "http://a,http://b" with a confusing
    # "error parsing value" exception. A str field sidesteps that entirely.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # --- Rate limiting -----------------------------------------------
    RATE_LIMIT_CHAT: str = "20/minute"
    RATE_LIMIT_LOGIN: str = "10/minute"
    RATE_LIMIT_UPLOAD: str = "10/minute"

    # --- Uploads --------------------------------------------------------
    MAX_UPLOAD_MB: int = 25
    # Same str-not-List[str] reasoning as CORS_ORIGINS above.
    ALLOWED_UPLOAD_EXTENSIONS: str = ".pdf,.txt,.md,.png,.jpg,.jpeg"
    UPLOAD_DIR: str = "./data/uploads"

    @property
    def allowed_upload_extensions(self) -> List[str]:
        return [e.strip() for e in self.ALLOWED_UPLOAD_EXTENSIONS.split(",") if e.strip()]

    # --- Database -------------------------------------------------------
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/workbench.db"

    # --- Vector store (Qdrant) ------------------------------------------
    # QDRANT_URL unset -> runs Qdrant in embedded/local mode (on-disk,
    # no server process, nothing on the network). Set QDRANT_URL to point
    # at a real Qdrant server/container for a multi-user deployment.
    QDRANT_URL: str | None = None
    QDRANT_LOCAL_PATH: str = "./data/qdrant"
    QDRANT_COLLECTION: str = "industrial_documents"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    LOW_MEMORY_MODE: bool = False# open-weight, runs locally via fastembed

    # --- LLM (Ollama-compatible local inference) -------------------------
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TEXT_MODEL: str = "llama3.1:8b"
    OLLAMA_VISION_MODEL: str = "llava:latest"
    LLM_REQUEST_TIMEOUT_SECONDS: int = 120

    # If true (or if Ollama is simply unreachable), the LLM client returns
    # deterministic canned responses so the full pipeline — routing,
    # retrieval, guardrails, trace panel — can be built/demoed/graded
    # before model weights are pulled onto the machine.
    MOCK_LLM: bool = True

    # --- Guardrails -------------------------------------------------------
    # Custom lightweight rails (guardrails/guard.py) are always active and
    # never require network access. Flip this on to additionally route
    # through the full NeMo Guardrails engine defined in
    # guardrails/config.yml once you've wired an LLM engine + embedding
    # model it can reach — see guardrails/README.md.
    USE_NEMO_GUARDRAILS: bool = False

    # --- Observability (optional Langfuse export) ------------------------
    LANGFUSE_PUBLIC_KEY: str | None = None
    LANGFUSE_SECRET_KEY: str | None = None
    LANGFUSE_HOST: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
