"""Unit tests for the deterministic issue-analysis heuristics."""
from __future__ import annotations

import json

from app.models import Issue
from app.services.issue_service import (
    derive_knowledge,
    derive_risks,
    hours_for,
    level_for,
    score_complexity,
    suitability_for,
)
from app.services.vectorstore import SearchHit


def _issue(labels: list[str] | None = None, body: str = "", comments: int = 0) -> Issue:
    return Issue(
        repository_id="r",
        github_number=1,
        title="t",
        body=body,
        labels=json.dumps(labels or []),
        comments_count=comments,
        html_url="https://github.com/x/y/issues/1",
    )


def _hit(path: str, score: float = 0.5) -> SearchHit:
    return SearchHit(path=path, start_line=1, end_line=10, kind="function", text="x", score=score)


def test_good_first_issue_scores_easy():
    issue = _issue(labels=["good first issue"], body="Fix the typo in README ```diff```")
    hits = [_hit("docs/index.md")]
    score = score_complexity(issue, hits)
    assert score <= 3
    assert level_for(score) == "easy"
    assert suitability_for(issue, score) >= 80


def test_cross_module_feature_scores_harder():
    issue = _issue(labels=["enhancement"], body="x" * 2000, comments=15)
    hits = [_hit("src/a.py"), _hit("web/b.ts"), _hit("infra/c.py"), _hit("docs/d.md"), _hit("tests/e.py")]
    score = score_complexity(issue, hits)
    assert score >= 7
    assert level_for(score) == "hard"
    assert hours_for(score) == "8–20h+"


def test_scores_clamped_to_range():
    trivial = _issue(labels=["typo", "good first issue", "help wanted"], body="```x```")
    assert 1 <= score_complexity(trivial, [_hit("a.md")]) <= 10
    brutal = _issue(labels=["breaking", "enhancement"], body="x" * 5000, comments=50)
    hits = [_hit(f"mod{i}/f.py") for i in range(5)]
    assert 1 <= score_complexity(brutal, hits) <= 10


def test_risks_flag_missing_tests_and_sparse_description():
    issue = _issue(labels=["bug"], body="short")
    risks = derive_risks(issue, [_hit("src/core.py")])
    joined = " ".join(risks).lower()
    assert "test" in joined
    assert "reproduce" in joined or "sparse" in joined


def test_knowledge_derived_from_hit_paths():
    hits = [_hit("src/click/parser.py"), _hit("docs/options.md")]
    knowledge = derive_knowledge(hits)
    assert "Python" in knowledge
    assert any(k.startswith("module:") for k in knowledge)
