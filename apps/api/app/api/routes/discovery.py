from __future__ import annotations

import json
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import PersonalizationProfile, User
from app.schemas import OpportunityOut, PreferencesOut, PreferencesUpdate
from app.services import discovery_service
from app.services.github_service import GitHubError

router = APIRouter(prefix="/discovery", tags=["discovery"])


def _profile(db: Session, user: User) -> PersonalizationProfile | None:
    return db.scalar(
        select(PersonalizationProfile).where(PersonalizationProfile.user_id == user.id)
    )


def _prefs_out(profile: PersonalizationProfile | None) -> PreferencesOut:
    v = discovery_service.profile_values(profile)
    return PreferencesOut(**v)


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _prefs_out(_profile(db, user))


@router.put("/preferences", response_model=PreferencesOut)
def update_preferences(
    payload: PreferencesUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile(db, user)
    if not profile:
        profile = PersonalizationProfile(user_id=user.id)
        db.add(profile)
    profile.languages = json.dumps(payload.languages)
    profile.topics = json.dumps(payload.topics)
    profile.experience_level = payload.experience_level
    profile.labels = json.dumps(payload.labels)
    db.commit()
    db.refresh(profile)
    return _prefs_out(profile)


@router.get("/opportunities", response_model=list[OpportunityOut])
def opportunities(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    profile = _profile(db, user)
    try:
        found = discovery_service.find_opportunities(profile)
    except GitHubError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [asdict(o) for o in found]
