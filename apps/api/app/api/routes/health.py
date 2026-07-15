from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.providers.registry import get_embedding_provider, get_llm_provider
from app.services.vectorstore import get_vector_store

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "environment": settings.environment,
        "llm_provider": get_llm_provider().name,
        "embedding_provider": get_embedding_provider().name,
        "vector_store_mode": get_vector_store().mode,
    }
