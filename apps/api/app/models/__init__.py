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
    "Repository",
    "IndexJob",
    "Issue",
    "Conversation",
    "Message",
]
