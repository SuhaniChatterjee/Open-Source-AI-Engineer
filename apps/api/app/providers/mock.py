"""Offline, deterministic providers so the whole flow runs with zero API keys.

- MockEmbeddingProvider produces stable hashed bag-of-words vectors. It is NOT
  semantically strong, but it is deterministic and dependency-free, which makes
  the index -> retrieve -> chat path fully runnable and testable offline.
- MockLLMProvider composes an extractive, grounded answer from the retrieved
  context so the chat endpoint returns something useful (with citations)
  without calling any real model.
"""
from __future__ import annotations

import hashlib
import math
import re

from app.providers.base import ChatMessage, EmbeddingProvider, LLMProvider

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


class MockEmbeddingProvider(EmbeddingProvider):
    dim = 384

    @property
    def name(self) -> str:
        return "mock-embed"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = _tokenize(text)
        if not tokens:
            vec[0] = 1.0
            return vec
        for tok in tokens:
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class MockLLMProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "mock-llm"

    def complete(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        user_msg = next(
            (m.content for m in reversed(messages) if m.role == "user"), ""
        )
        context = next(
            (
                m.content
                for m in messages
                if m.role == "system" and m.content.startswith("CONTEXT")
            ),
            "",
        )
        question = user_msg.strip().splitlines()[0] if user_msg else "your question"

        if not context.strip():
            return (
                "I don't have any indexed context for this repository yet, so I "
                "can't answer confidently. Once indexing finishes, ask again.\n\n"
                "_(offline mock model — connect a real provider for full answers)_"
            )

        # Extractive: surface the most relevant snippets already assembled into
        # the context block, framed as an answer. Grounded, no hallucination.
        snippets = [
            line for line in context.splitlines() if line.strip().startswith("[")
        ][:5]
        joined = "\n".join(snippets) if snippets else context[:600]
        return (
            f"Based on the indexed repository, here is what is relevant to "
            f"“{question}”:\n\n{joined}\n\n"
            "The cited files above are the best matches for your question. "
            "Open them to see the full implementation.\n\n"
            "_(offline mock model — connect OpenAI/Ollama for synthesized answers)_"
        )
