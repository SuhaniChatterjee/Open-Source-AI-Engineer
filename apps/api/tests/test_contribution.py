"""Unit tests for contribution categorization, confidence gating, and diffs."""
from __future__ import annotations

import json

from app.models import Issue
from app.services.contribution_service import (
    CONFIDENCE_THRESHOLD,
    _unified_diff,
    categorize,
    compute_confidence,
)


def _issue(labels=None, complexity=4, affected=None):
    return Issue(
        repository_id="r",
        github_number=1,
        title="t",
        labels=json.dumps(labels or []),
        html_url="https://github.com/x/y/issues/1",
        complexity_score=complexity,
        affected_files=json.dumps(affected or []),
    )


def test_categorize_safe_and_unsafe():
    assert categorize(_issue(labels=["documentation"])) == ("docs", True)
    assert categorize(_issue(labels=["tests"])) == ("test", True)
    assert categorize(_issue(labels=["bug"])) == ("bug", False)
    assert categorize(_issue(labels=["enhancement"])) == ("feature", False)
    assert categorize(_issue(labels=[])) == ("other", False)


def test_no_files_forces_zero_confidence():
    issue = _issue(labels=["documentation"], complexity=2)
    score, rationale = compute_confidence(issue, "docs", True, 0)
    assert score == 0
    assert score < CONFIDENCE_THRESHOLD  # would be gated to guidance


def test_easy_safe_single_file_is_high_confidence():
    issue = _issue(labels=["documentation"], complexity=2)
    score, _ = compute_confidence(issue, "docs", True, 1)
    assert score >= CONFIDENCE_THRESHOLD


def test_complex_feature_many_files_is_gated():
    issue = _issue(labels=["enhancement"], complexity=9)
    score, _ = compute_confidence(issue, "feature", False, 3)
    assert score < CONFIDENCE_THRESHOLD


def test_confidence_clamped():
    issue = _issue(labels=["documentation"], complexity=1)
    score, _ = compute_confidence(issue, "docs", True, 1)
    assert 0 <= score <= 100


def test_unified_diff_reflects_change():
    diff = _unified_diff("a.py", "line1\nline2\n", "line1\nCHANGED\nline2\n")
    assert "+CHANGED" in diff
    assert "a/a.py" in diff and "b/a.py" in diff
