"""The GitHub write path: turn an APPROVED contribution draft into a real
branch, commit, push, and draft pull request.

Hard rules enforced here:
- Only an `approved` ContributionTask may be published (human approval gate).
- A write credential must be configured; we never fabricate a push.
- The PR is always opened as a DRAFT.

The git mechanics (`push_branch`) are isolated from the GitHub REST call
(`open_draft_pr`) so the push can be tested against any remote (including a
local bare repo) without touching github.com.

Real-world note: contributors rarely have push access to upstream repos, so
`head_repo` lets the caller push to their own fork and open the PR against the
original. If omitted, the branch is pushed to the repo itself (works only when
the user has write access).
"""
from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass

import httpx
from git import Actor, Repo

from app.core.config import settings
from app.core.security import decrypt_secret
from app.db.session import SessionLocal
from app.indexing.cloner import workspace_path
from app.models import ContributionTask, Issue, ProviderCredential, Repository, User

logger = logging.getLogger(__name__)


class GitHubWriteError(Exception):
    pass


@dataclass
class PublishPreview:
    branch_name: str
    base: str
    head: str
    files: list[str]
    commit_message: str
    pr_title: str
    pr_body: str
    head_repo: str
    token_configured: bool


def resolve_write_token(db, user: User | None) -> str | None:
    """A user's encrypted GitHub token, else a server-level env token."""
    if user:
        cred = (
            db.query(ProviderCredential)
            .filter(
                ProviderCredential.user_id == user.id,
                ProviderCredential.provider == "github",
            )
            .first()
        )
        if cred:
            token = decrypt_secret(cred.encrypted_key)
            if token:
                return token
    return os.environ.get("GITHUB_TOKEN")


def branch_name_for(task: ContributionTask, issue: Issue) -> str:
    return f"osae/issue-{issue.github_number}-{task.id[:8]}"


def _split_owner_repo(full_name: str) -> tuple[str, str]:
    owner, name = full_name.split("/", 1)
    return owner, name


def build_pr_payload(
    *, title: str, body: str, head: str, base: str, draft: bool = True
) -> dict:
    return {"title": title, "body": body, "head": head, "base": base, "draft": draft}


def _auth_url(clone_url: str, token: str | None) -> str:
    if not token or not clone_url.startswith("https://"):
        return clone_url
    return clone_url.replace("https://", f"https://x-access-token:{token}@", 1)


def push_branch(
    *,
    clone_url: str,
    token: str | None,
    default_branch: str,
    branch: str,
    changes: list[dict],
    commit_message: str,
    author: Actor,
    workspace: str,
) -> None:
    """Clone `clone_url`, create `branch`, apply `changes`, commit, and push.

    `changes` is the task's proposed_changes list. Raises GitHubWriteError on
    an empty or no-op change set.
    """
    dest = workspace_path(workspace)
    if os.path.exists(dest):
        shutil.rmtree(dest)

    repo = Repo.clone_from(_auth_url(clone_url, token), dest, depth=1, branch=default_branch)
    repo.git.checkout("-b", branch)

    touched: list[str] = []
    for change in changes:
        path = change["path"]
        target = os.path.join(dest, path)
        os.makedirs(os.path.dirname(target) or dest, exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(change["new_content"])
        touched.append(path)

    if not touched:
        raise GitHubWriteError("No files to write.")

    repo.index.add(touched)
    if not repo.index.diff("HEAD"):
        raise GitHubWriteError("Proposed changes produced no diff against HEAD.")

    repo.index.commit(commit_message, author=author, committer=author)
    origin = repo.remote("origin")
    push_info = origin.push(refspec=f"{branch}:{branch}")
    for info in push_info:
        if info.flags & info.ERROR:
            raise GitHubWriteError(f"git push failed: {info.summary}")


def open_draft_pr(
    *, api_url: str, repo_full_name: str, token: str, payload: dict
) -> dict:
    owner, name = _split_owner_repo(repo_full_name)
    resp = httpx.post(
        f"{api_url}/repos/{owner}/{name}/pulls",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json=payload,
        timeout=60,
    )
    if resp.status_code >= 400:
        raise GitHubWriteError(
            f"GitHub PR creation failed ({resp.status_code}): {resp.text[:300]}"
        )
    data = resp.json()
    return {"number": data["number"], "url": data["html_url"]}


def preview(db, user: User, task: ContributionTask, head_repo: str | None) -> PublishPreview:
    issue = db.get(Issue, task.issue_id)
    repo = db.get(Repository, task.repository_id)
    branch = branch_name_for(task, issue)
    changes = _changes(task)
    head_owner = _split_owner_repo(head_repo)[0] if head_repo else None
    head = f"{head_owner}:{branch}" if head_owner else branch
    return PublishPreview(
        branch_name=branch,
        base=repo.default_branch,
        head=head,
        files=[c["path"] for c in changes],
        commit_message=task.commit_message or "",
        pr_title=task.pr_title or "",
        pr_body=task.pr_body or "",
        head_repo=head_repo or repo.full_name,
        token_configured=resolve_write_token(db, user) is not None,
    )


def _changes(task: ContributionTask) -> list[dict]:
    import json

    return json.loads(task.proposed_changes or "[]")


def publish(task_id: str, head_repo: str | None) -> None:
    """Background entry point: perform the real push + draft PR."""
    db = SessionLocal()
    workspace = f"publish-{task_id}"
    try:
        task = db.get(ContributionTask, task_id)
        if not task:
            return
        issue = db.get(Issue, task.issue_id)
        repo = db.get(Repository, task.repository_id)
        user = db.get(User, task.owner_id)

        token = resolve_write_token(db, user)
        if not token:
            raise GitHubWriteError(
                "No GitHub write token configured. Add one in Settings to publish."
            )

        branch = branch_name_for(task, issue)
        changes = _changes(task)
        # Push to the fork if given, else to the repo itself.
        push_full_name = head_repo or repo.full_name
        push_clone_url = f"https://github.com/{push_full_name}.git"
        author = Actor(user.name or user.login, user.email or f"{user.login}@users.noreply.github.com")

        task.publish_status = "publishing"
        task.branch_name = branch
        task.pr_head_repo = push_full_name
        db.commit()

        push_branch(
            clone_url=push_clone_url,
            token=token,
            default_branch=repo.default_branch,
            branch=branch,
            changes=changes,
            commit_message=task.commit_message or f"Address #{issue.github_number}",
            author=author,
            workspace=workspace,
        )

        head_owner = _split_owner_repo(push_full_name)[0]
        head = f"{head_owner}:{branch}" if head_repo else branch
        payload = build_pr_payload(
            title=task.pr_title or f"Address #{issue.github_number}",
            body=task.pr_body or "",
            head=head,
            base=repo.default_branch,
            draft=True,
        )
        result = open_draft_pr(
            api_url=settings.github_api_url,
            repo_full_name=repo.full_name,
            token=token,
            payload=payload,
        )
        task.pr_number = result["number"]
        task.pr_url = result["url"]
        task.publish_status = "published"
        task.publish_error = None
        db.commit()
        logger.info("Published contribution %s as PR %s", task_id, result["url"])
    except Exception as exc:  # noqa: BLE001
        logger.exception("Publish failed for %s", task_id)
        task = db.get(ContributionTask, task_id)
        if task:
            task.publish_status = "failed"
            task.publish_error = str(exc)[:2000]
            db.commit()
    finally:
        db.close()
        dest = workspace_path(workspace)
        if os.path.exists(dest):
            shutil.rmtree(dest, ignore_errors=True)
