from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import sign_session
from app.db.session import get_db
from app.models import User
from app.schemas import AuthConfig, DevLoginRequest, OAuthCallbackRequest, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

_STATE_SALT = "osae.oauth.state.v1"
_STATE_MAX_AGE = 600  # 10 minutes


def _state_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.session_secret, salt=_STATE_SALT)


def _github_enabled() -> bool:
    return bool(settings.github_client_id and settings.github_client_secret)


def _set_session_cookie(response: Response, user_id: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=sign_session(user_id),
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path="/",
    )


@router.get("/config", response_model=AuthConfig)
def auth_config() -> AuthConfig:
    return AuthConfig(
        github_enabled=_github_enabled(),
        dev_login_enabled=settings.allow_dev_login,
    )


@router.get("/github/login")
def github_login() -> RedirectResponse:
    if not _github_enabled():
        raise HTTPException(status_code=400, detail="GitHub OAuth is not configured")
    state = _state_serializer().dumps(secrets.token_urlsafe(16))
    return RedirectResponse(auth_service.build_authorize_url(state))


@router.post("/github/callback", response_model=UserOut)
def github_callback(
    payload: OAuthCallbackRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    if not _github_enabled():
        raise HTTPException(status_code=400, detail="GitHub OAuth is not configured")
    try:
        _state_serializer().loads(payload.state, max_age=_STATE_MAX_AGE)
    except (BadSignature, SignatureExpired) as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired state") from exc

    try:
        token = auth_service.exchange_code_for_token(payload.code)
        profile = auth_service.fetch_github_user(token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"GitHub login failed: {exc}") from exc

    github_id = str(profile["id"])
    user = db.scalar(select(User).where(User.github_id == github_id))
    if not user:
        user = User(github_id=github_id, login=profile["login"])
        db.add(user)
    user.login = profile.get("login", user.login)
    user.name = profile.get("name")
    user.email = profile.get("email")
    user.avatar_url = profile.get("avatar_url")
    db.commit()
    db.refresh(user)

    _set_session_cookie(response, user.id)
    return user


@router.post("/dev-login", response_model=UserOut)
def dev_login(
    payload: DevLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    if not settings.allow_dev_login:
        raise HTTPException(status_code=403, detail="Dev login is disabled")
    login = payload.login.strip() or "dev"
    user = db.scalar(select(User).where(User.login == login, User.github_id.is_(None)))
    if not user:
        user = User(login=login, name=f"{login} (dev)")
        db.add(user)
        db.commit()
        db.refresh(user)
    _set_session_cookie(response, user.id)
    return user


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(settings.session_cookie_name, path="/")
    return {"ok": True}
