"""Guardrail: the Alembic migrations must fully describe the models.

Applies all migrations to a fresh SQLite DB, then diffs the resulting schema
against the ORM metadata. Any added/removed table or column means a migration
is missing — the test fails so it can't be forgotten.
"""
from __future__ import annotations

import os

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.core.config import settings
from app.db.base import Base
from app import models  # noqa: F401  (register tables on metadata)

_STRUCTURAL = {"add_table", "remove_table", "add_column", "remove_column"}


def _alembic_config(url: str) -> Config:
    api_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(api_root, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(api_root, "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_migrations_match_models(tmp_path, monkeypatch):
    db_path = tmp_path / "drift.db"
    url = f"sqlite:///{db_path}"
    # env.py reads settings.database_url; point it at the temp DB.
    monkeypatch.setattr(settings, "database_url", url)

    command.upgrade(_alembic_config(url), "head")

    engine = create_engine(url)
    with engine.connect() as conn:
        ctx = MigrationContext.configure(
            conn, opts={"compare_type": True, "render_as_batch": True}
        )
        diffs = compare_metadata(ctx, Base.metadata)

    structural = [d for d in diffs if isinstance(d, tuple) and d[0] in _STRUCTURAL]
    assert not structural, f"Model/migration drift detected: {structural}"
