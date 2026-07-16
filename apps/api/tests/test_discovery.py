"""Unit tests for the discovery query builder and opportunity scoring (offline)."""
from __future__ import annotations

from app.services import discovery_service
from app.services.discovery_service import (
    DEFAULT_LABELS,
    build_queries,
    score_opportunity,
)


def _values(languages=None, topics=None, labels=None, level="beginner"):
    return {
        "languages": languages or [],
        "topics": topics or [],
        "labels": labels or [],
        "experience_level": level,
    }


def test_default_labels_when_none_selected():
    queries = build_queries(_values())
    assert len(queries) == len(DEFAULT_LABELS)
    assert all("is:issue is:open" in q and "no:assignee" in q for q in queries)
    assert any('label:"good first issue"' in q for q in queries)


def test_query_includes_languages_and_topics():
    q = build_queries(_values(languages=["python", "typescript"], topics=["cli"], labels=["docs"]))
    assert len(q) == 1
    assert "language:python" in q[0] and "language:typescript" in q[0]
    assert "cli" in q[0]
    assert 'label:"docs"' in q[0]


def test_query_caps_labels_at_three():
    q = build_queries(_values(labels=["a", "b", "c", "d", "e"]))
    assert len(q) == 3


def _item(labels=None, comments=0, body=""):
    return {
        "labels": [{"name": n} for n in (labels or [])],
        "comments": comments,
        "body": body,
    }


def test_good_first_issue_scores_high():
    score, reasons = score_opportunity(
        _item(labels=["good first issue"], body="x" * 200), _values()
    )
    assert score >= 80
    assert any("beginner" in r for r in reasons)


def test_contested_sparse_issue_scores_lower():
    high, _ = score_opportunity(_item(labels=["good first issue"], body="x" * 200), _values())
    low, reasons = score_opportunity(_item(labels=[], comments=40, body=""), _values())
    assert low < high
    assert any("contested" in r or "sparse" in r for r in reasons)


def test_scores_clamped():
    s, _ = score_opportunity(
        _item(labels=["good first issue", "help wanted", "documentation"], body="x" * 300),
        _values(level="beginner"),
    )
    assert 0 <= s <= 100


def test_repo_parsed_from_item():
    full, html = discovery_service._repo_from_item(
        {
            "repository_url": "https://api.github.com/repos/pallets/click",
            "html_url": "https://github.com/pallets/click/issues/42",
        }
    )
    assert full == "pallets/click"
    assert html == "https://github.com/pallets/click"
