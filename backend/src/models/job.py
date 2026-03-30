"""JobDescription model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.session import Session
    from src.models.user import User


class JobDescription(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "job_descriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    raw_text: Mapped[str] = mapped_column(Text)
    analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # type: ignore[type-arg]
    embedding = mapped_column(Vector(1536), nullable=True)

    user: Mapped[User] = relationship(back_populates="job_descriptions")
    sessions: Mapped[list[Session]] = relationship(
        back_populates="job_description"
    )
