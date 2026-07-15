"""Thin wrapper over Qdrant with an automatic in-memory fallback.

Each repository gets its own collection so retrieval is naturally scoped and a
repo can be re-indexed or deleted independently.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SearchHit:
    path: str
    start_line: int
    end_line: int
    kind: str
    text: str
    score: float


class VectorStore:
    def __init__(self) -> None:
        try:
            self.client = QdrantClient(url=settings.qdrant_url, timeout=10)
            self.client.get_collections()  # connectivity probe
            self.mode = "qdrant"
        except Exception as exc:  # pragma: no cover - env dependent
            logger.warning("Qdrant unreachable (%s); using in-memory vector store", exc)
            self.client = QdrantClient(location=":memory:")
            self.mode = "memory"

    def _collection(self, repo_id: str) -> str:
        return f"{settings.qdrant_collection_prefix}{repo_id.replace('-', '')}"

    def ensure_collection(self, repo_id: str, dim: int) -> None:
        name = self._collection(repo_id)
        if self.client.collection_exists(name):
            self.client.delete_collection(name)
        self.client.create_collection(
            collection_name=name,
            vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
        )

    def upsert(self, repo_id: str, vectors: list[list[float]], payloads: list[dict]) -> None:
        name = self._collection(repo_id)
        points = [
            qm.PointStruct(id=str(uuid.uuid4()), vector=vec, payload=payload)
            for vec, payload in zip(vectors, payloads)
        ]
        # Batch to keep request sizes sane on large repos.
        for i in range(0, len(points), 256):
            self.client.upsert(collection_name=name, points=points[i : i + 256])

    def search(self, repo_id: str, query_vector: list[float], limit: int = 8) -> list[SearchHit]:
        name = self._collection(repo_id)
        if not self.client.collection_exists(name):
            return []
        results = self.client.search(
            collection_name=name, query_vector=query_vector, limit=limit
        )
        hits: list[SearchHit] = []
        for r in results:
            p = r.payload or {}
            hits.append(
                SearchHit(
                    path=p.get("path", "?"),
                    start_line=p.get("start_line", 0),
                    end_line=p.get("end_line", 0),
                    kind=p.get("kind", "chunk"),
                    text=p.get("text", ""),
                    score=r.score,
                )
            )
        return hits

    def delete_repo(self, repo_id: str) -> None:
        name = self._collection(repo_id)
        if self.client.collection_exists(name):
            self.client.delete_collection(name)


_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
