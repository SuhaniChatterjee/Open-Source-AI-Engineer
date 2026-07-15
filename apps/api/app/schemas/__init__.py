"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RepoCreate(BaseModel):
    # Accept "owner/name" or a full GitHub URL.
    repo: str = Field(..., examples=["tiangolo/fastapi"])


class RepoOut(BaseModel):
    id: str
    full_name: str
    clone_url: str
    default_branch: str
    status: str
    file_count: int
    chunk_count: int
    readme_summary: str | None = None
    error: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class IndexJobOut(BaseModel):
    id: str
    repository_id: str
    status: str
    stage: str | None
    progress: int
    error: str | None = None

    class Config:
        from_attributes = True


class CitationOut(BaseModel):
    path: str
    start_line: int
    end_line: int
    kind: str
    score: float


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2)
    top_k: int = Field(8, ge=1, le=20)


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
    provider: str
