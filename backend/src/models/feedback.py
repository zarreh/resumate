"""FeedbackLog and SessionDecision models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from src.models.session import Session
    from src.models.user import User


class FeedbackLog(UUIDMixin, Base):
    __tablename__ = "feedback_logs"

    session_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID, ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    bullet_id: Mapped[str] = mapped_column(String)
    decision: Mapped[str] = mapped_column(String)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped[Session] = relationship(
        back_populates="feedback_logs"
    )


class SessionDecision(UUIDMixin, Base):
    __tablename__ = "session_decisions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID, ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    decisions_snapshot: Mapped[dict] = mapped_column(JSONB)  # type: ignore[type-arg]
    embedding = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped[Session] = relationship(
        back_populates="session_decisions"
    )
    user: Mapped[User] = relationship()
