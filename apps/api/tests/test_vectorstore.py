"""Vector store persistence: embedded on-disk data must survive a 'restart'
(a new client opening the same path), and fall back to memory when disabled."""
from __future__ import annotations

from app.core.config import settings
from app.services.vectorstore import VectorStore

_PAYLOADS = [
    {"path": "auth/login.py", "start_line": 1, "end_line": 9, "kind": "function", "name": "login", "text": "def login(): ..."},
    {"path": "api/routes.py", "start_line": 1, "end_line": 5, "kind": "function", "name": "handler", "text": "def handler(): ..."},
]
_VECTORS = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]]


def test_vectors_persist_across_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "qdrant_url", "http://127.0.0.1:59999")  # unreachable
    monkeypatch.setattr(settings, "qdrant_path", str(tmp_path / "qd"))
    repo_id = "repo-persist"

    store = VectorStore()
    assert store.mode == "qdrant-local"
    store.ensure_collection(repo_id, dim=4)
    store.upsert(repo_id, _VECTORS, _PAYLOADS)
    hits = store.search(repo_id, [1.0, 0.0, 0.0, 0.0], limit=1)
    assert hits and hits[0].path == "auth/login.py"
    store.close()  # release the on-disk lock, simulating shutdown

    # New process/client opening the same path — data should still be there.
    reopened = VectorStore()
    assert reopened.mode == "qdrant-local"
    hits2 = reopened.search(repo_id, [1.0, 0.0, 0.0, 0.0], limit=1)
    assert hits2 and hits2[0].path == "auth/login.py"
    reopened.close()


def test_memory_fallback_when_path_disabled(monkeypatch):
    monkeypatch.setattr(settings, "qdrant_url", "http://127.0.0.1:59999")
    monkeypatch.setattr(settings, "qdrant_path", "")
    store = VectorStore()
    assert store.mode == "memory"
    store.close()
