"""Resume Writer LangGraph agent — produces tailored resumes."""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from src.agents.resume_writer.prompts import CALIBRATION_PROMPT, STRENGTH_PROMPTS, SYSTEM_PROMPT
from src.agents.resume_writer.schemas import ResumeWriterOutput
from src.schemas.job import JDAnalysis
from src.schemas.matching import GapAnalysis, MatchResult, RankedEntry
from src.schemas.resume import EnhancedResume
from src.services.llm_config import LLMConfig

logger = logging.getLogger(__name__)


class WriterState(TypedDict):
    """State for the Resume Writer graph."""

    jd_analysis: dict[str, Any]
    ranked_entries: list[dict[str, Any]]
    match_result: dict[str, Any]
    context_text: str
    style_feedback: str
    style_preference: str  # "conservative" | "moderate" | "aggressive"
    mode: str  # "full" or "calibration"
    resume: dict[str, Any] | None


class ResumeWriterAgent:
    """LangGraph agent that produces a tailored EnhancedResume from career entries
    and a JD analysis."""

    def __init__(self, llm_config: LLMConfig) -> None:
        self._model: BaseChatModel = llm_config.get_chat_model(
            "resume_writer", temperature=0.3, streaming=False
        )
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:  # noqa: ANN401
        graph = StateGraph(WriterState)
        graph.add_node("write_resume", self._write_resume_node)
        graph.set_entry_point("write_resume")
        graph.add_edge("write_resume", END)
        return graph.compile()

    def _build_user_message(self, state: WriterState) -> str:
        """Build the user message with all context for the LLM."""
        jd = state["jd_analysis"]
        entries = state["ranked_entries"]
        match = state["match_result"]
        context = state.get("context_text", "")

        parts: list[str] = []

        # JD Analysis
        parts.append("## Job Description Analysis")
        parts.append(f"**Role:** {jd.get('role_title', 'Unknown')}")
        if jd.get("company_name"):
            parts.append(f"**Company:** {jd['company_name']}")
        parts.append(f"**Seniority:** {jd.get('seniority_level', 'mid')}")
        parts.append(f"**Industry:** {jd.get('industry', 'Unknown')}")
        parts.append(f"**Required Skills:** {', '.join(jd.get('required_skills', []))}")
        parts.append(f"**Preferred Skills:** {', '.join(jd.get('preferred_skills', []))}")
        parts.append(f"**Tech Stack:** {', '.join(jd.get('tech_stack', []))}")
        parts.append(f"**ATS Keywords:** {', '.join(jd.get('ats_keywords', []))}")
        parts.append(
            f"**Responsibilities:** {'; '.join(jd.get('responsibilities', []))}"
        )
        parts.append("")

        # Match context
        parts.append("## Match Context")
        parts.append(f"**Overall Match Score:** {match.get('overall_score', 0):.0f}/100")
        gap = match.get("gap_analysis", {})
        if gap.get("unmatched_required"):
            parts.append(
                f"**Unmatched Required Skills (GAPS):** {', '.join(gap['unmatched_required'])}"
            )
        if gap.get("missing_tech"):
            parts.append(
                f"**Missing Tech Stack:** {', '.join(gap['missing_tech'])}"
            )
        rec_order = match.get("recommended_section_order", [])
        if rec_order:
            parts.append(f"**Recommended Section Order:** {', '.join(rec_order)}")
        parts.append("")

        # Career entries
        parts.append("## Selected Career Entries")
        for i, entry in enumerate(entries):
            parts.append(f"\n### Entry {i + 1}: {entry.get('title', 'Untitled')}")
            parts.append(f"- **ID:** {entry.get('entry_id', '')}")
            parts.append(f"- **Type:** {entry.get('entry_type', '')}")
            if entry.get("organization"):
                parts.append(f"- **Organization:** {entry['organization']}")
            if entry.get("start_date"):
                date_str = entry["start_date"]
                if entry.get("end_date"):
                    date_str += f" — {entry['end_date']}"
                else:
                    date_str += " — Present"
                parts.append(f"- **Dates:** {date_str}")
            parts.append(f"- **Tags:** {', '.join(entry.get('tags', []))}")
            parts.append(
                f"- **Relevance Score:** {entry.get('similarity_score', 0):.2f}"
            )
            bullets = entry.get("bullet_points", [])
            if bullets:
                parts.append("- **Bullet Points:**")
                for b in bullets:
                    parts.append(f"  - {b}")
        parts.append("")

        # Additional context
        if context:
            parts.append("## Additional Context from Candidate")
            parts.append(context)
            parts.append("")

        parts.append(
            "Produce the complete EnhancedResume JSON with tailored summary, "
            "sections, skills, and metadata."
        )

        return "\n".join(parts)

    async def _write_resume_node(self, state: WriterState) -> dict[str, Any]:
        """Run the LLM to produce the enhanced resume."""
        structured_model = self._model.with_structured_output(ResumeWriterOutput)

        mode = state.get("mode", "full")
        style_pref = state.get("style_preference", "moderate")
        strength_block = STRENGTH_PROMPTS.get(style_pref, STRENGTH_PROMPTS["moderate"])

        if mode == "calibration" and state.get("style_feedback"):
            system_content = (
                SYSTEM_PROMPT
                + "\n\n"
                + strength_block
                + "\n\n"
                + CALIBRATION_PROMPT.format(feedback=state["style_feedback"])
            )
        else:
            system_content = SYSTEM_PROMPT + "\n\n" + strength_block

        user_content = self._build_user_message(state)

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=user_content),
        ]

        result: Any = await structured_model.ainvoke(messages)

        if isinstance(result, ResumeWriterOutput):
            resume = result.resume
        elif isinstance(result, dict):
            parsed = ResumeWriterOutput.model_validate(result)
            resume = parsed.resume
        else:
            msg = f"Unexpected LLM output type: {type(result)}"
            raise TypeError(msg)

        logger.info(
            "Generated resume: sections=%d, skills=%d, bullets=%d",
            len(resume.sections),
            len(resume.skills),
            sum(
                len(e.bullets)
                for s in resume.sections
                for e in s.entries
            ),
        )

        return {"resume": resume.model_dump()}

    async def write(
        self,
        jd_analysis: JDAnalysis,
        ranked_entries: list[RankedEntry],
        match_result: MatchResult,
        context_text: str = "",
        style_feedback: str = "",
        style_preference: str = "moderate",
        mode: str = "full",
    ) -> EnhancedResume:
        """Generate a tailored resume from JD analysis and career entries.

        Args:
            jd_analysis: Structured JD analysis.
            ranked_entries: Ranked career entries from retrieval.
            match_result: Match scoring results with gap analysis.
            context_text: Optional additional context from the user.
            style_feedback: Optional style calibration feedback.
            style_preference: Enhancement strength (conservative/moderate/aggressive).
            mode: "full" for standard generation, "calibration" for style-aware.

        Returns:
            EnhancedResume with tailored sections, bullets, and summary.
        """
        initial_state: WriterState = {
            "jd_analysis": jd_analysis.model_dump(),
            "ranked_entries": [e.model_dump() for e in ranked_entries],
            "match_result": match_result.model_dump(),
            "context_text": context_text,
            "style_feedback": style_feedback,
            "style_preference": style_preference,
            "mode": mode,
            "resume": None,
        }
        result = await self._graph.ainvoke(initial_state)

        resume_data = result.get("resume")
        if resume_data is None:
            msg = "Resume Writer agent did not produce a resume"
            raise RuntimeError(msg)

        if isinstance(resume_data, EnhancedResume):
            return resume_data
        return EnhancedResume.model_validate(resume_data)
