"""Job dispatch tests: both the inline and Celery (eager) paths must reach the
underlying service function with the right arguments."""
from __future__ import annotations

import app.services.contribution_service as contribution_service
import app.services.github_writer as github_writer
import app.services.indexing_service as indexing_service
import app.tasks  # noqa: F401  (registers tasks on the celery app, as the worker does)
from app import jobs
from app.core.config import settings
from app.worker import celery_app


def test_celery_tasks_registered():
    names = {t for t in celery_app.tasks if not t.startswith("celery.")}
    assert {"index_repository", "generate_contribution", "publish_contribution"} <= names


def test_celery_runs_eagerly_in_tests():
    # Safe fallback: an enqueued task runs inline when no worker is present.
    assert celery_app.conf.task_always_eager is True


def test_submit_indexing_celery_path(monkeypatch):
    monkeypatch.setattr(settings, "task_backend", "celery")
    calls = []
    monkeypatch.setattr(indexing_service, "run_indexing", lambda r, j: calls.append((r, j)))
    jobs.submit_indexing(None, "repo1", "job1")
    assert calls == [("repo1", "job1")]  # eager task executed the service fn


def test_submit_indexing_inline_path(monkeypatch):
    monkeypatch.setattr(settings, "task_backend", "inline")
    calls = []
    monkeypatch.setattr(indexing_service, "run_indexing", lambda r, j: calls.append((r, j)))
    # No BackgroundTasks -> runs inline immediately.
    jobs.submit_indexing(None, "repo2", "job2")
    assert calls == [("repo2", "job2")]


def test_submit_indexing_inline_uses_background(monkeypatch):
    monkeypatch.setattr(settings, "task_backend", "inline")

    class _BG:
        def __init__(self):
            self.tasks = []

        def add_task(self, fn, *args):
            self.tasks.append((fn, args))

    bg = _BG()
    jobs.submit_indexing(bg, "repo3", "job3")
    assert len(bg.tasks) == 1
    assert bg.tasks[0][1] == ("repo3", "job3")


def test_submit_contribution_and_publish_celery(monkeypatch):
    monkeypatch.setattr(settings, "task_backend", "celery")
    c_calls, p_calls = [], []
    monkeypatch.setattr(contribution_service, "start_contribution", lambda t: c_calls.append(t))
    monkeypatch.setattr(github_writer, "publish", lambda t, h: p_calls.append((t, h)))
    jobs.submit_contribution(None, "task-c")
    jobs.submit_publish(None, "task-p", "fork/repo")
    assert c_calls == ["task-c"]
    assert p_calls == [("task-p", "fork/repo")]
