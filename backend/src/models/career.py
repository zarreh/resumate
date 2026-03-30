"""CareerHistoryEntry model."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.user import User


class CareerHistoryEntry(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "career_history_entries"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    entry_type: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    organization: Mapped[str | None] = mapped_column(String, nullable=True)
    start_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    bullet_points: Mapped[list] = mapped_column(JSONB, default=list)  # type: ignore[type-arg]
    tags: Mapped[list] = mapped_column(JSONB, default=list)  # type: ignore[type-arg]
    source: Mapped[str] = mapped_column(String)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding = mapped_column(Vector(1536), nullable=True)

    user: Mapped[User] = relationship(back_populates="career_entries")
