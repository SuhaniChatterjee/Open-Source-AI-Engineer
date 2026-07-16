"""Personalization engine.

Learns what a developer actually engages with — from their indexed repos,
analyzed issues, and (most importantly) contribution *outcomes* — and turns it
into affinity signals that improve discovery over time. The model is a
transparent, outcome-weighted tally computed from live data (no training, no
stale state): the more you do, and the more of it lands as pull requests, the
stronger the signal.

Weights escalate with commitment/success:
    indexed repo language        +1
    analyzed issue label         +1
    drafted contribution         +2   (labels; repo language x0.5)
    approved contribution        +4
    published PR                 +6
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ContributionTask, Issue, Repository, User

_EXT_LANG = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".md": "documentation",
}

_STOP_TOKENS = {"the", "app", "lib", "core", "python", "js", "api", "cli", "www", "com", "io"}

_W_DRAFT = 2
_W_APPROVED = 4
_W_PUBLISHED = 6


@dataclass
class Signals:
    languages: list[tuple[str, float]] = field(default_factory=list)
    labels: list[tuple[str, float]] = field(default_factory=list)
    topics: list[tuple[str, float]] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def top_languages(self, n: int = 4) -> list[str]:
        return [k for k, _ in self.languages[:n]]

    def top_labels(self, n: int = 6) -> set[str]:
        return {k for k, _ in self.labels[:n]}

    def top_topics(self, n: int = 4) -> list[str]:
        return [k for k, _ in self.topics[:n]]

    @property
    def has_history(self) -> bool:
        return bool(self.languages or self.labels)


def _labels_of(issue: Issue) -> list[str]:
    try:
        return [l.lower() for l in json.loads(issue.labels or "[]")]
    except json.JSONDecodeError:
        return []


def _repo_languages(repo: Repository) -> list[str]:
    try:
        counts = json.loads(repo.languages or "{}")
    except json.JSONDecodeError:
        return []
    langs: list[str] = []
    for ext in counts:
        lang = _EXT_LANG.get(ext)
        if lang and lang not in langs:
            langs.append(lang)
    return langs


def _name_tokens(full_name: str) -> list[str]:
    name = full_name.split("/")[-1]
    toks = re.split(r"[-_.\s]+", name.lower())
    return [t for t in toks if len(t) > 2 and t not in _STOP_TOKENS]


def _normalize(counter: Counter) -> list[tuple[str, float]]:
    if not counter:
        return []
    top = max(counter.values())
    return sorted(
        ((k, round(v / top, 3)) for k, v in counter.items()),
        key=lambda kv: kv[1],
        reverse=True,
    )


def compute_signals(db: Session, user: User) -> Signals:
    lang_w: Counter = Counter()
    label_w: Counter = Counter()
    topic_w: Counter = Counter()

    repos = db.scalars(
        select(Repository).where(Repository.owner_id == user.id)
    ).all()
    repo_by_id = {r.id: r for r in repos}
    for repo in repos:
        for lang in _repo_languages(repo):
            lang_w[lang] += 1
        for tok in _name_tokens(repo.full_name):
            topic_w[tok] += 0.5

    repo_ids = list(repo_by_id.keys())
    analyzed = 0
    if repo_ids:
        issues = db.scalars(
            select(Issue).where(
                Issue.repository_id.in_(repo_ids),
                Issue.analysis_status == "analyzed",
            )
        ).all()
        analyzed = len(issues)
        for issue in issues:
            for label in _labels_of(issue):
                label_w[label] += 1

    tasks = db.scalars(
        select(ContributionTask).where(ContributionTask.owner_id == user.id)
    ).all()
    drafted = approved = published = 0
    for task in tasks:
        if task.publish_status == "published":
            weight = _W_PUBLISHED
            published += 1
        elif task.status == "approved":
            weight = _W_APPROVED
            approved += 1
        else:
            weight = _W_DRAFT
            drafted += 1
        issue = db.get(Issue, task.issue_id)
        if issue:
            for label in _labels_of(issue):
                label_w[label] += weight
        repo = repo_by_id.get(task.repository_id)
        if repo:
            for lang in _repo_languages(repo):
                lang_w[lang] += weight * 0.5

    stats = {
        "repos_indexed": len(repos),
        "issues_analyzed": analyzed,
        "contributions_drafted": drafted,
        "contributions_approved": approved,
        "pull_requests_opened": published,
    }
    return Signals(
        languages=_normalize(lang_w),
        labels=_normalize(label_w),
        topics=_normalize(topic_w),
        stats=stats,
    )


def suggestions(signals: Signals, prefs: dict) -> dict:
    """Learned languages/labels not yet in the user's explicit preferences."""
    have_langs = {l.lower() for l in prefs.get("languages", [])}
    have_labels = {l.lower() for l in prefs.get("labels", [])}
    return {
        "languages": [l for l in signals.top_languages(4) if l not in have_langs],
        "labels": [l for l in sorted(signals.top_labels(6)) if l not in have_labels],
    }
