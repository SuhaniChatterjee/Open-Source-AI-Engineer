"""Fail-closed production configuration checks.

The app ships with permissive defaults so local dev is zero-config. Those same
defaults are dangerous on a public URL, so when ENVIRONMENT=production the app
refuses to start unless they've been replaced. Failing to boot is the correct
outcome — the alternative is quietly serving a wide-open auth bypass.
"""
from __future__ import annotations

import logging

from app.core.config import DEFAULT_SESSION_SECRET, Settings

logger = logging.getLogger(__name__)


class InsecureConfigError(RuntimeError):
    pass


def collect_production_errors(s: Settings) -> list[str]:
    errors: list[str] = []

    # The single most dangerous setting: dev-login authenticates as ANY user
    # with no password. On a public URL that is a total account takeover.
    if s.allow_dev_login:
        errors.append(
            "ALLOW_DEV_LOGIN must be false in production — it lets anyone sign "
            "in as any user without a password."
        )

    if s.session_secret == DEFAULT_SESSION_SECRET:
        errors.append(
            "SESSION_SECRET is still the public default from the repo — anyone "
            "could forge session cookies. Set a long random value."
        )

    if not s.encryption_key:
        errors.append(
            "ENCRYPTION_KEY must be set in production. Without it, stored "
            "provider/GitHub tokens are encrypted with a key derived from "
            "SESSION_SECRET. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; "
            'print(Fernet.generate_key().decode())"'
        )

    if not s.session_cookie_secure:
        errors.append("SESSION_COOKIE_SECURE must be true in production (HTTPS).")

    if s.session_cookie_samesite.lower() == "none" and not s.session_cookie_secure:
        errors.append("SESSION_COOKIE_SAMESITE=none requires SESSION_COOKIE_SECURE=true.")

    if s.database_url.startswith("sqlite"):
        errors.append(
            "DATABASE_URL points at SQLite. Use managed Postgres in production — "
            "hosting filesystems are ephemeral."
        )

    # With dev-login correctly disabled, OAuth is the only way in.
    if not (s.github_client_id and s.github_client_secret):
        errors.append(
            "GITHUB_CLIENT_ID/GITHUB_CLIENT_SECRET must be set — with dev-login "
            "disabled, GitHub OAuth is the only way to sign in."
        )

    origins = s.cors_origins_list
    if not origins or any("localhost" in o for o in origins):
        errors.append(
            "CORS_ORIGINS still contains localhost. Set it to your deployed "
            "frontend origin(s)."
        )

    return errors


def collect_production_warnings(s: Settings) -> list[str]:
    warnings: list[str] = []
    if s.qdrant_path and not s.qdrant_url.startswith(("http://", "https://")):
        warnings.append("Qdrant URL looks unset; embedded on-disk vectors do not survive redeploys.")
    if s.task_backend != "celery":
        warnings.append(
            "TASK_BACKEND=inline runs indexing inside the web process; set to "
            "'celery' and run a worker for production throughput."
        )
    return warnings


def verify_production(s: Settings) -> None:
    """Raise if the configuration is unsafe for a public deployment."""
    if s.environment.lower() != "production":
        return

    for warning in collect_production_warnings(s):
        logger.warning("config: %s", warning)

    errors = collect_production_errors(s)
    if errors:
        detail = "\n".join(f"  - {e}" for e in errors)
        raise InsecureConfigError(
            "Refusing to start: unsafe production configuration.\n" + detail
        )
    logger.info("Production configuration checks passed.")
