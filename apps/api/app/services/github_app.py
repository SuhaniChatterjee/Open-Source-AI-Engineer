"""GitHub App authentication.

Two-legged auth:
1. Mint a short-lived app JWT (RS256, signed with the app private key).
2. Exchange it for an *installation access token* scoped to one installation.

Installation tokens are cached in-process until shortly before expiry. If the
app isn't configured, `is_configured()` is False and callers fall back to a
user PAT (see github_writer.resolve_write_token).
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

import httpx
import jwt

from app.core.config import settings

_token_cache: dict[int, tuple[str, float]] = {}
_lock = threading.Lock()


def is_configured() -> bool:
    return bool(settings.github_app_id and _private_key())


def install_url() -> str | None:
    if not settings.github_app_slug:
        return None
    return f"https://github.com/apps/{settings.github_app_slug}/installations/new"


def _private_key() -> str | None:
    if settings.github_app_private_key:
        return settings.github_app_private_key.replace("\\n", "\n")
    if settings.github_app_private_key_path:
        try:
            with open(settings.github_app_private_key_path, "r", encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return None
    return None


def app_jwt() -> str:
    """A signed JWT identifying the app (valid ~9 minutes)."""
    key = _private_key()
    if not settings.github_app_id or not key:
        raise RuntimeError("GitHub App is not configured")
    now = int(time.time())
    payload = {
        "iat": now - 60,  # allow for clock drift
        "exp": now + 9 * 60,  # GitHub max is 10 minutes
        "iss": settings.github_app_id,
    }
    return jwt.encode(payload, key, algorithm="RS256")


def installation_token(installation_id: int) -> str:
    """Return a cached or freshly-minted installation access token."""
    with _lock:
        cached = _token_cache.get(installation_id)
        if cached and cached[1] - 60 > time.time():
            return cached[0]

    resp = httpx.post(
        f"{settings.github_api_url}/app/installations/{installation_id}/access_tokens",
        headers={
            "Authorization": f"Bearer {app_jwt()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data["token"]
    expires = data.get("expires_at")
    exp_ts = (
        datetime.fromisoformat(expires.replace("Z", "+00:00")).timestamp()
        if expires
        else time.time() + 3600
    )
    with _lock:
        _token_cache[installation_id] = (token, exp_ts)
    return token
