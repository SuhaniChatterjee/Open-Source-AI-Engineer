"""Gemini provider tests — request shaping and failure handling, no network.

Gemini's API differs from OpenAI's in ways that are easy to get subtly wrong,
so these pin the wire format.
"""
from __future__ import annotations

import json

import httpx
import pytest

from app.providers.base import ChatMessage
from app.providers.gemini import (
    GeminiEmbeddingProvider,
    GeminiError,
    GeminiLLMProvider,
)


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=None)


def _capture(monkeypatch, payload):
    """Patch httpx.post and record what we would have sent."""
    sent = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        sent["url"] = url
        sent["headers"] = headers
        sent["json"] = json
        return _FakeResponse(payload)

    monkeypatch.setattr(httpx, "post", fake_post)
    return sent


def test_chat_maps_system_and_assistant_roles(monkeypatch):
    sent = _capture(
        monkeypatch,
        {"candidates": [{"content": {"parts": [{"text": "an answer"}]}}]},
    )
    out = GeminiLLMProvider(api_key="k", model="gemini-2.0-flash").complete(
        [
            ChatMessage(role="system", content="be grounded"),
            ChatMessage(role="user", content="q1"),
            ChatMessage(role="assistant", content="a1"),
            ChatMessage(role="user", content="q2"),
        ]
    )
    assert out == "an answer"

    body = sent["json"]
    # System text must be hoisted out of contents into systemInstruction.
    assert body["systemInstruction"]["parts"][0]["text"] == "be grounded"
    roles = [c["role"] for c in body["contents"]]
    assert roles == ["user", "model", "user"]  # 'assistant' -> 'model'
    assert all(c["role"] != "system" for c in body["contents"])


def test_api_key_goes_in_header_not_url(monkeypatch):
    sent = _capture(monkeypatch, {"candidates": [{"content": {"parts": [{"text": "x"}]}}]})
    GeminiLLMProvider(api_key="secret-key").complete([ChatMessage(role="user", content="hi")])
    assert sent["headers"]["x-goog-api-key"] == "secret-key"
    assert "secret-key" not in sent["url"]  # never leak the key into a URL


def test_multiple_system_messages_are_joined(monkeypatch):
    sent = _capture(monkeypatch, {"candidates": [{"content": {"parts": [{"text": "x"}]}}]})
    GeminiLLMProvider(api_key="k").complete(
        [
            ChatMessage(role="system", content="rules"),
            ChatMessage(role="system", content="CONTEXT: stuff"),
            ChatMessage(role="user", content="q"),
        ]
    )
    system = sent["json"]["systemInstruction"]["parts"][0]["text"]
    assert "rules" in system and "CONTEXT: stuff" in system


def test_blocked_response_raises_clearly(monkeypatch):
    _capture(monkeypatch, {"promptFeedback": {"blockReason": "SAFETY"}})
    with pytest.raises(GeminiError, match="SAFETY"):
        GeminiLLMProvider(api_key="k").complete([ChatMessage(role="user", content="q")])


def test_empty_answer_raises(monkeypatch):
    _capture(monkeypatch, {"candidates": [{"content": {"parts": []}, "finishReason": "MAX_TOKENS"}]})
    with pytest.raises(GeminiError, match="MAX_TOKENS"):
        GeminiLLMProvider(api_key="k").complete([ChatMessage(role="user", content="q")])


def test_embeddings_batch_shape_and_dim(monkeypatch):
    sent = _capture(
        monkeypatch,
        {"embeddings": [{"values": [0.1] * 768}, {"values": [0.2] * 768}]},
    )
    provider = GeminiEmbeddingProvider(api_key="k")
    vectors = provider.embed(["a", "b"])

    assert len(vectors) == 2
    assert len(vectors[0]) == provider.dim == 768
    reqs = sent["json"]["requests"]
    assert len(reqs) == 2
    assert reqs[0]["content"]["parts"][0]["text"] == "a"
    assert reqs[0]["model"].startswith("models/")
