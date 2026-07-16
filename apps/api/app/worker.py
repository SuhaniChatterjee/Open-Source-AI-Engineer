"""Celery application.

Run a worker with:
    celery -A app.worker.celery_app worker --loglevel=info

The broker/result backend default to REDIS_URL. `task_always_eager` (default
True) makes an enqueued task run inline if no worker is available, so the app
never silently drops work; set CELERY_TASK_ALWAYS_EAGER=false in production
where a real worker consumes the queue.
"""
from __future__ import annotations

from celery import Celery

from app.core.config import settings

_broker = settings.celery_broker_url or settings.redis_url
_backend = settings.celery_result_backend or settings.redis_url

celery_app = Celery(
    "osae",
    broker=_broker,
    backend=_backend,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)
