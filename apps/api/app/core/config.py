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

    # --- Redis (reserved for background workers; not required for the slice) ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Vector store (Qdrant) ---
    # If Qdrant is unreachable, the vector store falls back to in-memory mode.
    qdrant_url: str = "http://localhost:6333"
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
