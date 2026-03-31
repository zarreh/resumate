"""Analytics service — aggregate feedback metrics for quality dashboard."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.feedback import FeedbackLog
from src.models.session import Session


class AnalyticsService:
    """Aggregates feedback_logs data for the quality dashboard."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_feedback_metrics(self, user_id: uuid.UUID) -> dict:
        """Return aggregate feedback metrics for a user.

        Queries feedback_logs joined with sessions to compute approval,
        rejection, and edit rates across all sessions.
        """
        # Get per-session, per-decision counts
        stmt = (
            select(
                FeedbackLog.session_id,
                FeedbackLog.decision,
                func.count().label("cnt"),
            )
            .join(Session, FeedbackLog.session_id == Session.id)
            .where(Session.user_id == user_id)
            .group_by(FeedbackLog.session_id, FeedbackLog.decision)
        )
        result = await self._db.execute(stmt)
        rows = result.all()

        # Aggregate per-session
        session_map: dict[uuid.UUID, dict[str, int]] = {}
        for session_id, decision, cnt in rows:
            if session_id not in session_map:
                session_map[session_id] = {"approved": 0, "rejected": 0, "edited": 0}
            session_map[session_id][decision] = cnt

        # Totals
        approved_count = sum(s["approved"] for s in session_map.values())
        rejected_count = sum(s["rejected"] for s in session_map.values())
        edited_count = sum(s["edited"] for s in session_map.values())
        total = approved_count + rejected_count + edited_count

        # Load session metadata for per-session breakdown
        per_session = []
        if session_map:
            sessions_stmt = (
                select(Session)
                .options(selectinload(Session.job_description))
                .where(Session.id.in_(session_map.keys()))
                .order_by(Session.created_at.desc())
            )
            sessions_result = await self._db.execute(sessions_stmt)
            sessions = sessions_result.scalars().all()

            for s in sessions:
                counts = session_map[s.id]
                analysis = s.job_description.analysis if s.job_description else None
                session_total = counts["approved"] + counts["rejected"] + counts["edited"]
                per_session.append({
                    "session_id": str(s.id),
                    "role_title": analysis.get("role_title") if analysis else None,
                    "company_name": analysis.get("company_name") if analysis else None,
                    "approved": counts["approved"],
                    "rejected": counts["rejected"],
                    "edited": counts["edited"],
                    "total": session_total,
                    "created_at": s.created_at.isoformat(),
                })

        return {
            "total_decisions": total,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "edited_count": edited_count,
            "approval_rate": round(approved_count / total, 3) if total else 0.0,
            "rejection_rate": round(rejected_count / total, 3) if total else 0.0,
            "edit_rate": round(edited_count / total, 3) if total else 0.0,
            "sessions_with_feedback": len(session_map),
            "per_session": per_session,
        }
