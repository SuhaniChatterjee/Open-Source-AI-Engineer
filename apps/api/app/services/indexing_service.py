"""Orchestrates the repository indexing pipeline:

    clone -> walk files -> language detection -> structure-aware chunking
          -> embeddings -> vector upsert -> architecture map -> ready

For the MVP this runs in a FastAPI BackgroundTask (in-process). The stage/
progress model and the code are structured so it can move to a Redis/Celery
worker later without changing the pipeline (see docs/TRD.md section 11).
"""
from __future__ import annotations

import json
import logging
import os

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.indexing import architecture, cloner, parser
from app.models import IndexJob, Repository
from app.providers.registry import get_embedding_provider
from app.services.vectorstore import get_vector_store

logger = logging.getLogger(__name__)

_IGNORE_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    "__pycache__",
    ".venv",
    "venv",
    "vendor",
    ".mypy_cache",
    ".pytest_cache",
    "coverage",
}


def run_indexing(repo_id: str, job_id: str) -> None:
    """Entry point for the background task. Owns its own DB session."""
    db = SessionLocal()
    try:
        _run(db, repo_id, job_id)
    except Exception as exc:  # noqa: BLE001 - top-level guard for the worker
        logger.exception("Indexing failed for repo %s", repo_id)
        _fail(db, repo_id, job_id, str(exc))
    finally:
        db.close()
        cloner.cleanup(repo_id)


def _set(db: Session, repo: Repository, job: IndexJob, *, stage: str, progress: int) -> None:
    repo.status = stage
    job.stage = stage
    job.progress = progress
    job.status = "running"
    db.commit()


def _fail(db: Session, repo_id: str, job_id: str, error: str) -> None:
    repo = db.get(Repository, repo_id)
    job = db.get(IndexJob, job_id)
    if repo:
        repo.status = "failed"
        repo.error = error[:2000]
    if job:
        job.status = "failed"
        job.error = error[:2000]
    db.commit()


def _run(db: Session, repo_id: str, job_id: str) -> None:
    repo = db.get(Repository, repo_id)
    job = db.get(IndexJob, job_id)
    if not repo or not job:
        return

    # 1. Clone
    _set(db, repo, job, stage="cloning", progress=5)
    local_path = cloner.clone_repo(repo_id, repo.clone_url, repo.default_branch)

    # 2. Walk + read files
    _set(db, repo, job, stage="parsing", progress=25)
    rel_files, sources, languages = _collect_files(local_path)
    repo.file_count = len(rel_files)
    repo.languages = json.dumps(languages)
    repo.readme_summary = _readme_summary(local_path)

    # 3. Chunk
    all_chunks: list[parser.Chunk] = []
    for rel, text in sources.items():
        all_chunks.extend(parser.chunk_file(rel, text))

    # 4. Embed + upsert
    _set(db, repo, job, stage="embedding", progress=55)
    embedder = get_embedding_provider()
    store = get_vector_store()
    store.ensure_collection(repo_id, embedder.dim)

    batch = 64
    for i in range(0, len(all_chunks), batch):
        window = all_chunks[i : i + batch]
        vectors = embedder.embed([c.text for c in window])
        payloads = [
            {
                "path": c.path,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "kind": c.kind,
                "name": c.name,
                "text": c.text,
            }
            for c in window
        ]
        store.upsert(repo_id, vectors, payloads)
        job.progress = 55 + int(35 * (i + batch) / max(1, len(all_chunks)))
        db.commit()
    repo.chunk_count = len(all_chunks)

    # 5. Architecture map
    _set(db, repo, job, stage="mapping", progress=92)
    arch = architecture.build_architecture(local_path, rel_files, languages)
    job.log = json.dumps({"architecture": arch})

    # 6. Done
    repo.status = "ready"
    repo.error = None
    job.status = "succeeded"
    job.stage = "ready"
    job.progress = 100
    db.commit()
    logger.info(
        "Indexed %s: %d files, %d chunks", repo.full_name, len(rel_files), len(all_chunks)
    )


def _collect_files(root: str) -> tuple[list[str], dict[str, str], dict[str, int]]:
    rel_files: list[str] = []
    sources: dict[str, str] = {}
    languages: dict[str, int] = {}

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS]
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)
            rel_files.append(rel)
            if ext in settings.supported_extensions:
                try:
                    if os.path.getsize(full) > settings.max_file_bytes:
                        continue
                    with open(full, "r", encoding="utf-8", errors="replace") as fh:
                        sources[rel] = fh.read()
                    languages[ext] = languages.get(ext, 0) + 1
                except OSError:
                    continue
            if len(rel_files) >= settings.max_repo_files:
                return rel_files, sources, languages
    return rel_files, sources, languages


def _readme_summary(root: str) -> str | None:
    for name in ("README.md", "README.rst", "README.txt", "readme.md"):
        path = os.path.join(root, name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                return fh.read(1500)
    return None
