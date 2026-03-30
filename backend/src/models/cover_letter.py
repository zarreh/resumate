"""CoverLetter model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.session import Session
    from src.models.user import User


class CoverLetter(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cover_letters"

    session_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID, ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(Text)

    session: Mapped[Session] = relationship(
        back_populates="cover_letters"
    )
    user: Mapped[User] = relationship()
