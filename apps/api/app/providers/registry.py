"""Resolves the active providers for a given user, with a safe mock fallback.

Each user picks a provider (mock | openai | ollama) and stores their own API
key (encrypted). The platform itself pays for no inference. If a user hasn't
configured a real provider, everything still works via the offline mocks.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_secret
from app.models import ProviderCredential, User
from app.providers.base import EmbeddingProvider, LLMProvider
from app.providers.mock import MockEmbeddingProvider, MockLLMProvider

if TYPE_CHECKING:  # pragma: no cover
    pass


def _user_key(db: Session, user_id: str, provider: str) -> str | None:
    cred = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.user_id == user_id,
            ProviderCredential.provider == provider,
        )
    )
    return decrypt_secret(cred.encrypted_key) if cred else None


def resolve_embedding_provider(db: Session, user: User | None) -> EmbeddingProvider:
    provider = (user.embedding_provider if user else settings.embedding_provider).lower()
    if provider == "openai":
        key = _user_key(db, user.id, "openai") if user else settings.openai_api_key
        if key:
            from app.providers.openai import OpenAIEmbeddingProvider

            return OpenAIEmbeddingProvider(api_key=key)
    if provider == "ollama":
        from app.providers.ollama import OllamaEmbeddingProvider

        return OllamaEmbeddingProvider()
    return MockEmbeddingProvider()


def resolve_llm_provider(db: Session, user: User | None) -> LLMProvider:
    provider = (user.llm_provider if user else settings.llm_provider).lower()
    if provider == "openai":
        key = _user_key(db, user.id, "openai") if user else settings.openai_api_key
        if key:
            from app.providers.openai import OpenAILLMProvider

            return OpenAILLMProvider(api_key=key)
    if provider == "ollama":
        from app.providers.ollama import OllamaLLMProvider

        return OllamaLLMProvider()
    return MockLLMProvider()


# --- Global (user-less) resolvers, used by the health endpoint ---


def get_embedding_provider() -> EmbeddingProvider:
    if settings.embedding_provider.lower() == "openai" and settings.openai_api_key:
        from app.providers.openai import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(api_key=settings.openai_api_key)
    if settings.embedding_provider.lower() == "ollama":
        from app.providers.ollama import OllamaEmbeddingProvider

        return OllamaEmbeddingProvider()
    return MockEmbeddingProvider()


def get_llm_provider() -> LLMProvider:
    if settings.llm_provider.lower() == "openai" and settings.openai_api_key:
        from app.providers.openai import OpenAILLMProvider

        return OpenAILLMProvider(api_key=settings.openai_api_key)
    if settings.llm_provider.lower() == "ollama":
        from app.providers.ollama import OllamaLLMProvider

        return OllamaLLMProvider()
    return MockLLMProvider()
