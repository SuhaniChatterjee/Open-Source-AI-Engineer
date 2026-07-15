"""Database engine, session factory, and FastAPI dependency."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# SQLite needs check_same_thread=False because indexing runs in a background
# thread. Postgres (the default) ignores this connect arg.
_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a session and closing it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables. For the MVP we use create_all; migrations come later."""
    # Import models so they register on the metadata before create_all.
    from app import models  # noqa: F401
    from app.db.base import Base

    Base.metadata.create_all(bind=engine)
