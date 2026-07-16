"""Application configuration, loaded from environment / .env.

Everything has a local-dev-friendly default so the API boots with zero setup.
Providers are BYO-key: the platform pays for no inference. When no provider
key is configured, the app falls back to deterministic "mock" providers so the
full index -> chat flow runs completely offline.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    app_name: str = "OpenSource AI Engineer API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # --- Postgres ---
    database_url: str = "postgresql+psycopg://osae:osae@localhost:5432/osae"

    # --- Redis / background jobs ---
    redis_url: str = "redis://localhost:6379/0"
    # How background jobs run: "inline" (FastAPI BackgroundTasks — zero-config,
    # non-blocking dev default) or "celery" (enqueue to a Redis-backed worker).
    task_backend: str = "inline"
    # Broker/backend default to redis_url when blank.
    celery_broker_url: str = ""
    celery_result_backend: str = ""
    # Eager runs tasks inline in the caller (used by tests, and a safe fallback
    # if someone enqueues without a running worker). Set False in production.
    celery_task_always_eager: bool = True

    # --- Auth / sessions ---
    frontend_url: str = "http://localhost:3000"
    # Signs session cookies. OVERRIDE in production.
    session_secret: str = "dev-insecure-session-secret-change-me"
    session_cookie_name: str = "osae_session"
    session_max_age_seconds: int = 60 * 60 * 24 * 14  # 14 days
    session_cookie_secure: bool = False  # True behind HTTPS in production
    # Fernet key (base64, 32 bytes). If blank, one is derived from session_secret
    # for local dev. OVERRIDE with a real key in production.
    encryption_key: str | None = None

    # --- GitHub OAuth (user login). Register an OAuth App to fill these in. ---
    github_client_id: str | None = None
    github_client_secret: str | None = None
    github_oauth_scope: str = "read:user user:email"
    github_api_url: str = "https://api.github.com"
    # When GitHub OAuth is not configured, allow a local dev login so the app
    # stays runnable with zero credentials (mirrors the mock-provider fallback).
    allow_dev_login: bool = True

    # --- GitHub App (installation tokens + webhooks). Optional. ---
    github_app_id: str | None = None
    github_app_slug: str | None = None  # for the install URL
    # PEM private key, either inline or via a file path.
    github_app_private_key: str | None = None
    github_app_private_key_path: str | None = None
    # Secret configured on the GitHub App used to sign webhook deliveries.
    github_webhook_secret: str | None = None

    # --- Vector store (Qdrant) ---
    # Resolution order: a reachable Qdrant server (shared, multi-process — use
    # this in production) -> an embedded on-disk store at qdrant_path
    # (persistent across restarts, single-process — the zero-config dev default)
    # -> in-memory (ephemeral, last resort). Set qdrant_path to "" to disable
    # the embedded fallback.
    qdrant_url: str = "http://localhost:6333"
    qdrant_path: str = "qdrant_data"
    qdrant_collection_prefix: str = "osae_repo_"

    # --- Providers (BYO key). Leave blank to use the offline mock providers. ---
    # Which provider drives chat + embeddings: mock | openai | ollama
    llm_provider: str = "mock"
    embedding_provider: str = "mock"

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.1"
    ollama_embedding_model: str = "nomic-embed-text"

    # --- Indexing ---
    workspace_dir: str = "/tmp/osae-workspaces"
    max_repo_files: int = 4000  # v1 caps repo size; large repos are a later phase
    max_file_bytes: int = 400_000
    supported_extensions: list[str] = [
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".md",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
