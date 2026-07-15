"""Tests for the GitHub write path.

The git mechanics are exercised against a LOCAL bare repository acting as the
remote — no network, no github.com. The GitHub REST call is covered by testing
the payload builder in isolation.
"""
from __future__ import annotations

import os

import pytest
from git import Actor, Repo

from app.core.config import settings
from app.services import github_writer
from app.services.github_writer import GitHubWriteError, build_pr_payload, push_branch


def _make_upstream(tmp_path) -> tuple[str, str]:
    """Create a bare 'remote' with one commit on 'main'. Returns (bare_url, default_branch)."""
    seed = tmp_path / "seed"
    seed.mkdir()
    repo = Repo.init(seed)
    (seed / "README.md").write_text("# Seed\n")
    repo.index.add(["README.md"])
    repo.index.commit("init", author=Actor("t", "t@e.c"), committer=Actor("t", "t@e.c"))
    repo.git.branch("-M", "main")

    bare = tmp_path / "upstream.git"
    Repo.clone_from(str(seed), str(bare), bare=True)
    return str(bare), "main"


def test_pr_payload_always_draft():
    payload = build_pr_payload(title="t", body="b", head="user:branch", base="main")
    assert payload["draft"] is True
    assert payload["head"] == "user:branch"
    assert payload["base"] == "main"


def test_push_branch_creates_branch_with_change(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "workspace_dir", str(tmp_path / "ws"))
    bare_url, default_branch = _make_upstream(tmp_path)

    changes = [{"path": "docs/new.md", "action": "modify", "new_content": "# Hello\nchanged\n"}]
    push_branch(
        clone_url=bare_url,
        token=None,
        default_branch=default_branch,
        branch="osae/issue-1-abc",
        changes=changes,
        commit_message="docs: update",
        author=Actor("Suhani", "s@e.c"),
        workspace="pub-test",
    )

    bare = Repo(bare_url)
    assert "osae/issue-1-abc" in bare.heads
    # The pushed branch contains the new file with our content.
    blob = (bare.heads["osae/issue-1-abc"].commit.tree / "docs" / "new.md")
    assert "changed" in blob.data_stream.read().decode()


def test_push_branch_rejects_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "workspace_dir", str(tmp_path / "ws"))
    bare_url, default_branch = _make_upstream(tmp_path)
    # Writing README with identical content produces no diff.
    changes = [{"path": "README.md", "action": "modify", "new_content": "# Seed\n"}]
    with pytest.raises(GitHubWriteError):
        push_branch(
            clone_url=bare_url,
            token=None,
            default_branch=default_branch,
            branch="osae/noop",
            changes=changes,
            commit_message="noop",
            author=Actor("t", "t@e.c"),
            workspace="pub-noop",
        )


def test_auth_url_injects_token():
    url = github_writer._auth_url("https://github.com/owner/repo.git", "tok123")
    assert url == "https://x-access-token:tok123@github.com/owner/repo.git"
    assert github_writer._auth_url("https://github.com/o/r.git", None) == "https://github.com/o/r.git"


def test_branch_name_deterministic():
    class _I:
        github_number = 42

    class _T:
        id = "abcdef1234567890"

    assert github_writer.branch_name_for(_T(), _I()) == "osae/issue-42-abcdef12"
