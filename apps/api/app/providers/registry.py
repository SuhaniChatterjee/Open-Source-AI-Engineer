"""Selects the active providers from settings, with a safe mock fallback."""
from __future__ import annotations

from app.core.config import settings
from app.providers.base import EmbeddingProvider, LLMProvider
from app.providers.mock import MockEmbeddingProvider, MockLLMProvider


def get_embedding_provider() -> EmbeddingProvider:
    provider = settings.embedding_provider.lower()
    if provider == "openai" and settings.openai_api_key:
        from app.providers.openai import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider()
    if provider == "ollama":
        from app.providers.ollama import OllamaEmbeddingProvider

        return OllamaEmbeddingProvider()
    return MockEmbeddingProvider()


def get_llm_provider() -> LLMProvider:
    provider = settings.llm_provider.lower()
    if provider == "openai" and settings.openai_api_key:
        from app.providers.openai import OpenAILLMProvider

        return OpenAILLMProvider()
    if provider == "ollama":
        from app.providers.ollama import OllamaLLMProvider

        return OllamaLLMProvider()
    return MockLLMProvider()
