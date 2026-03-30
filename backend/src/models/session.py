"""Session model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.cover_letter import CoverLetter
    from src.models.feedback import FeedbackLog, SessionDecision
    from src.models.job import JobDescription
    from src.models.resume import TailoredResume
    from src.models.user import User


class Session(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    job_description_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID, ForeignKey("job_descriptions.id", ondelete="CASCADE"), index=True
    )
    current_gate: Mapped[str] = mapped_column(String, default="analysis")
    selected_entry_ids: Mapped[list] = mapped_column(JSONB, default=list)  # type: ignore[type-arg]
    context_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    style_preference: Mapped[str | None] = mapped_column(String, nullable=True)
    enhanced_resume: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # type: ignore[type-arg]

    user: Mapped[User] = relationship(back_populates="sessions")
    job_description: Mapped[JobDescription] = relationship(
        back_populates="sessions"
    )
    tailored_resumes: Mapped[list[TailoredResume]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    feedback_logs: Mapped[list[FeedbackLog]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    session_decisions: Mapped[list[SessionDecision]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    cover_letters: Mapped[list[CoverLetter]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
