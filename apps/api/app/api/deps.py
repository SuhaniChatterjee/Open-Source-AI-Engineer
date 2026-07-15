"""Shared FastAPI dependencies for authentication."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_session
from app.db.session import get_db
from app.models import User


def _user_from_request(request: Request, db: Session) -> User | None:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    user_id = verify_session(token)
    if not user_id:
        return None
    return db.get(User, user_id)


def get_optional_user(
    request: Request, db: Session = Depends(get_db)
) -> User | None:
    return _user_from_request(request, db)


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    user = _user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
