"""GitHub webhook verification and event routing.

Deliveries are authenticated with an HMAC-SHA256 signature over the raw body
(`X-Hub-Signature-256`). Verification is constant-time. Events are routed to
small handlers that keep our local state in sync:

- installation(.created/.deleted/.suspend/.unsuspend) -> upsert/remove installs
- push                                                -> re-index tracked repos
- issues(.opened/.edited/.reopened/.closed/...)       -> upsert the issue
- ping                                                -> ack

Webhook payloads are untrusted input: handlers only read known fields and never
execute anything from them.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import GitHubInstallation, IndexJob, Repository, User
from app.services import issue_service

logger = logging.getLogger(__name__)

# A scheduler that enqueues a re-index: schedule(repo_id, job_id).
Scheduler = Callable[[str, str], None]


def verify_signature(body: bytes, signature_header: str | None) -> bool:
    """Constant-time HMAC-SHA256 check of `X-Hub-Signature-256`."""
    secret = settings.github_webhook_secret
    if not secret:
        # No secret configured -> reject signed deliveries rather than trust them.
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def dispatch(db: Session, event: str, payload: dict, schedule: Scheduler) -> dict:
    handler = {
        "ping": _on_ping,
        "installation": _on_installation,
        "installation_repositories": _on_installation_repositories,
        "push": _on_push,
        "issues": _on_issues,
    }.get(event, _on_unhandled)
    return handler(db, payload, schedule)


def _on_ping(db, payload, schedule) -> dict:
    return {"ok": True, "event": "ping"}


def _on_unhandled(db, payload, schedule) -> dict:
    return {"ok": True, "handled": False}


def _on_installation(db: Session, payload: dict, schedule: Scheduler) -> dict:
    action = payload.get("action")
    inst = payload.get("installation", {})
    installation_id = inst.get("id")
    if installation_id is None:
        return {"ok": False, "error": "missing installation id"}

    row = db.scalar(
        select(GitHubInstallation).where(
            GitHubInstallation.installation_id == installation_id
        )
    )
    if action == "deleted":
        if row:
            db.delete(row)
            db.commit()
        return {"ok": True, "action": "deleted", "installation_id": installation_id}

    account = inst.get("account", {}) or {}
    sender = (payload.get("sender") or {}).get("login")
    if not row:
        row = GitHubInstallation(installation_id=installation_id)
        db.add(row)
    row.account_login = account.get("login", "")
    row.account_type = account.get("type")
    row.target_type = inst.get("target_type")
    row.repository_selection = inst.get("repository_selection")
    row.sender_login = sender
    row.suspended = action == "suspend"
    # Best-effort link to a platform user by matching GitHub login.
    if sender:
        user = db.scalar(select(User).where(User.login == sender))
        if user:
            row.user_id = user.id
    db.commit()
    return {"ok": True, "action": action, "installation_id": installation_id}


def _on_installation_repositories(db, payload, schedule) -> dict:
    # Repository selection changes; nothing to persist for the MVP.
    return {
        "ok": True,
        "added": len(payload.get("repositories_added", [])),
        "removed": len(payload.get("repositories_removed", [])),
    }


def _on_push(db: Session, payload: dict, schedule: Scheduler) -> dict:
    repo_info = payload.get("repository", {}) or {}
    full_name = repo_info.get("full_name")
    if not full_name:
        return {"ok": False, "error": "missing repository"}

    # Re-index every tracked copy of this repo that is currently ready.
    repos = db.scalars(
        select(Repository).where(
            Repository.full_name == full_name, Repository.status == "ready"
        )
    ).all()
    scheduled = 0
    for repo in repos:
        repo.status = "pending"
        job = IndexJob(repository_id=repo.id, status="queued")
        db.add(job)
        db.commit()
        db.refresh(job)
        schedule(repo.id, job.id)
        scheduled += 1
    return {"ok": True, "event": "push", "reindexed": scheduled}


def _on_issues(db: Session, payload: dict, schedule: Scheduler) -> dict:
    repo_info = payload.get("repository", {}) or {}
    full_name = repo_info.get("full_name")
    issue_payload = payload.get("issue")
    if not full_name or not issue_payload:
        return {"ok": False, "error": "missing repository or issue"}

    repos = db.scalars(
        select(Repository).where(Repository.full_name == full_name)
    ).all()
    updated = 0
    for repo in repos:
        if issue_service.upsert_issue_from_payload(db, repo, issue_payload):
            updated += 1
    return {"ok": True, "event": "issues", "action": payload.get("action"), "updated": updated}
