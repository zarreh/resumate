"""Session Learning service — stores decisions on completion and retrieves
similar past sessions for few-shot context injection."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.feedback import FeedbackLog, SessionDecision
from src.models.job import JobDescription
from src.models.session import Session
from src.schemas.resume import EnhancedResume
from src.services.llm_config import LLMConfig
from src.services.retrieval import RetrievalService

logger = logging.getLogger(__name__)


class SessionLearningService:
    """Captures completed session decisions and retrieves similar past sessions."""

    def __init__(self, db: AsyncSession, llm_config: LLMConfig) -> None:
        self._db = db
        self._retrieval = RetrievalService(db, llm_config)

    async def complete_session(
        self,
        session: Session,
        user_id: uuid.UUID,
    ) -> SessionDecision:
        """Record a SessionDecision snapshot when a session reaches 'final'.

        The snapshot captures:
        - JD analysis (role, industry, skills)
        - Enhanced resume summary and section order
        - Selected entry IDs and style preference
        - Bullet-level feedback decisions
        - The JD embedding is copied so past sessions can be found by cosine similarity
        """
        # Load the JD to get analysis and embedding
        jd_result = await self._db.execute(
            select(JobDescription).where(JobDescription.id == session.job_description_id)
        )
        jd = jd_result.scalar_one_or_none()

        # Load feedback logs for this session
        feedback_result = await self._db.execute(
            select(FeedbackLog)
            .where(FeedbackLog.session_id == session.id)
            .order_by(FeedbackLog.created_at)
        )
        feedback_logs = list(feedback_result.scalars().all())

        # Build the decisions snapshot
        jd_analysis = jd.analysis if jd else None
        enhanced_resume = session.enhanced_resume

        # Summarize bullet rewrites from the enhanced resume
        bullet_rewrites = []
        if enhanced_resume:
            resume = EnhancedResume.model_validate(enhanced_resume)
            for section in resume.sections:
                for entry in section.entries:
                    for bullet in entry.bullets:
                        if bullet.original_text != bullet.enhanced_text:
                            bullet_rewrites.append({
                                "bullet_id": bullet.id,
                                "original": bullet.original_text,
                                "enhanced": bullet.enhanced_text,
                            })

        # Summarize feedback decisions
        feedback_summary = {
            "approved": [],
            "rejected": [],
            "edited": [],
        }
        for log in feedback_logs:
            feedback_summary[log.decision].append({
                "bullet_id": log.bullet_id,
                "feedback_text": log.feedback_text,
            })

        snapshot = {
            "jd_analysis": jd_analysis,
            "role_title": jd_analysis.get("role_title") if jd_analysis else None,
            "industry": jd_analysis.get("industry") if jd_analysis else None,
            "selected_entry_ids": session.selected_entry_ids or [],
            "style_preference": session.style_preference,
            "section_order": (
                [s["section_type"] for s in enhanced_resume.get("sections", [])]
                if enhanced_resume
                else []
            ),
            "summary": enhanced_resume.get("summary") if enhanced_resume else None,
            "skills": enhanced_resume.get("skills", []) if enhanced_resume else [],
            "bullet_rewrites": bullet_rewrites[:20],  # Cap to keep snapshot manageable
            "feedback": feedback_summary,
        }

        # Copy the JD embedding for cosine similarity lookups
        jd_embedding = list(jd.embedding) if (jd and jd.embedding is not None) else None

        # If JD has no embedding yet, generate one
        if jd_embedding is None and jd and jd.raw_text:
            await self._retrieval.embed_job_description(jd)
            await self._db.refresh(jd)
            jd_embedding = list(jd.embedding) if jd.embedding is not None else None

        decision = SessionDecision(
            session_id=session.id,
            user_id=user_id,
            decisions_snapshot=snapshot,
            embedding=jd_embedding,
        )
        self._db.add(decision)
        await self._db.commit()
        await self._db.refresh(decision)

        logger.info(
            "Stored SessionDecision %s for session %s (user %s)",
            decision.id,
            session.id,
            user_id,
        )
        return decision

    async def find_similar_sessions(
        self,
        user_id: uuid.UUID,
        jd_embedding: list[float],
        *,
        top_k: int = 3,
        exclude_session_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """Find past session decisions most similar to a JD by cosine distance.

        Returns a list of decisions_snapshot dicts enriched with similarity scores.
        """
        embedding_str = "[" + ",".join(str(v) for v in jd_embedding) + "]"

        conditions = [
            "user_id = :user_id",
            "embedding IS NOT NULL",
        ]
        params: dict = {"user_id": user_id, "top_k": top_k}

        if exclude_session_id is not None:
            conditions.append("session_id != :exclude_session_id")
            params["exclude_session_id"] = exclude_session_id

        where_clause = " AND ".join(conditions)

        query = text(f"""
            SELECT id, session_id, decisions_snapshot,
                   1 - (embedding <=> '{embedding_str}'::vector) AS similarity
            FROM session_decisions
            WHERE {where_clause}
            ORDER BY embedding <=> '{embedding_str}'::vector
            LIMIT :top_k
        """)

        result = await self._db.execute(query, params)
        rows = result.fetchall()

        similar: list[dict] = []
        for row in rows:
            entry = dict(row.decisions_snapshot) if row.decisions_snapshot else {}
            entry["_similarity"] = float(row.similarity)
            entry["_session_id"] = str(row.session_id)
            similar.append(entry)

        logger.info(
            "Found %d similar past sessions for user %s (top similarity: %.3f)",
            len(similar),
            user_id,
            similar[0]["_similarity"] if similar else 0.0,
        )

        return similar

    def format_past_sessions_context(self, similar_sessions: list[dict]) -> str:
        """Format similar past sessions into a text block for the Resume Writer prompt.

        Returns an empty string if no past sessions are available.
        """
        if not similar_sessions:
            return ""

        parts: list[str] = [
            "## Past Session Insights",
            "The following are insights from similar past tailoring sessions that the "
            "candidate has completed. Use these as guidance for style, section ordering, "
            "and enhancement approach — but adapt to the current JD's specific requirements.",
            "",
        ]

        for i, session in enumerate(similar_sessions):
            similarity = session.get("_similarity", 0)
            role = session.get("role_title", "Unknown Role")
            industry = session.get("industry", "Unknown")
            style = session.get("style_preference", "moderate")

            parts.append(f"### Past Session {i + 1} (Similarity: {similarity:.2f})")
            parts.append(f"- **Role:** {role}")
            parts.append(f"- **Industry:** {industry}")
            parts.append(f"- **Style Preference:** {style}")

            section_order = session.get("section_order", [])
            if section_order:
                parts.append(f"- **Section Order Used:** {', '.join(section_order)}")

            # Show a few example bullet rewrites from the past session
            rewrites = session.get("bullet_rewrites", [])
            if rewrites:
                parts.append("- **Example Bullet Enhancements (approved by user):**")
                for rw in rewrites[:3]:
                    parts.append(f"  - Original: {rw.get('original', '')}")
                    parts.append(f"  - Enhanced: {rw.get('enhanced', '')}")

            # Show feedback patterns
            feedback = session.get("feedback", {})
            rejected_count = len(feedback.get("rejected", []))
            approved_count = len(feedback.get("approved", []))
            if approved_count or rejected_count:
                parts.append(
                    f"- **User Approval Rate:** {approved_count} approved, "
                    f"{rejected_count} rejected"
                )

            parts.append("")

        return "\n".join(parts)
