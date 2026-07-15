"""OpenAI-compatible provider (works with OpenAI and any compatible base_url).

Only used when the user configures OPENAI_API_KEY. Kept dependency-light by
calling the REST API directly with httpx rather than pulling the SDK.
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.providers.base import ChatMessage, EmbeddingProvider, LLMProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    # text-embedding-3-small returns 1536 dims
    dim = 1536

    @property
    def name(self) -> str:
        return f"openai:{settings.openai_embedding_model}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = httpx.post(
            f"{settings.openai_base_url}/embeddings",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"model": settings.openai_embedding_model, "input": texts},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return [row["embedding"] for row in data]


class OpenAILLMProvider(LLMProvider):
    @property
    def name(self) -> str:
        return f"openai:{settings.openai_chat_model}"

    def complete(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        resp = httpx.post(
            f"{settings.openai_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_chat_model,
                "temperature": temperature,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
