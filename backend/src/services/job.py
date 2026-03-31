"""Job description service — CRUD for job descriptions and session management."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.job import JobDescription
from src.models.session import Session
from src.schemas.job import JDAnalysis


class JobService:
    """Manages job descriptions and sessions in the database."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_job_description(
        self,
        user_id: uuid.UUID,
        raw_text: str,
        analysis: JDAnalysis | None = None,
    ) -> JobDescription:
        """Create a new job description record."""
        jd = JobDescription(
            user_id=user_id,
            raw_text=raw_text,
            analysis=analysis.model_dump() if analysis else None,
        )
        self._db.add(jd)
        await self._db.commit()
        await self._db.refresh(jd)
        return jd

    async def get_job_description(
        self, user_id: uuid.UUID, jd_id: uuid.UUID
    ) -> JobDescription | None:
        """Fetch a single job description by ID, scoped to user."""
        result = await self._db.execute(
            select(JobDescription).where(
                JobDescription.id == jd_id,
                JobDescription.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_analysis(
        self, jd: JobDescription, analysis: JDAnalysis
    ) -> JobDescription:
        """Store analysis results on an existing job description."""
        jd.analysis = analysis.model_dump()  # type: ignore[assignment]
        await self._db.commit()
        await self._db.refresh(jd)
        return jd

    async def list_job_descriptions(
        self, user_id: uuid.UUID
    ) -> list[JobDescription]:
        """List all job descriptions for a user, newest first."""
        result = await self._db.execute(
            select(JobDescription)
            .where(JobDescription.user_id == user_id)
            .order_by(JobDescription.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_session(
        self,
        user_id: uuid.UUID,
        jd_id: uuid.UUID,
    ) -> Session:
        """Create a new tailoring session linked to a job description."""
        session = Session(
            user_id=user_id,
            job_description_id=jd_id,
            current_gate="analysis",
            selected_entry_ids=[],
        )
        self._db.add(session)
        await self._db.commit()
        await self._db.refresh(session)
        return session

    async def get_session(
        self, user_id: uuid.UUID, session_id: uuid.UUID
    ) -> Session | None:
        """Fetch a session by ID, scoped to user."""
        result = await self._db.execute(
            select(Session).where(
                Session.id == session_id,
                Session.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_session_gate(
        self, session: Session, gate: str
    ) -> Session:
        """Advance a session to a new gate."""
        session.current_gate = gate
        await self._db.commit()
        await self._db.refresh(session)
        return session

    async def update_session_selections(
        self,
        session: Session,
        selected_entry_ids: list[str],
        context_text: str | None = None,
    ) -> Session:
        """Update the selected entries and optional context for a session."""
        session.selected_entry_ids = selected_entry_ids  # type: ignore[assignment]
        if context_text is not None:
            session.context_text = context_text
        await self._db.commit()
        await self._db.refresh(session)
        return session

    async def list_sessions(self, user_id: uuid.UUID) -> list[Session]:
        """List all sessions for a user with JD eagerly loaded, newest first."""
        result = await self._db.execute(
            select(Session)
            .options(selectinload(Session.job_description))
            .where(Session.user_id == user_id)
            .order_by(Session.created_at.desc())
        )
        return list(result.scalars().all())
