"""The production config gate must fail closed.

These tests encode the deployment blockers: if any of them start passing with
insecure settings, the app could be deployed wide open.
"""
from __future__ import annotations

import pytest

from app.core.config import DEFAULT_SESSION_SECRET, Settings
from app.core.startup_checks import (
    InsecureConfigError,
    collect_production_errors,
    verify_production,
)


def _safe_prod(**overrides) -> Settings:
    base = dict(
        environment="production",
        allow_dev_login=False,
        session_secret="a-real-long-random-secret-value-9f2c",
        encryption_key="8Yl0Z8mWZ0mVQ0m0m0m0m0m0m0m0m0m0m0m0m0m0m0M=",
        session_cookie_secure=True,
        session_cookie_samesite="none",
        database_url="postgresql+psycopg://u:p@db.example.com/osae",
        github_client_id="cid",
        github_client_secret="csecret",
        cors_origins=["https://app.example.com"],
    )
    base.update(overrides)
    return Settings(**base)


def test_safe_production_config_passes():
    verify_production(_safe_prod())  # must not raise


def test_development_is_never_gated():
    # Dev keeps its permissive defaults.
    verify_production(Settings(environment="development"))


def test_dev_login_blocks_production():
    errors = collect_production_errors(_safe_prod(allow_dev_login=True))
    assert any("ALLOW_DEV_LOGIN" in e for e in errors)
    with pytest.raises(InsecureConfigError):
        verify_production(_safe_prod(allow_dev_login=True))


def test_default_session_secret_blocks_production():
    errors = collect_production_errors(_safe_prod(session_secret=DEFAULT_SESSION_SECRET))
    assert any("SESSION_SECRET" in e for e in errors)


def test_missing_encryption_key_blocks_production():
    errors = collect_production_errors(_safe_prod(encryption_key=None))
    assert any("ENCRYPTION_KEY" in e for e in errors)


def test_insecure_cookie_blocks_production():
    errors = collect_production_errors(_safe_prod(session_cookie_secure=False))
    assert any("SESSION_COOKIE_SECURE" in e for e in errors)


def test_sqlite_blocks_production():
    errors = collect_production_errors(_safe_prod(database_url="sqlite:///./dev.db"))
    assert any("SQLite" in e for e in errors)


def test_missing_oauth_blocks_production():
    errors = collect_production_errors(_safe_prod(github_client_id=None))
    assert any("GITHUB_CLIENT_ID" in e for e in errors)


def test_localhost_cors_blocks_production():
    errors = collect_production_errors(_safe_prod(cors_origins=["http://localhost:3000"]))
    assert any("CORS_ORIGINS" in e for e in errors)


def test_all_errors_reported_together():
    # A totally default prod config should surface every blocker at once.
    errors = collect_production_errors(Settings(environment="production"))
    assert len(errors) >= 6


# --- env parsing / normalization used by hosting platforms ---

def test_cors_origins_accepts_comma_separated_env():
    s = Settings(cors_origins="https://a.vercel.app, https://b.vercel.app")
    assert s.cors_origins == ["https://a.vercel.app", "https://b.vercel.app"]


@pytest.mark.parametrize(
    "given",
    ["postgres://u:p@h/db", "postgresql://u:p@h/db"],
)
def test_managed_postgres_url_normalized(given):
    # Render/Heroku hand out postgres:// which SQLAlchemy 2 rejects.
    assert Settings(database_url=given).database_url.startswith("postgresql+psycopg://")
