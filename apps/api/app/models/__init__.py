"""ORM models for the MVP vertical slice.

The full data model (users, GitHub installations, contribution tasks, PRs,
provider credentials, autonomous runs, personalization profiles) is described
in docs/TRD.md. Here we implement the subset needed for the
index -> chat -> architecture-map flow.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Repository(Base):
    __tablename__ = "repositories"

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

    jobs: Mapped[list["IndexJob"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
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


__all__ = ["Repository", "IndexJob", "Conversation", "Message"]
