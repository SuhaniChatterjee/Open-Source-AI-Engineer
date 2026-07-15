"""GitHub OAuth (user-to-server) helpers.

Exchanges an authorization code for an access token and fetches the GitHub
user profile. The access token is used once at login to identify the user and
is not persisted for the MVP (repo access uses public clone; the GitHub App
installation flow for private repos is a later phase — see
docs/GitHub-App-Design.md).
"""
from __future__ import annotations

import httpx

from app.core.config import settings


class OAuthError(Exception):
    pass


def build_authorize_url(state: str) -> str:
    from urllib.parse import urlencode

    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": f"{settings.frontend_url}/auth/callback",
        "scope": settings.github_oauth_scope,
        "state": state,
    }
    return f"https://github.com/login/oauth/authorize?{urlencode(params)}"


def exchange_code_for_token(code: str) -> str:
    resp = httpx.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
            "redirect_uri": f"{settings.frontend_url}/auth/callback",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise OAuthError(data.get("error_description", "token exchange failed"))
    return token


def fetch_github_user(token: str) -> dict:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    user = httpx.get(f"{settings.github_api_url}/user", headers=headers, timeout=30)
    user.raise_for_status()
    profile = user.json()

    if not profile.get("email"):
        emails = httpx.get(
            f"{settings.github_api_url}/user/emails", headers=headers, timeout=30
        )
        if emails.status_code == 200:
            primary = next(
                (e for e in emails.json() if e.get("primary")), None
            )
            if primary:
                profile["email"] = primary.get("email")
    return profile
