"""Personalization engine: affinities learned from activity, outcome-weighted,
and their effect on discovery ranking + query expansion."""
from __future__ import annotations

import json
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models import ContributionTask, Issue, Repository, User
from app.services import discovery_service, personalization_service


@pytest.fixture
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path/'p.db'}"
    monkeypatch.setattr(settings, "database_url", url)
    from alembic import command
    from alembic.config import Config

    api_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(api_root, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(api_root, "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    engine = create_engine(url, connect_args={"check_same_thread": False})
    return sessionmaker(bind=engine)()


def _seed(db):
    user = User(login="dev")
    db.add(user)
    db.commit()
    db.refresh(user)

    repo = Repository(
        full_name="pallets/click",
        clone_url="x",
        status="ready",
        owner_id=user.id,
        languages=json.dumps({".py": 40, ".md": 10}),
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    # An analyzed docs issue + a published contribution on a bug issue.
    docs_issue = Issue(
        repository_id=repo.id, github_number=1, title="docs", html_url="x",
        labels=json.dumps(["documentation"]), analysis_status="analyzed",
    )
    bug_issue = Issue(
        repository_id=repo.id, github_number=2, title="bug", html_url="x",
        labels=json.dumps(["bug"]), analysis_status="analyzed",
    )
    db.add_all([docs_issue, bug_issue])
    db.commit()
    db.refresh(bug_issue)

    task = ContributionTask(
        repository_id=repo.id, issue_id=bug_issue.id, owner_id=user.id,
        status="approved", publish_status="published",
    )
    db.add(task)
    db.commit()
    return user


def test_signals_learn_languages_and_labels(db):
    user = _seed(db)
    signals = personalization_service.compute_signals(db, user)

    assert "python" in signals.top_languages()
    assert signals.stats["repos_indexed"] == 1
    assert signals.stats["issues_analyzed"] == 2
    assert signals.stats["pull_requests_opened"] == 1

    # 'bug' had a published PR (weight 6) vs 'documentation' only analyzed
    # (weight 1) -> bug ranks higher.
    label_rank = [name for name, _ in signals.labels]
    assert label_rank.index("bug") < label_rank.index("documentation")


def test_no_history_is_empty(db):
    user = User(login="fresh")
    db.add(user)
    db.commit()
    signals = personalization_service.compute_signals(db, user)
    assert not signals.has_history
    assert signals.stats["repos_indexed"] == 0


def test_signals_boost_matching_opportunity():
    signals = personalization_service.Signals(labels=[("bug", 1.0), ("cli", 0.5)])
    values = {"languages": [], "topics": [], "labels": [], "experience_level": "beginner"}
    item = {"labels": [{"name": "bug"}], "comments": 0, "body": "x" * 200}
    boosted, reasons = discovery_service.score_opportunity(item, values, signals)
    plain, _ = discovery_service.score_opportunity(item, values, None)
    assert boosted > plain
    assert any("history" in r for r in reasons)


def test_query_expands_from_signals_when_prefs_empty():
    signals = personalization_service.Signals(
        languages=[("python", 1.0), ("go", 0.4)],
        topics=[("parser", 1.0)],
    )
    values = {"languages": [], "topics": [], "labels": [], "experience_level": "beginner"}
    queries = discovery_service.build_queries(values, signals)
    assert any("language:python" in q for q in queries)
    assert any("parser" in q for q in queries)


def test_suggestions_exclude_existing_prefs():
    signals = personalization_service.Signals(
        languages=[("python", 1.0), ("go", 0.5)],
        labels=[("bug", 1.0)],
    )
    sugg = personalization_service.suggestions(
        signals, {"languages": ["python"], "labels": []}
    )
    assert "python" not in sugg["languages"]
    assert "go" in sugg["languages"]
    assert "bug" in sugg["labels"]
