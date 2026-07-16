"""Read-only GitHub REST helpers for public repositories.

For the MVP we hit the public API unauthenticated (60 req/hr) or with an
optional server-level GITHUB_TOKEN. Per-installation tokens via the GitHub App
are a later phase (docs/GitHub-App-Design.md).
"""
from __future__ import annotations

import os

import httpx

from app.core.config import settings


class GitHubError(Exception):
    pass


def _headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def search_issues(query: str, per_page: int = 30, sort: str = "updated") -> list[dict]:
    """Search issues across GitHub. Returns raw search result items."""
    resp = httpx.get(
        f"{settings.github_api_url}/search/issues",
        headers=_headers(),
        params={
            "q": query,
            "per_page": min(per_page, 100),
            "sort": sort,
            "order": "desc",
        },
        timeout=30,
    )
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        raise GitHubError(
            "GitHub search rate limit reached. Set GITHUB_TOKEN or try again shortly."
        )
    resp.raise_for_status()
    return resp.json().get("items", [])


def fetch_open_issues(full_name: str, limit: int = 50) -> list[dict]:
    """Fetch open issues (excluding pull requests) for a public repo."""
    resp = httpx.get(
        f"{settings.github_api_url}/repos/{full_name}/issues",
        headers=_headers(),
        params={
            "state": "open",
            "per_page": min(limit, 100),
            "sort": "updated",
            "direction": "desc",
        },
        timeout=30,
    )
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        raise GitHubError(
            "GitHub API rate limit reached. Set GITHUB_TOKEN or try again later."
        )
    if resp.status_code == 404:
        raise GitHubError(f"Repository {full_name} not found on GitHub.")
    resp.raise_for_status()

    issues = []
    for item in resp.json():
        if "pull_request" in item:  # the issues endpoint also returns PRs
            continue
        issues.append(
            {
                "number": item["number"],
                "title": item["title"],
                "body": item.get("body") or "",
                "state": item["state"],
                "labels": [l["name"] for l in item.get("labels", [])],
                "author": (item.get("user") or {}).get("login"),
                "comments_count": item.get("comments", 0),
                "html_url": item["html_url"],
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            }
        )
    return issues
