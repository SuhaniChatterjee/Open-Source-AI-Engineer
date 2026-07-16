"""Job dispatch: route background work to Celery or run it inline.

`task_backend="celery"` enqueues to a worker; otherwise the work runs via
FastAPI BackgroundTasks (non-blocking, zero-config dev) or inline when no
BackgroundTasks is available. This one indirection keeps every call site
identical regardless of deployment.
"""
from __future__ import annotations

from typing import Optional

from fastapi import BackgroundTasks

from app.core.config import settings


def _use_celery() -> bool:
    return settings.task_backend.lower() == "celery"


def submit_indexing(
    background: Optional[BackgroundTasks], repo_id: str, job_id: str
) -> None:
    if _use_celery():
        from app.tasks import index_repository_task

        index_repository_task.delay(repo_id, job_id)
        return
    from app.services.indexing_service import run_indexing

    if background is not None:
        background.add_task(run_indexing, repo_id, job_id)
    else:
        run_indexing(repo_id, job_id)


def submit_contribution(
    background: Optional[BackgroundTasks], task_id: str
) -> None:
    if _use_celery():
        from app.tasks import generate_contribution_task

        generate_contribution_task.delay(task_id)
        return
    from app.services.contribution_service import start_contribution

    if background is not None:
        background.add_task(start_contribution, task_id)
    else:
        start_contribution(task_id)


def submit_publish(
    background: Optional[BackgroundTasks], task_id: str, head_repo: str | None
) -> None:
    if _use_celery():
        from app.tasks import publish_contribution_task

        publish_contribution_task.delay(task_id, head_repo)
        return
    from app.services.github_writer import publish

    if background is not None:
        background.add_task(publish, task_id, head_repo)
    else:
        publish(task_id, head_repo)
