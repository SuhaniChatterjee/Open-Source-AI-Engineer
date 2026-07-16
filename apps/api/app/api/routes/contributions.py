from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from dataclasses import asdict

from app.models import ContributionTask, Issue, Repository, User
from app.schemas import (
    ContributionOut,
    ContributionReview,
    PublishPreviewOut,
    PublishRequest,
)
from app.jobs import submit_contribution, submit_publish
from app.services import contribution_service, github_writer

router = APIRouter(prefix="/repositories/{repo_id}", tags=["contributions"])


def _owned(db: Session, repo_id: str, user: User) -> Repository:
    repo = db.get(Repository, repo_id)
    if not repo or repo.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


def _task_or_404(db: Session, repo_id: str, task_id: str, user: User) -> ContributionTask:
    task = db.get(ContributionTask, task_id)
    if not task or task.repository_id != repo_id or task.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Contribution not found")
    return task


def _to_out(db: Session, task: ContributionTask) -> dict:
    issue = db.get(Issue, task.issue_id)
    return {
        "id": task.id,
        "repository_id": task.repository_id,
        "issue_id": task.issue_id,
        "issue_number": issue.github_number if issue else None,
        "status": task.status,
        "stage": task.stage,
        "category": task.category,
        "is_safe_category": task.is_safe_category,
        "summary": task.summary,
        "plan": json.loads(task.plan or "[]"),
        "proposed_changes": json.loads(task.proposed_changes or "[]"),
        "test_plan": task.test_plan,
        "risks": json.loads(task.risks or "[]"),
        "confidence_score": task.confidence_score,
        "confidence_rationale": task.confidence_rationale,
        "guidance": task.guidance,
        "commit_message": task.commit_message,
        "pr_title": task.pr_title,
        "pr_body": task.pr_body,
        "provider": task.provider,
        "reviewer_note": task.reviewer_note,
        "error": task.error,
        "publish_status": task.publish_status,
        "branch_name": task.branch_name,
        "pr_number": task.pr_number,
        "pr_url": task.pr_url,
        "pr_head_repo": task.pr_head_repo,
        "publish_error": task.publish_error,
    }


@router.post("/issues/{number}/contribute", response_model=ContributionOut, status_code=201)
def start_contribution(
    repo_id: str,
    number: int,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = _owned(db, repo_id, user)
    if repo.status != "ready":
        raise HTTPException(status_code=409, detail="Repository is not indexed yet")
    issue = db.scalar(
        select(Issue).where(Issue.repository_id == repo_id, Issue.github_number == number)
    )
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    if issue.analysis_status != "analyzed":
        raise HTTPException(
            status_code=409, detail="Analyze the issue before drafting a contribution"
        )

    task = ContributionTask(
        repository_id=repo_id, issue_id=issue.id, owner_id=user.id, status="queued"
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    submit_contribution(background, task.id)
    return _to_out(db, task)


@router.get("/contributions", response_model=list[ContributionOut])
def list_contributions(
    repo_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _owned(db, repo_id, user)
    tasks = db.scalars(
        select(ContributionTask)
        .where(ContributionTask.repository_id == repo_id, ContributionTask.owner_id == user.id)
        .order_by(ContributionTask.created_at.desc())
    ).all()
    return [_to_out(db, t) for t in tasks]


@router.get("/contributions/{task_id}", response_model=ContributionOut)
def get_contribution(
    repo_id: str,
    task_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _task_or_404(db, repo_id, task_id, user)
    return _to_out(db, task)


@router.post("/contributions/{task_id}/review", response_model=ContributionOut)
def review_contribution(
    repo_id: str,
    task_id: str,
    payload: ContributionReview,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _task_or_404(db, repo_id, task_id, user)
    try:
        contribution_service.set_review(db, task, payload.approve, payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_out(db, task)


@router.get("/contributions/{task_id}/publish-preview", response_model=PublishPreviewOut)
def publish_preview(
    repo_id: str,
    task_id: str,
    head_repo: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dry run: show exactly what would be pushed. No side effects."""
    task = _task_or_404(db, repo_id, task_id, user)
    if task.status != "approved":
        raise HTTPException(
            status_code=409, detail="Only an approved draft can be published"
        )
    return asdict(github_writer.preview(db, user, task, head_repo))


@router.post("/contributions/{task_id}/publish", response_model=ContributionOut, status_code=202)
def publish_contribution(
    repo_id: str,
    task_id: str,
    payload: PublishRequest,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Perform the real branch push + draft PR. Requires an approved draft, an
    explicit confirm flag, and a configured write token."""
    task = _task_or_404(db, repo_id, task_id, user)
    if task.status != "approved":
        raise HTTPException(
            status_code=409, detail="Only an approved draft can be published"
        )
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required")
    if task.publish_status in ("publishing", "published"):
        raise HTTPException(status_code=409, detail=f"Already {task.publish_status}")
    repo = db.get(Repository, repo_id)
    push_account = (payload.head_repo or repo.full_name).split("/", 1)[0]
    if github_writer.resolve_publish_token(db, user, push_account) is None:
        raise HTTPException(
            status_code=400,
            detail="No GitHub write access. Install the GitHub App or add a token in Settings.",
        )

    task.publish_status = "publishing"
    task.publish_error = None
    db.commit()
    submit_publish(background, task.id, payload.head_repo)
    return _to_out(db, task)
