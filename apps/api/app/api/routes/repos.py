from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import IndexJob, Repository, User
from app.schemas import IndexJobOut, RepoCreate, RepoOut
from app.services.indexing_service import run_indexing
from app.services.repo_service import normalize_repo
from app.services.vectorstore import get_vector_store

router = APIRouter(prefix="/repositories", tags=["repositories"])


def _owned(db: Session, repo_id: str, user: User) -> Repository:
    repo = db.get(Repository, repo_id)
    if not repo or repo.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.get("", response_model=list[RepoOut])
def list_repositories(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.scalars(
        select(Repository)
        .where(Repository.owner_id == user.id)
        .order_by(Repository.created_at.desc())
    ).all()


@router.post("", response_model=RepoOut, status_code=201)
def add_repository(
    payload: RepoCreate,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        full_name, clone_url = normalize_repo(payload.repo)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    existing = db.scalar(
        select(Repository).where(
            Repository.full_name == full_name, Repository.owner_id == user.id
        )
    )
    if existing and existing.status not in ("failed",):
        return existing

    repo = existing or Repository(
        full_name=full_name, clone_url=clone_url, owner_id=user.id
    )
    repo.clone_url = clone_url
    repo.status = "pending"
    repo.error = None
    db.add(repo)
    db.commit()
    db.refresh(repo)

    job = IndexJob(repository_id=repo.id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    background.add_task(run_indexing, repo.id, job.id)
    return repo


@router.get("/{repo_id}", response_model=RepoOut)
def get_repository(
    repo_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _owned(db, repo_id, user)


@router.get("/{repo_id}/status", response_model=IndexJobOut)
def get_index_status(
    repo_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _owned(db, repo_id, user)
    job = db.scalar(
        select(IndexJob)
        .where(IndexJob.repository_id == repo_id)
        .order_by(IndexJob.created_at.desc())
    )
    if not job:
        raise HTTPException(status_code=404, detail="No index job found")
    return job


@router.get("/{repo_id}/architecture")
def get_architecture(
    repo_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _owned(db, repo_id, user)
    job = db.scalar(
        select(IndexJob)
        .where(IndexJob.repository_id == repo_id, IndexJob.status == "succeeded")
        .order_by(IndexJob.created_at.desc())
    )
    if not job or not job.log:
        raise HTTPException(
            status_code=409, detail="Architecture not available until indexing completes"
        )
    return json.loads(job.log).get("architecture", {})


@router.delete("/{repo_id}", status_code=204)
def delete_repository(
    repo_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = _owned(db, repo_id, user)
    get_vector_store().delete_repo(repo_id)
    db.delete(repo)
    db.commit()
