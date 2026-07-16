"""Open Source Discovery Engine.

Turns a user's PersonalizationProfile into GitHub issue-search queries, then
ranks the results by how good a contribution opportunity each is *for this
user* — favouring beginner-friendly, well-described, unclaimed, active issues.

Query building and scoring are pure functions (unit-tested offline); only
`find_opportunities` touches the network.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from app.models import PersonalizationProfile
from app.services import github_service

# Labels we search for when the user hasn't picked any — the canonical
# "come contribute here" signals.
DEFAULT_LABELS = ["good first issue", "help wanted"]

_EASY_LABELS = {"good first issue", "good-first-issue", "documentation", "docs", "starter"}
_HELP_LABELS = {"help wanted", "help-wanted"}


@dataclass
class Opportunity:
    repo_full_name: str
    repo_url: str
    number: int
    title: str
    html_url: str
    labels: list[str]
    comments: int
    body_preview: str
    created_at: str | None
    updated_at: str | None
    fit_score: int
    reasons: list[str]


def _list(field: str | None) -> list[str]:
    try:
        return [x for x in json.loads(field or "[]") if x]
    except json.JSONDecodeError:
        return []


def profile_values(profile: PersonalizationProfile | None) -> dict:
    return {
        "languages": _list(profile.languages) if profile else [],
        "topics": _list(profile.topics) if profile else [],
        "labels": _list(profile.labels) if profile else [],
        "experience_level": profile.experience_level if profile else "beginner",
    }


def build_queries(values: dict) -> list[str]:
    """One query per label (OR semantics via separate searches), each scoped by
    languages + free-text topics. Capped to keep API usage sane."""
    labels = values["labels"] or DEFAULT_LABELS
    base_parts = ["is:issue", "is:open", "archived:false", "no:assignee"]
    for lang in values["languages"][:4]:
        base_parts.append(f"language:{lang}")
    base = " ".join(base_parts)
    topics = " ".join(values["topics"][:4]).strip()

    queries: list[str] = []
    for label in labels[:3]:
        q = f'{base} label:"{label}"'
        if topics:
            q += f" {topics}"
        queries.append(q)
    return queries


def _repo_from_item(item: dict) -> tuple[str, str]:
    # search/issues items carry repository_url like .../repos/{owner}/{name}
    repo_url = item.get("repository_url", "")
    full = repo_url.split("/repos/", 1)[-1] if "/repos/" in repo_url else ""
    html = item.get("html_url", "")
    repo_html = html.rsplit("/issues/", 1)[0] if "/issues/" in html else repo_url
    return full, repo_html


def score_opportunity(item: dict, values: dict) -> tuple[int, list[str]]:
    labels = {l["name"].lower() for l in item.get("labels", [])}
    reasons: list[str] = []
    score = 55

    if labels & _EASY_LABELS:
        score += 22
        reasons.append("beginner-friendly label")
    if labels & _HELP_LABELS:
        score += 10
        reasons.append("maintainers want help")

    comments = item.get("comments", 0)
    if comments == 0:
        score += 10
        reasons.append("unclaimed (no discussion yet)")
    elif comments > 15:
        score -= 8
        reasons.append("long discussion — may be contested")

    body = item.get("body") or ""
    if len(body) > 120:
        score += 8
        reasons.append("well described")
    elif not body.strip():
        score -= 8
        reasons.append("sparse description")

    level = values.get("experience_level", "beginner")
    if level == "advanced" and not (labels & _EASY_LABELS):
        score += 6
        reasons.append("matches your advanced level")
    if level == "beginner" and (labels & _EASY_LABELS):
        score += 6

    return max(0, min(100, score)), reasons


def _to_opportunity(item: dict, values: dict) -> Opportunity:
    full, repo_html = _repo_from_item(item)
    score, reasons = score_opportunity(item, values)
    body = item.get("body") or ""
    return Opportunity(
        repo_full_name=full,
        repo_url=repo_html,
        number=item.get("number", 0),
        title=item.get("title", ""),
        html_url=item.get("html_url", ""),
        labels=[l["name"] for l in item.get("labels", [])],
        comments=item.get("comments", 0),
        body_preview=body[:280],
        created_at=item.get("created_at"),
        updated_at=item.get("updated_at"),
        fit_score=score,
        reasons=reasons,
    )


def find_opportunities(
    profile: PersonalizationProfile | None, limit: int = 30
) -> list[Opportunity]:
    values = profile_values(profile)
    seen: dict[tuple[str, int], Opportunity] = {}
    for query in build_queries(values):
        for item in github_service.search_issues(query, per_page=20):
            if "pull_request" in item:
                continue
            opp = _to_opportunity(item, values)
            key = (opp.repo_full_name, opp.number)
            # Keep the higher-scoring instance if a dupe appears across queries.
            if key not in seen or opp.fit_score > seen[key].fit_score:
                seen[key] = opp
    ranked = sorted(seen.values(), key=lambda o: o.fit_score, reverse=True)
    return ranked[:limit]
