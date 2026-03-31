"""Tools available to the Chat agent.

Each tool is a plain async function decorated with ``@tool``.  They accept
a lightweight *context* dict (injected at runtime) so they can reach the DB
and services without global state.
"""

from __future__ import annotations

import uuid
from typing import Any

from langchain_core.tools import tool


# ---------------------------------------------------------------------------
# Context helpers — tools receive a ``context`` dict at bind time
# ---------------------------------------------------------------------------


def _make_tools(context: dict[str, Any]) -> list:  # noqa: ANN401
    """Build tool list bound to the given *context*.

    ``context`` must contain:
    - ``db``: AsyncSession
    - ``user_id``: uuid.UUID
    - ``session_id``: uuid.UUID | None (current session, may be absent)
    - ``llm_config``: LLMConfig
    """

    @tool
    async def search_career_history(query: str) -> str:
        """Search the user's career history for entries matching a query.

        Args:
            query: Natural language search query (e.g. "Kubernetes experience",
                   "projects using Python").
        """
        from src.services.retrieval import RetrievalService

        db = context["db"]
        llm_config = context["llm_config"]
        user_id = context["user_id"]

        retrieval = RetrievalService(db, llm_config)

        # Generate a query embedding
        embedding = await retrieval.generate_embedding(query)

        # Ensure entries have embeddings
        await retrieval.embed_all_entries(user_id)

        # Search
        results = await retrieval.find_relevant_entries(
            user_id, embedding, top_k=5
        )

        if not results:
            return "No matching career entries found."

        lines = []
        for r in results:
            lines.append(
                f"- **{r.title}** at {r.organization or 'N/A'} "
                f"(type: {r.entry_type}, similarity: {r.similarity_score:.2f})"
            )
            for b in r.bullet_points[:3]:
                lines.append(f"  - {b}")
            if r.tags:
                lines.append(f"  Tags: {', '.join(r.tags)}")
        return "\n".join(lines)

    @tool
    async def add_career_entry(
        title: str,
        entry_type: str,
        bullet_points: list[str],
        organization: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Add a new career history entry for the user.

        Args:
            title: Title of the entry (e.g. "Senior Backend Engineer").
            entry_type: Type: work_experience, project, education, certification, volunteer.
            bullet_points: List of accomplishment bullet points.
            organization: Company or institution name.
            tags: Skill/technology tags.
        """
        from src.models.career import CareerHistoryEntry

        db = context["db"]
        user_id = context["user_id"]

        entry = CareerHistoryEntry(
            user_id=user_id,
            entry_type=entry_type,
            title=title,
            organization=organization,
            bullet_points=bullet_points,
            tags=tags or [],
            source="user_provided",
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)

        return f"Added career entry: '{title}' (id: {entry.id})"

    @tool
    async def get_session_status() -> str:
        """Get the current status of the active tailoring session."""
        from src.services.job import JobService

        db = context["db"]
        user_id = context["user_id"]
        session_id = context.get("session_id")

        if session_id is None:
            return "No active session. Start a new session to tailor a resume."

        svc = JobService(db)
        session = await svc.get_session(user_id, uuid.UUID(str(session_id)))
        if session is None:
            return "Session not found."

        return (
            f"Session ID: {session.id}\n"
            f"Current Gate: {session.current_gate}\n"
            f"Selected Entries: {len(session.selected_entry_ids or [])} entries\n"
            f"Has Resume Draft: {'Yes' if session.enhanced_resume else 'No'}"
        )

    @tool
    async def get_jd_analysis() -> str:
        """Retrieve the analyzed job description for the active session."""
        from src.schemas.job import JDAnalysis
        from src.services.job import JobService

        db = context["db"]
        user_id = context["user_id"]
        session_id = context.get("session_id")

        if session_id is None:
            return "No active session."

        svc = JobService(db)
        session = await svc.get_session(user_id, uuid.UUID(str(session_id)))
        if session is None:
            return "Session not found."

        jd = await svc.get_job_description(user_id, session.job_description_id)
        if jd is None or jd.analysis is None:
            return "No job description analysis available."

        analysis = JDAnalysis.model_validate(jd.analysis)
        return (
            f"**{analysis.role_title}**"
            + (f" at {analysis.company_name}" if analysis.company_name else "")
            + f"\nSeniority: {analysis.seniority_level}"
            + f"\nIndustry: {analysis.industry}"
            + f"\nRequired Skills: {', '.join(analysis.required_skills)}"
            + f"\nPreferred Skills: {', '.join(analysis.preferred_skills)}"
            + f"\nTech Stack: {', '.join(analysis.tech_stack)}"
        )

    @tool
    async def get_enhanced_resume() -> str:
        """Retrieve a summary of the current resume draft for the active session."""
        from src.schemas.resume import EnhancedResume
        from src.services.job import JobService

        db = context["db"]
        user_id = context["user_id"]
        session_id = context.get("session_id")

        if session_id is None:
            return "No active session."

        svc = JobService(db)
        session = await svc.get_session(user_id, uuid.UUID(str(session_id)))
        if session is None:
            return "Session not found."

        if session.enhanced_resume is None:
            return "No resume draft generated yet."

        resume = EnhancedResume.model_validate(session.enhanced_resume)
        total_bullets = sum(
            len(e.bullets) for s in resume.sections for e in s.entries
        )
        section_names = [s.title for s in resume.sections]

        return (
            f"Summary: {resume.summary[:200]}...\n"
            f"Sections: {', '.join(section_names)}\n"
            f"Total bullets: {total_bullets}\n"
            f"Skills: {', '.join(resume.skills[:10])}"
        )

    return [
        search_career_history,
        add_career_entry,
        get_session_status,
        get_jd_analysis,
        get_enhanced_resume,
    ]
