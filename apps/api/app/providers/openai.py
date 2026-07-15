"""OpenAI-compatible provider (works with OpenAI and any compatible base_url).

Used when a user has configured an OpenAI key. Kept dependency-light by calling
the REST API directly with httpx rather than pulling the SDK.
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.providers.base import ChatMessage, EmbeddingProvider, LLMProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    # text-embedding-3-small returns 1536 dims
    dim = 1536

    def __init__(self, api_key: str, base_url: str | None = None, model: str | None = None):
        self.api_key = api_key
        self.base_url = base_url or settings.openai_base_url
        self.model = model or settings.openai_embedding_model

    @property
    def name(self) -> str:
        return f"openai:{self.model}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = httpx.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "input": texts},
            timeout=60,
        )
        resp.raise_for_status()
        return [row["embedding"] for row in resp.json()["data"]]


class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str | None = None, model: str | None = None):
        self.api_key = api_key
        self.base_url = base_url or settings.openai_base_url
        self.model = model or settings.openai_chat_model

    @property
    def name(self) -> str:
        return f"openai:{self.model}"

    def complete(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "temperature": temperature,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
