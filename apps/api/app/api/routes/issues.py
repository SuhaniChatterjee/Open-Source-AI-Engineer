from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Issue, Repository, User
from app.schemas import IssueDetailOut, IssueOut, IssueSyncResult
from app.services import issue_service
from app.services.github_service import GitHubError

router = APIRouter(prefix="/repositories/{repo_id}/issues", tags=["issues"])


def _owned(db: Session, repo_id: str, user: User) -> Repository:
    repo = db.get(Repository, repo_id)
    if not repo or repo.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


def _to_out(issue: Issue) -> dict:
    return {
        "id": issue.id,
        "github_number": issue.github_number,
        "title": issue.title,
        "state": issue.state,
        "labels": json.loads(issue.labels or "[]"),
        "author": issue.author,
        "comments_count": issue.comments_count,
        "html_url": issue.html_url,
        "github_updated_at": issue.github_updated_at,
        "analysis_status": issue.analysis_status,
        "complexity_score": issue.complexity_score,
        "complexity_level": issue.complexity_level,
        "estimated_hours": issue.estimated_hours,
        "suitability_score": issue.suitability_score,
    }


def _to_detail(issue: Issue) -> dict:
    return {
        **_to_out(issue),
        "body": issue.body,
        "affected_files": json.loads(issue.affected_files or "[]"),
        "required_knowledge": json.loads(issue.required_knowledge or "[]"),
        "strategy": issue.strategy,
        "risks": json.loads(issue.risks or "[]"),
        "analysis_provider": issue.analysis_provider,
    }


@router.post("/sync", response_model=IssueSyncResult)
def sync_issues(
    repo_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = _owned(db, repo_id, user)
    try:
        synced = issue_service.sync_issues(db, repo)
    except GitHubError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return IssueSyncResult(synced=synced)


@router.get("", response_model=list[IssueOut])
def list_issues(
    repo_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _owned(db, repo_id, user)
    issues = db.scalars(
        select(Issue)
        .where(Issue.repository_id == repo_id)
        .order_by(Issue.suitability_score.desc().nullslast(), Issue.github_number.desc())
    ).all()
    return [_to_out(i) for i in issues]


@router.get("/{number}", response_model=IssueDetailOut)
def get_issue(
    repo_id: str,
    number: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _owned(db, repo_id, user)
    issue = db.scalar(
        select(Issue).where(
            Issue.repository_id == repo_id, Issue.github_number == number
        )
    )
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return _to_detail(issue)


@router.post("/{number}/analyze", response_model=IssueDetailOut)
def analyze_issue(
    repo_id: str,
    number: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = _owned(db, repo_id, user)
    if repo.status != "ready":
        raise HTTPException(
            status_code=409,
            detail=f"Repository must be indexed before analysis (status: {repo.status})",
        )
    issue = db.scalar(
        select(Issue).where(
            Issue.repository_id == repo_id, Issue.github_number == number
        )
    )
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    try:
        issue = issue_service.analyze_issue(db, user, repo, issue)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc
    return _to_detail(issue)
