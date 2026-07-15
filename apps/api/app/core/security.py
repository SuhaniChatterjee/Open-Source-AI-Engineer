"""Session token signing and symmetric encryption for stored secrets.

- Session cookies carry a signed, timestamped user id (itsdangerous). No server
  session store needed for the MVP.
- Provider API keys are encrypted at rest with Fernet before hitting the DB and
  are never returned to the client in plaintext.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import settings

_SALT = "osae.session.v1"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.session_secret, salt=_SALT)


def sign_session(user_id: str) -> str:
    return _serializer().dumps({"uid": user_id})


def verify_session(token: str) -> str | None:
    """Return the user id from a session token, or None if invalid/expired."""
    try:
        data = _serializer().loads(token, max_age=settings.session_max_age_seconds)
        return data.get("uid")
    except (BadSignature, SignatureExpired):
        return None


def _fernet() -> Fernet:
    key = settings.encryption_key
    if not key:
        # Derive a stable dev key from the session secret. NOT for production.
        digest = hashlib.sha256(settings.session_secret.encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str | None:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return None


def mask_secret(plaintext: str) -> str:
    """A safe hint to show in the UI, e.g. 'sk-…a1b2'."""
    if len(plaintext) <= 6:
        return "•" * len(plaintext)
    return f"{plaintext[:3]}…{plaintext[-4:]}"
