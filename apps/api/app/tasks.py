"""Celery task wrappers around the (already worker-safe) service functions.

Each underlying service owns its own DB session and cleans up its workspace, so
these wrappers stay thin. Tasks call `module.function(...)` (not a bound import)
so they remain patchable in tests.
"""
from __future__ import annotations

from app.services import contribution_service, github_writer, indexing_service
from app.worker import celery_app


@celery_app.task(name="index_repository", bind=True, max_retries=2)
def index_repository_task(self, repo_id: str, job_id: str) -> None:
    indexing_service.run_indexing(repo_id, job_id)


@celery_app.task(name="generate_contribution", bind=True)
def generate_contribution_task(self, task_id: str) -> None:
    contribution_service.start_contribution(task_id)


@celery_app.task(name="publish_contribution", bind=True)
def publish_contribution_task(self, task_id: str, head_repo: str | None = None) -> None:
    github_writer.publish(task_id, head_repo)
