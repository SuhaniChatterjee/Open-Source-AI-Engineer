"""ORM models for the MVP vertical slice.

The full data model (users, GitHub installations, contribution tasks, PRs,
provider credentials, autonomous runs, personalization profiles) is described
in docs/TRD.md. Here we implement the subset needed for the
index -> chat -> architecture-map flow.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    # GitHub numeric id as string; null for local dev-login users.
    github_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    login: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Which provider this user wants for chat/embeddings: mock | openai | ollama
    llm_provider: Mapped[str] = mapped_column(String(32), default="mock")
    embedding_provider: Mapped[str] = mapped_column(String(32), default="mock")

    repositories: Mapped[list["Repository"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    credentials: Mapped[list["ProviderCredential"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ProviderCredential(Base):
    __tablename__ = "provider_credentials"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_provider"),)

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(32))  # openai | ollama | ...
    encrypted_key: Mapped[str] = mapped_column(Text)  # Fernet ciphertext
    hint: Mapped[str] = mapped_column(String(64))  # masked, safe to display

    user: Mapped["User"] = relationship(back_populates="credentials")


class PersonalizationProfile(Base):
    """Per-user preferences that drive the discovery engine (and, later, the
    broader personalization engine)."""

    __tablename__ = "personalization_profiles"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    languages: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list[str]
    topics: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list[str]
    # beginner | intermediate | advanced
    experience_level: Mapped[str] = mapped_column(String(16), default="beginner")
    labels: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list[str]


class GitHubInstallation(Base):
    """A GitHub App installation on a user/org account. Lets the platform mint
    short-lived installation tokens to act on the installed repositories."""

    __tablename__ = "github_installations"

    installation_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    account_login: Mapped[str] = mapped_column(String(255), index=True)
    account_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # User|Organization
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    repository_selection: Mapped[str | None] = mapped_column(String(16), nullable=True)  # all|selected
    sender_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    suspended: Mapped[bool] = mapped_column(default=False)
    # Best-effort link to the platform user who installed it (matched by login).
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )


class Repository(Base):
    __tablename__ = "repositories"

    owner_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    # e.g. "fastapi/fastapi"
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    clone_url: Mapped[str] = mapped_column(String(512))
    default_branch: Mapped[str] = mapped_column(String(128), default="main")
    # pending | cloning | parsing | embedding | mapping | ready | failed
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    languages: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    readme_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped["User | None"] = relationship(back_populates="repositories")
    jobs: Mapped[list["IndexJob"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    issues: Mapped[list["Issue"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )


class IndexJob(Base):
    __tablename__ = "index_jobs"

    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    # queued | running | succeeded | failed
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0..100
    log: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    repository: Mapped["Repository"] = relationship(back_populates="jobs")


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (
        UniqueConstraint("repository_id", "github_number", name="uq_repo_issue"),
    )

    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    github_number: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(512))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(16), default="open")
    labels: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list[str]
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    html_url: Mapped[str] = mapped_column(String(512))
    github_created_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    github_updated_at: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # --- analysis (populated by analyze; null until run) ---
    # not_analyzed | analyzing | analyzed | failed
    analysis_status: Mapped[str] = mapped_column(String(32), default="not_analyzed")
    complexity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1..10
    complexity_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    estimated_hours: Mapped[str | None] = mapped_column(String(32), nullable=True)
    suitability_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0..100
    # JSON: list of {path, start_line, end_line, kind, score}
    affected_files: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_knowledge: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list[str]
    strategy: Mapped[str | None] = mapped_column(Text, nullable=True)
    risks: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list[str]
    analysis_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)

    repository: Mapped["Repository"] = relationship(back_populates="issues")
    contributions: Mapped[list["ContributionTask"]] = relationship(
        back_populates="issue", cascade="all, delete-orphan"
    )


class ContributionTask(Base):
    """An AI-drafted attempt to solve an issue. Never pushed to GitHub without
    explicit human approval; the MVP stops at an approved draft (the GitHub App
    write path is a later phase — see docs/GitHub-App-Design.md)."""

    __tablename__ = "contribution_tasks"

    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    issue_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("issues.id", ondelete="CASCADE"), index=True
    )
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    # queued | planning | generating | ready_for_review | needs_guidance
    #   | approved | rejected | failed
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)  # docs|test|bug|feature|other
    is_safe_category: Mapped[bool] = mapped_column(default=False)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list[str]
    # JSON: list of {path, action, original_content, new_content, diff, note}
    proposed_changes: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    risks: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list[str]

    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0..100
    confidence_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    # When confidence is too low we withhold a draft and give guidance instead.
    guidance: Mapped[str | None] = mapped_column(Text, nullable=True)

    commit_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    pr_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    pr_body: Mapped[str | None] = mapped_column(Text, nullable=True)

    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- publish (GitHub write path; only after approval) ---
    # none | publishing | published | failed
    publish_status: Mapped[str] = mapped_column(String(32), default="none")
    branch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pr_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    pr_head_repo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publish_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    issue: Mapped["Issue"] = relationship(back_populates="contributions")


class Conversation(Base):
    __tablename__ = "conversations"

    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="New conversation")

    repository: Mapped["Repository"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    # JSON string: list of {path, start_line, end_line, score}
    citations: Mapped[str | None] = mapped_column(Text, nullable=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


__all__ = [
    "User",
    "ProviderCredential",
    "PersonalizationProfile",
    "GitHubInstallation",
    "Repository",
    "IndexJob",
    "Issue",
    "ContributionTask",
    "Conversation",
    "Message",
]
