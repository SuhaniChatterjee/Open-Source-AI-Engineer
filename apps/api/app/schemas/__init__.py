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
    llm_provider: str = Field(..., pattern="^(mock|openai|gemini|ollama)$")
    embedding_provider: str = Field(..., pattern="^(mock|openai|gemini|ollama)$")


class ProviderKeyUpdate(BaseModel):
    # "github" stores a write token used only for publishing pull requests.
    provider: str = Field(..., pattern="^(openai|gemini|github)$")
    api_key: str = Field(..., min_length=8)


class ProviderStatus(BaseModel):
    llm_provider: str
    embedding_provider: str
    configured_keys: dict[str, str]  # provider -> masked hint


class PreferencesOut(BaseModel):
    languages: list[str] = []
    topics: list[str] = []
    experience_level: str = "beginner"
    labels: list[str] = []


class PreferencesUpdate(BaseModel):
    languages: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    experience_level: str = Field("beginner", pattern="^(beginner|intermediate|advanced)$")
    labels: list[str] = Field(default_factory=list)


class AffinityOut(BaseModel):
    name: str
    weight: float


class InsightsOut(BaseModel):
    languages: list[AffinityOut] = []
    labels: list[AffinityOut] = []
    topics: list[AffinityOut] = []
    stats: dict = {}
    suggestions: dict = {}
    has_history: bool = False


class OpportunityOut(BaseModel):
    repo_full_name: str
    repo_url: str
    number: int
    title: str
    html_url: str
    labels: list[str] = []
    comments: int
    body_preview: str
    created_at: str | None = None
    updated_at: str | None = None
    fit_score: int
    reasons: list[str] = []


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


class ProposedChange(BaseModel):
    path: str
    action: str
    original_content: str
    new_content: str
    diff: str
    note: str | None = None


class ContributionOut(BaseModel):
    id: str
    repository_id: str
    issue_id: str
    issue_number: int | None = None
    status: str
    stage: str | None = None
    category: str | None = None
    is_safe_category: bool
    summary: str | None = None
    plan: list[str] = []
    proposed_changes: list[ProposedChange] = []
    test_plan: str | None = None
    risks: list[str] = []
    confidence_score: int | None = None
    confidence_rationale: str | None = None
    guidance: str | None = None
    commit_message: str | None = None
    pr_title: str | None = None
    pr_body: str | None = None
    provider: str | None = None
    reviewer_note: str | None = None
    error: str | None = None
    publish_status: str = "none"
    branch_name: str | None = None
    pr_number: int | None = None
    pr_url: str | None = None
    pr_head_repo: str | None = None
    publish_error: str | None = None


class ContributionReview(BaseModel):
    approve: bool
    note: str | None = None


class PublishPreviewOut(BaseModel):
    branch_name: str
    base: str
    head: str
    files: list[str]
    commit_message: str
    pr_title: str
    pr_body: str
    head_repo: str
    token_configured: bool


class PublishRequest(BaseModel):
    confirm: bool
    # Optional "owner/name" of the user's fork to push to and open the PR from.
    head_repo: str | None = None


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
