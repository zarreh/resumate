"""TailoredResume and ResumeTemplate models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.session import Session
    from src.models.user import User


class TailoredResume(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tailored_resumes"

    session_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID, ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[dict] = mapped_column(JSONB)  # type: ignore[type-arg]
    template_name: Mapped[str] = mapped_column(String)
    pdf_path: Mapped[str | None] = mapped_column(String, nullable=True)

    session: Mapped[Session] = relationship(
        back_populates="tailored_resumes"
    )
    user: Mapped[User] = relationship()


class ResumeTemplate(UUIDMixin, Base):
    __tablename__ = "resume_templates"

    name: Mapped[str] = mapped_column(String, unique=True)
    display_name: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=func.now()
    )
