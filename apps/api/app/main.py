"""FastAPI application entry point for the OpenSource AI Engineer API."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    auth,
    chat,
    contributions,
    discovery,
    github_app,
    health,
    issues,
    providers,
    repos,
)
from app.core.config import settings
from app.core.startup_checks import verify_production
from app.db.session import init_db

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Refuse to boot with dev defaults on a public deployment.
    verify_production(settings)
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(providers.router, prefix=settings.api_v1_prefix)
app.include_router(repos.router, prefix=settings.api_v1_prefix)
app.include_router(issues.router, prefix=settings.api_v1_prefix)
app.include_router(contributions.router, prefix=settings.api_v1_prefix)
app.include_router(github_app.router, prefix=settings.api_v1_prefix)
app.include_router(discovery.router, prefix=settings.api_v1_prefix)
app.include_router(chat.router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health",
    }
