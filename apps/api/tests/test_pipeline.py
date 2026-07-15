"""Offline smoke tests for the core pipeline (no DB / network required)."""
from __future__ import annotations

from app.indexing import parser
from app.providers.mock import MockEmbeddingProvider, MockLLMProvider
from app.providers.base import ChatMessage
from app.services.repo_service import normalize_repo


def test_normalize_repo_slug_and_url():
    assert normalize_repo("tiangolo/fastapi") == (
        "tiangolo/fastapi",
        "https://github.com/tiangolo/fastapi.git",
    )
    assert normalize_repo("https://github.com/tiangolo/fastapi") == (
        "tiangolo/fastapi",
        "https://github.com/tiangolo/fastapi.git",
    )


def test_chunker_produces_chunks():
    src = "def hello(name):\n    return f'hi {name}'\n\nclass Greeter:\n    def go(self):\n        return 1\n"
    chunks = parser.chunk_file("sample.py", src)
    assert chunks, "expected at least one chunk"
    assert all(c.path == "sample.py" for c in chunks)
    assert all(c.start_line >= 1 for c in chunks)


def test_markdown_falls_back_to_line_chunker():
    chunks = parser.chunk_file("README.md", "# Title\n\nSome text\n" * 30)
    assert chunks
    assert chunks[0].kind == "doc"


def test_mock_embeddings_are_deterministic_and_normalized():
    emb = MockEmbeddingProvider()
    a = emb.embed(["authentication login user"])[0]
    b = emb.embed(["authentication login user"])[0]
    assert a == b
    assert len(a) == emb.dim
    norm = sum(x * x for x in a) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_mock_llm_grounds_in_context():
    llm = MockLLMProvider()
    out = llm.complete(
        [
            ChatMessage(role="system", content="CONTEXT:\n\n[auth.py:1-10 (function)]\ndef login(): ..."),
            ChatMessage(role="user", content="How does login work?"),
        ]
    )
    assert "auth.py" in out
