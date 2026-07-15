from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import encrypt_secret, mask_secret
from app.db.session import get_db
from app.models import ProviderCredential, User
from app.schemas import ProviderKeyUpdate, ProviderSettingsUpdate, ProviderStatus

router = APIRouter(prefix="/providers", tags=["providers"])


def _status(db: Session, user: User) -> ProviderStatus:
    creds = db.scalars(
        select(ProviderCredential).where(ProviderCredential.user_id == user.id)
    ).all()
    return ProviderStatus(
        llm_provider=user.llm_provider,
        embedding_provider=user.embedding_provider,
        configured_keys={c.provider: c.hint for c in creds},
    )


@router.get("", response_model=ProviderStatus)
def get_providers(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _status(db, user)


@router.put("/settings", response_model=ProviderStatus)
def update_settings(
    payload: ProviderSettingsUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.llm_provider = payload.llm_provider
    user.embedding_provider = payload.embedding_provider
    db.commit()
    db.refresh(user)
    return _status(db, user)


@router.put("/keys", response_model=ProviderStatus)
def set_key(
    payload: ProviderKeyUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cred = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.user_id == user.id,
            ProviderCredential.provider == payload.provider,
        )
    )
    if not cred:
        cred = ProviderCredential(user_id=user.id, provider=payload.provider)
        db.add(cred)
    cred.encrypted_key = encrypt_secret(payload.api_key)
    cred.hint = mask_secret(payload.api_key)
    db.commit()
    return _status(db, user)


@router.delete("/keys/{provider}", response_model=ProviderStatus)
def delete_key(
    provider: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cred = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.user_id == user.id,
            ProviderCredential.provider == provider,
        )
    )
    if cred:
        db.delete(cred)
        db.commit()
    return _status(db, user)
