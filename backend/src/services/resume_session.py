"""Resume session service — manages enhanced resume state on sessions."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.session import Session
from src.schemas.resume import EnhancedResume
from src.services.job import JobService


class ResumeSessionService:
    """Manages the enhanced resume lifecycle on a session."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._job_svc = JobService(db)

    async def get_session(
        self, user_id: uuid.UUID, session_id: uuid.UUID
    ) -> Session | None:
        return await self._job_svc.get_session(user_id, session_id)

    async def store_enhanced_resume(
        self, session: Session, resume: EnhancedResume
    ) -> Session:
        """Store the enhanced resume JSON on the session."""
        session.enhanced_resume = resume.model_dump()  # type: ignore[assignment]
        await self._db.commit()
        await self._db.refresh(session)
        return session

    async def get_enhanced_resume(self, session: Session) -> EnhancedResume | None:
        """Load the enhanced resume from a session, if any."""
        if session.enhanced_resume is None:
            return None
        return EnhancedResume.model_validate(session.enhanced_resume)

    async def update_style_preference(
        self, session: Session, style: str
    ) -> Session:
        """Update the style preference on a session."""
        session.style_preference = style
        await self._db.commit()
        await self._db.refresh(session)
        return session
