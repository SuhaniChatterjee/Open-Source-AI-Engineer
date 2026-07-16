"""Google Gemini provider.

Gemini's free tier covers both chat and embeddings, which makes it the
cheapest way to run this app for real (as opposed to the offline mocks).

Notes on the API shape, which differs from OpenAI's:
- The key goes in an `x-goog-api-key` header, never a URL query param.
- There is no "system" role: system text goes in `systemInstruction`, and the
  assistant role is called "model".
- Embeddings are batched via `:batchEmbedContents`.
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.providers.base import ChatMessage, EmbeddingProvider, LLMProvider


class GeminiError(RuntimeError):
    pass


class GeminiEmbeddingProvider(EmbeddingProvider):
    # text-embedding-004 returns 768 dims
    dim = 768

    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or settings.gemini_embedding_model

    @property
    def name(self) -> str:
        return f"gemini:{self.model}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = httpx.post(
            f"{settings.gemini_base_url}/models/{self.model}:batchEmbedContents",
            headers={"x-goog-api-key": self.api_key},
            json={
                "requests": [
                    {
                        "model": f"models/{self.model}",
                        "content": {"parts": [{"text": t}]},
                    }
                    for t in texts
                ]
            },
            timeout=90,
        )
        resp.raise_for_status()
        return [e["values"] for e in resp.json()["embeddings"]]


class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or settings.gemini_chat_model

    @property
    def name(self) -> str:
        return f"gemini:{self.model}"

    def complete(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        # Gemini has no system role — hoist system text into systemInstruction.
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        contents = [
            {
                "role": "model" if m.role == "assistant" else "user",
                "parts": [{"text": m.content}],
            }
            for m in messages
            if m.role != "system"
        ]
        payload: dict = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        resp = httpx.post(
            f"{settings.gemini_base_url}/models/{self.model}:generateContent",
            headers={"x-goog-api-key": self.api_key},
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        candidates = data.get("candidates") or []
        if not candidates:
            # Safety filters (or an empty prompt) can yield zero candidates.
            reason = (data.get("promptFeedback") or {}).get("blockReason", "no candidates")
            raise GeminiError(f"Gemini returned no answer ({reason}).")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            finish = candidates[0].get("finishReason", "unknown")
            raise GeminiError(f"Gemini returned an empty answer (finishReason: {finish}).")
        return text
