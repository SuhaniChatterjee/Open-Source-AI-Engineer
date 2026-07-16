"""GitHub App auth + webhook tests — all offline (generated RSA keypair, no
network, no registered app)."""
from __future__ import annotations

import hashlib
import hmac
import json

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import settings
from app.services import github_app, webhook_service


@pytest.fixture
def rsa_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


# --- app JWT ---

def test_app_jwt_signed_and_verifiable(rsa_keypair, monkeypatch):
    private_pem, public_pem = rsa_keypair
    monkeypatch.setattr(settings, "github_app_id", "123456")
    monkeypatch.setattr(settings, "github_app_private_key", private_pem)

    assert github_app.is_configured() is True
    token = github_app.app_jwt()
    decoded = jwt.decode(token, public_pem, algorithms=["RS256"])
    assert decoded["iss"] == "123456"
    assert decoded["exp"] > decoded["iat"]


def test_not_configured_without_key(monkeypatch):
    monkeypatch.setattr(settings, "github_app_id", None)
    monkeypatch.setattr(settings, "github_app_private_key", None)
    monkeypatch.setattr(settings, "github_app_private_key_path", None)
    assert github_app.is_configured() is False
    with pytest.raises(RuntimeError):
        github_app.app_jwt()


def test_install_url(monkeypatch):
    monkeypatch.setattr(settings, "github_app_slug", "osae-bot")
    assert github_app.install_url() == "https://github.com/apps/osae-bot/installations/new"
    monkeypatch.setattr(settings, "github_app_slug", None)
    assert github_app.install_url() is None


# --- webhook signature ---

def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_signature_accepts_valid_rejects_tampered(monkeypatch):
    monkeypatch.setattr(settings, "github_webhook_secret", "shh")
    body = json.dumps({"zen": "keep it simple"}).encode()
    good = _sign("shh", body)
    assert webhook_service.verify_signature(body, good) is True
    # tampered body
    assert webhook_service.verify_signature(body + b"x", good) is False
    # wrong secret
    assert webhook_service.verify_signature(body, _sign("nope", body)) is False
    # missing / malformed
    assert webhook_service.verify_signature(body, None) is False
    assert webhook_service.verify_signature(body, "md5=abc") is False


def test_signature_rejected_when_no_secret(monkeypatch):
    monkeypatch.setattr(settings, "github_webhook_secret", None)
    body = b"{}"
    assert webhook_service.verify_signature(body, _sign("x", body)) is False


# --- webhook routing (in-memory SQLite) ---

@pytest.fixture
def db(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    url = f"sqlite:///{tmp_path/'wh.db'}"
    monkeypatch.setattr(settings, "database_url", url)
    from alembic import command
    from alembic.config import Config
    import os

    api_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(api_root, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(api_root, "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")

    engine = create_engine(url, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    return Session()


def _noop_schedule(*args, **kwargs):
    pass


def test_ping(db):
    assert webhook_service.dispatch(db, "ping", {}, _noop_schedule)["event"] == "ping"


def test_installation_created_then_deleted(db):
    from app.models import GitHubInstallation

    payload = {
        "action": "created",
        "installation": {
            "id": 999,
            "account": {"login": "octo", "type": "User"},
            "target_type": "User",
            "repository_selection": "all",
        },
        "sender": {"login": "octo"},
    }
    out = webhook_service.dispatch(db, "installation", payload, _noop_schedule)
    assert out["installation_id"] == 999
    row = db.query(GitHubInstallation).filter_by(installation_id=999).one()
    assert row.account_login == "octo"

    payload["action"] = "deleted"
    webhook_service.dispatch(db, "installation", payload, _noop_schedule)
    assert db.query(GitHubInstallation).filter_by(installation_id=999).first() is None


def test_push_reindexes_tracked_ready_repo(db):
    from app.models import IndexJob, Repository

    repo = Repository(full_name="octo/demo", clone_url="https://github.com/octo/demo.git", status="ready")
    db.add(repo)
    db.commit()

    scheduled = []
    out = webhook_service.dispatch(
        db,
        "push",
        {"repository": {"full_name": "octo/demo"}},
        lambda *a, **k: scheduled.append(a),
    )
    assert out["reindexed"] == 1
    assert scheduled  # run_indexing was enqueued
    db.refresh(repo)
    assert repo.status == "pending"
    assert db.query(IndexJob).filter_by(repository_id=repo.id).count() == 1


def test_issues_event_upserts_issue(db):
    from app.models import Issue, Repository

    repo = Repository(full_name="octo/demo", clone_url="x", status="ready")
    db.add(repo)
    db.commit()

    payload = {
        "action": "opened",
        "repository": {"full_name": "octo/demo"},
        "issue": {
            "number": 7,
            "title": "Bug",
            "body": "broken",
            "state": "open",
            "labels": [{"name": "bug"}],
            "user": {"login": "octo"},
            "html_url": "https://github.com/octo/demo/issues/7",
        },
    }
    out = webhook_service.dispatch(db, "issues", payload, _noop_schedule)
    assert out["updated"] == 1
    issue = db.query(Issue).filter_by(repository_id=repo.id, github_number=7).one()
    assert issue.title == "Bug"
    assert json.loads(issue.labels) == ["bug"]


def test_issues_event_ignores_pull_request(db):
    from app.models import Issue, Repository

    repo = Repository(full_name="octo/demo", clone_url="x", status="ready")
    db.add(repo)
    db.commit()
    payload = {
        "action": "opened",
        "repository": {"full_name": "octo/demo"},
        "issue": {"number": 8, "title": "PR", "pull_request": {"url": "x"}, "html_url": "x"},
    }
    out = webhook_service.dispatch(db, "issues", payload, _noop_schedule)
    assert out["updated"] == 0
    assert db.query(Issue).count() == 0
