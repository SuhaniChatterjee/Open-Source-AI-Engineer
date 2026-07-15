"""Ollama provider for fully-local, free inference (http://localhost:11434)."""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.providers.base import ChatMessage, EmbeddingProvider, LLMProvider


class OllamaEmbeddingProvider(EmbeddingProvider):
    # nomic-embed-text returns 768 dims
    dim = 768

    @property
    def name(self) -> str:
        return f"ollama:{settings.ollama_embedding_model}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            resp = httpx.post(
                f"{settings.ollama_base_url}/api/embeddings",
                json={"model": settings.ollama_embedding_model, "prompt": text},
                timeout=60,
            )
            resp.raise_for_status()
            vectors.append(resp.json()["embedding"])
        return vectors


class OllamaLLMProvider(LLMProvider):
    @property
    def name(self) -> str:
        return f"ollama:{settings.ollama_chat_model}"

    def complete(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        resp = httpx.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.ollama_chat_model,
                "stream": False,
                "options": {"temperature": temperature},
                "messages": [{"role": m.role, "content": m.content} for m in messages],
            },
            timeout=180,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]
