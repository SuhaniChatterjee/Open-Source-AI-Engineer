"""Provider abstraction: any LLM / embedding backend plugs in behind these
interfaces so the platform stays provider-agnostic and pays no inference cost
(users bring their own key). See docs/AI-Agent-Design.md section 8.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str


class EmbeddingProvider(ABC):
    """Turns text into vectors for semantic retrieval."""

    #: dimensionality of the returned vectors (collection dim must match)
    dim: int = 384

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns one vector per input."""


class LLMProvider(ABC):
    """Generates a chat completion given a message list."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def complete(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        """Return the assistant's reply as a string."""
