"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UserOut(BaseModel):
    id: str
    login: str
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    llm_provider: str
    embedding_provider: str

    class Config:
        from_attributes = True


class AuthConfig(BaseModel):
    github_enabled: bool
    dev_login_enabled: bool


class DevLoginRequest(BaseModel):
    login: str = Field("dev", min_length=1, max_length=64)


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


class ProviderSettingsUpdate(BaseModel):
    llm_provider: str = Field(..., pattern="^(mock|openai|ollama)$")
    embedding_provider: str = Field(..., pattern="^(mock|openai|ollama)$")


class ProviderKeyUpdate(BaseModel):
    provider: str = Field(..., pattern="^(openai)$")
    api_key: str = Field(..., min_length=8)


class ProviderStatus(BaseModel):
    llm_provider: str
    embedding_provider: str
    configured_keys: dict[str, str]  # provider -> masked hint


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


class AffectedFile(BaseModel):
    path: str
    start_line: int
    end_line: int
    kind: str
    score: float


class IssueOut(BaseModel):
    id: str
    github_number: int
    title: str
    state: str
    labels: list[str] = []
    author: str | None = None
    comments_count: int
    html_url: str
    github_updated_at: str | None = None
    analysis_status: str
    complexity_score: int | None = None
    complexity_level: str | None = None
    estimated_hours: str | None = None
    suitability_score: int | None = None


class IssueDetailOut(IssueOut):
    body: str | None = None
    affected_files: list[AffectedFile] = []
    required_knowledge: list[str] = []
    strategy: str | None = None
    risks: list[str] = []
    analysis_provider: str | None = None


class IssueSyncResult(BaseModel):
    synced: int


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
