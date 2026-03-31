"""Reviewer agent — LangGraph agent that reviews resume from recruiter and hiring manager perspectives."""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from src.agents.reviewer.prompts import COMBINED_PROMPT
from src.agents.reviewer.schemas import ReviewOutput, ReviewReport
from src.schemas.job import JDAnalysis
from src.schemas.resume import EnhancedResume
from src.services.llm_config import LLMConfig

logger = logging.getLogger(__name__)


class ReviewerState(TypedDict):
    """State for the Reviewer graph."""

    enhanced_resume: dict[str, Any]
    jd_analysis: dict[str, Any]
    report: dict[str, Any] | None


class ReviewerAgent:
    """LangGraph agent that reviews enhanced resume from two perspectives."""

    def __init__(self, llm_config: LLMConfig) -> None:
        self._model: BaseChatModel = llm_config.get_chat_model(
            "reviewer", temperature=0.2, streaming=False
        )
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:  # noqa: ANN401
        """Build the LangGraph state graph."""
        graph = StateGraph(ReviewerState)
        graph.add_node("review", self._review_node)
        graph.set_entry_point("review")
        graph.add_edge("review", END)
        return graph.compile()

    def _build_user_message(self, state: ReviewerState) -> str:
        """Build the user message with resume and JD analysis for review."""
        resume = state["enhanced_resume"]
        jd = state["jd_analysis"]

        parts: list[str] = []

        # Job description analysis
        parts.append("## Job Description Analysis")
        parts.append(f"**Title:** {jd.get('role_title', 'N/A')}")
        parts.append(f"**Company:** {jd.get('company_name', 'N/A')}")

        if jd.get("required_skills"):
            parts.append(f"**Required Skills:** {', '.join(jd['required_skills'])}")
        if jd.get("preferred_skills"):
            parts.append(f"**Preferred Skills:** {', '.join(jd['preferred_skills'])}")
        if jd.get("responsibilities"):
            parts.append("**Responsibilities:**")
            for r in jd["responsibilities"]:
                parts.append(f"  - {r}")
        if jd.get("requirements"):
            parts.append("**Requirements:**")
            for r in jd["requirements"]:
                parts.append(f"  - {r}")
        parts.append("")

        # Enhanced resume to review
        parts.append("## Enhanced Resume to Review")
        parts.append(f"**Summary:** {resume.get('summary', '')}")
        parts.append("")

        bullet_count = 0
        for section in resume.get("sections", []):
            parts.append(f"### Section: {section.get('title', 'Untitled')}")
            for entry in section.get("entries", []):
                parts.append(
                    f"**{entry.get('title', '')}** at {entry.get('organization', 'N/A')}"
                )
                for bullet in entry.get("bullets", []):
                    bullet_count += 1
                    parts.append(
                        f"  - [{bullet.get('id', '')}] "
                        f"\"{bullet.get('enhanced_text', '')}\""
                        f" (relevance: {bullet.get('relevance_score', 0):.1f})"
                    )
            parts.append("")

        parts.append(f"**Skills:** {', '.join(resume.get('skills', []))}")
        parts.append("")
        parts.append(
            f"Total bullets: {bullet_count}. "
            f"Expected annotations: {bullet_count * 2} "
            f"(one per bullet per perspective)."
        )

        return "\n".join(parts)

    async def _review_node(self, state: ReviewerState) -> dict[str, Any]:
        """Run the LLM to produce a review report."""
        structured_model = self._model.with_structured_output(ReviewOutput)

        user_content = self._build_user_message(state)

        messages = [
            SystemMessage(content=COMBINED_PROMPT),
            HumanMessage(content=user_content),
        ]

        result: Any = await structured_model.ainvoke(messages)

        if isinstance(result, ReviewOutput):
            report = result.report
        elif isinstance(result, dict):
            parsed = ReviewOutput.model_validate(result)
            report = parsed.report
        else:
            msg = f"Unexpected LLM output type: {type(result)}"
            raise TypeError(msg)

        logger.info(
            "Review complete: strong=%d, adequate=%d, weak=%d, annotations=%d",
            report.strong_count,
            report.adequate_count,
            report.weak_count,
            len(report.annotations),
        )

        return {"report": report.model_dump()}

    async def review(
        self,
        enhanced_resume: EnhancedResume,
        jd_analysis: JDAnalysis,
    ) -> ReviewReport:
        """Review an enhanced resume from both recruiter and hiring manager perspectives.

        Args:
            enhanced_resume: The tailored resume to review.
            jd_analysis: The job description analysis for context.

        Returns:
            ReviewReport with per-bullet annotations from both perspectives.
        """
        initial_state: ReviewerState = {
            "enhanced_resume": enhanced_resume.model_dump(),
            "jd_analysis": jd_analysis.model_dump(),
            "report": None,
        }
        result = await self._graph.ainvoke(initial_state)

        report_data = result.get("report")
        if report_data is None:
            msg = "Reviewer agent did not produce a report"
            raise RuntimeError(msg)

        if isinstance(report_data, ReviewReport):
            return report_data
        return ReviewReport.model_validate(report_data)
