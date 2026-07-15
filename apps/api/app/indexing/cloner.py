"""Shallow-clone a public repository into an isolated workspace directory.

For the MVP we clone public repos over HTTPS. Private repos (via GitHub App
installation tokens) and sandboxed execution are covered in
docs/GitHub-App-Design.md and are a later phase.
"""
from __future__ import annotations

import os
import shutil

from git import Repo

from app.core.config import settings


def workspace_path(repo_id: str) -> str:
    return os.path.join(settings.workspace_dir, repo_id)


def clone_repo(repo_id: str, clone_url: str, branch: str | None = None) -> str:
    """Shallow clone into the workspace and return the local path."""
    dest = workspace_path(repo_id)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(settings.workspace_dir, exist_ok=True)

    kwargs = {"depth": 1}
    if branch:
        kwargs["branch"] = branch
    Repo.clone_from(clone_url, dest, **kwargs)
    return dest


def cleanup(repo_id: str) -> None:
    dest = workspace_path(repo_id)
    if os.path.exists(dest):
        shutil.rmtree(dest, ignore_errors=True)
