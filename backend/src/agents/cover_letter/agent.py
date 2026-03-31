"""Cover Letter agent — LangGraph agent that generates personalized cover letters."""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from src.agents.cover_letter.prompts import SYSTEM_PROMPT
from src.agents.cover_letter.schemas import CoverLetterContent, CoverLetterOutput
from src.schemas.job import JDAnalysis
from src.schemas.resume import EnhancedResume
from src.services.llm_config import LLMConfig

logger = logging.getLogger(__name__)


class CoverLetterState(TypedDict):
    """State for the Cover Letter graph."""

    enhanced_resume: dict[str, Any]
    jd_analysis: dict[str, Any]
    company_research: dict[str, Any] | None
    cover_letter: str | None


class CoverLetterAgent:
    """LangGraph agent that generates personalized cover letters."""

    def __init__(self, llm_config: LLMConfig) -> None:
        self._model: BaseChatModel = llm_config.get_chat_model(
            "cover_letter", temperature=0.4, streaming=False
        )
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:  # noqa: ANN401
        """Build the LangGraph state graph."""
        graph = StateGraph(CoverLetterState)
        graph.add_node("generate", self._generate_node)
        graph.set_entry_point("generate")
        graph.add_edge("generate", END)
        return graph.compile()

    def _build_user_message(self, state: CoverLetterState) -> str:
        """Build the user message with resume and JD analysis."""
        resume = state["enhanced_resume"]
        jd = state["jd_analysis"]

        parts: list[str] = []

        # Job description context
        parts.append("## Job Description")
        parts.append(f"**Title:** {jd.get('role_title', 'N/A')}")
        parts.append(f"**Company:** {jd.get('company_name', 'N/A')}")
        if jd.get("responsibilities"):
            parts.append("**Key Responsibilities:**")
            for r in jd["responsibilities"]:
                parts.append(f"  - {r}")
        if jd.get("required_skills"):
            parts.append(f"**Required Skills:** {', '.join(jd['required_skills'])}")
        if jd.get("qualifications"):
            parts.append(f"**Qualifications:** {', '.join(jd['qualifications'])}")
        parts.append("")

        # Company research context (if available)
        cr = state.get("company_research")
        if cr:
            parts.append("## Company Research")
            if cr.get("summary"):
                parts.append(f"**Overview:** {cr['summary']}")
            if cr.get("mission"):
                parts.append(f"**Mission:** {cr['mission']}")
            if cr.get("products"):
                parts.append(f"**Products/Services:** {', '.join(cr['products'])}")
            if cr.get("culture"):
                parts.append(f"**Culture:** {cr['culture']}")
            if cr.get("recent_news"):
                parts.append("**Recent News:**")
                for news in cr["recent_news"][:3]:
                    parts.append(f"  - {news}")
            parts.append("")

        # Resume context
        parts.append("## Candidate Profile")
        parts.append(f"**Summary:** {resume.get('summary', '')}")
        parts.append(f"**Skills:** {', '.join(resume.get('skills', []))}")
        parts.append("")

        # Top bullets (highest relevance)
        parts.append("## Top Achievements")
        all_bullets = []
        for section in resume.get("sections", []):
            for entry in section.get("entries", []):
                for bullet in entry.get("bullets", []):
                    all_bullets.append({
                        "text": bullet.get("enhanced_text", ""),
                        "score": bullet.get("relevance_score", 0),
                        "title": entry.get("title", ""),
                        "org": entry.get("organization", ""),
                    })

        # Sort by relevance and take top 5
        all_bullets.sort(key=lambda b: b["score"], reverse=True)
        for b in all_bullets[:5]:
            parts.append(
                f"- [{b['title']} at {b['org']}] {b['text']} "
                f"(relevance: {b['score']:.1f})"
            )
        parts.append("")

        parts.append(
            "Write a compelling cover letter for this candidate applying to this role."
        )

        return "\n".join(parts)

    async def _generate_node(self, state: CoverLetterState) -> dict[str, Any]:
        """Run the LLM to generate a cover letter."""
        structured_model = self._model.with_structured_output(CoverLetterOutput)

        user_content = self._build_user_message(state)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]

        result: Any = await structured_model.ainvoke(messages)

        if isinstance(result, CoverLetterOutput):
            content = result.cover_letter
        elif isinstance(result, dict):
            parsed = CoverLetterOutput.model_validate(result)
            content = parsed.cover_letter
        else:
            msg = f"Unexpected LLM output type: {type(result)}"
            raise TypeError(msg)

        logger.info(
            "Cover letter generated: %d words",
            len(content.body.split()),
        )

        return {"cover_letter": content.body}

    async def generate(
        self,
        enhanced_resume: EnhancedResume,
        jd_analysis: JDAnalysis,
        company_research: dict[str, Any] | None = None,
    ) -> str:
        """Generate a cover letter for the given resume and JD.

        Args:
            enhanced_resume: The tailored resume.
            jd_analysis: The job description analysis.
            company_research: Optional structured company research data.

        Returns:
            The cover letter text.
        """
        initial_state: CoverLetterState = {
            "enhanced_resume": enhanced_resume.model_dump(),
            "jd_analysis": jd_analysis.model_dump(),
            "company_research": company_research,
            "cover_letter": None,
        }
        result = await self._graph.ainvoke(initial_state)

        cover_letter = result.get("cover_letter")
        if cover_letter is None:
            msg = "Cover Letter agent did not produce content"
            raise RuntimeError(msg)

        return cover_letter
