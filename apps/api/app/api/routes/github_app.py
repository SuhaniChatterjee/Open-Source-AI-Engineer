from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.jobs import submit_indexing
from app.models import GitHubInstallation, User
from app.services import github_app, webhook_service

router = APIRouter(tags=["github-app"])


@router.get("/github/app")
def app_info(user: User = Depends(get_current_user)) -> dict:
    """Whether the GitHub App is configured, and where to install it."""
    return {
        "configured": github_app.is_configured(),
        "install_url": github_app.install_url(),
        "app_slug": settings.github_app_slug,
    }


@router.get("/github/installations")
def list_installations(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict]:
    rows = db.scalars(
        select(GitHubInstallation).where(
            (GitHubInstallation.user_id == user.id)
            | (GitHubInstallation.sender_login == user.login)
        )
    ).all()
    return [
        {
            "installation_id": r.installation_id,
            "account_login": r.account_login,
            "account_type": r.account_type,
            "repository_selection": r.repository_selection,
            "suspended": r.suspended,
        }
        for r in rows
    ]


@router.post("/webhooks/github", status_code=202)
async def github_webhook(
    request: Request,
    background: BackgroundTasks,
    x_github_event: str = Header(default="ping"),
    x_hub_signature_256: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    # Signature is computed over the exact raw bytes — read them before parsing.
    body = await request.body()
    if not webhook_service.verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    # Re-indexes triggered by a push go through the same job dispatch as the API.
    def schedule(repo_id: str, job_id: str) -> None:
        submit_indexing(background, repo_id, job_id)

    return webhook_service.dispatch(db, x_github_event, payload, schedule)
