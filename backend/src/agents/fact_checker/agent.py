"""Fact Checker agent — LangGraph agent that verifies resume claims against career history."""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from src.agents.fact_checker.prompts import SYSTEM_PROMPT
from src.agents.fact_checker.schemas import FactCheckOutput, FactCheckReport
from src.schemas.resume import EnhancedResume
from src.services.llm_config import LLMConfig

logger = logging.getLogger(__name__)


class FactCheckerState(TypedDict):
    """State for the Fact Checker graph."""

    enhanced_resume: dict[str, Any]
    career_entries: list[dict[str, Any]]
    report: dict[str, Any] | None


class FactCheckerAgent:
    """LangGraph agent that verifies enhanced resume claims against career history."""

    def __init__(self, llm_config: LLMConfig) -> None:
        self._model: BaseChatModel = llm_config.get_chat_model(
            "fact_checker", temperature=0.0, streaming=False
        )
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:  # noqa: ANN401
        """Build the LangGraph state graph."""
        graph = StateGraph(FactCheckerState)
        graph.add_node("fact_check", self._fact_check_node)
        graph.set_entry_point("fact_check")
        graph.add_edge("fact_check", END)
        return graph.compile()

    def _build_user_message(self, state: FactCheckerState) -> str:
        """Build the user message with resume and career entries for verification."""
        resume = state["enhanced_resume"]
        entries = state["career_entries"]

        parts: list[str] = []

        # Enhanced resume to verify
        parts.append("## Enhanced Resume to Verify")
        parts.append(f"**Summary:** {resume.get('summary', '')}")
        parts.append("")

        for section in resume.get("sections", []):
            parts.append(f"### Section: {section.get('title', 'Untitled')}")
            for entry in section.get("entries", []):
                parts.append(f"**{entry.get('title', '')}** at {entry.get('organization', 'N/A')}")
                parts.append(f"  Source Entry ID: {entry.get('entry_id', '')}")
                for bullet in entry.get("bullets", []):
                    parts.append(
                        f"  - [{bullet.get('id', '')}] "
                        f"(source: {bullet.get('source_entry_id', 'N/A')}) "
                        f"Original: \"{bullet.get('original_text', '')}\""
                    )
                    parts.append(
                        f"    Enhanced: \"{bullet.get('enhanced_text', '')}\""
                    )
            parts.append("")

        parts.append(f"**Skills:** {', '.join(resume.get('skills', []))}")
        parts.append("")

        # Career history entries (source of truth)
        parts.append("## Career History Entries (Source of Truth)")
        for entry in entries:
            parts.append(f"\n### Entry: {entry.get('title', 'Untitled')}")
            parts.append(f"- **ID:** {entry.get('id', entry.get('entry_id', ''))}")
            parts.append(f"- **Type:** {entry.get('entry_type', '')}")
            if entry.get("organization"):
                parts.append(f"- **Organization:** {entry['organization']}")
            if entry.get("start_date"):
                date_str = str(entry["start_date"])
                if entry.get("end_date"):
                    date_str += f" — {entry['end_date']}"
                parts.append(f"- **Dates:** {date_str}")
            if entry.get("tags"):
                parts.append(f"- **Tags:** {', '.join(entry['tags'])}")
            bullets = entry.get("bullet_points", [])
            if bullets:
                parts.append("- **Original Bullets:**")
                for b in bullets:
                    parts.append(f"  - {b}")
        parts.append("")

        parts.append(
            "Verify every enhanced bullet and the summary against the career "
            "history entries above. Produce a complete FactCheckReport."
        )

        return "\n".join(parts)

    async def _fact_check_node(self, state: FactCheckerState) -> dict[str, Any]:
        """Run the LLM to produce a fact-check report."""
        structured_model = self._model.with_structured_output(FactCheckOutput)

        user_content = self._build_user_message(state)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]

        result: Any = await structured_model.ainvoke(messages)

        if isinstance(result, FactCheckOutput):
            report = result.report
        elif isinstance(result, dict):
            parsed = FactCheckOutput.model_validate(result)
            report = parsed.report
        else:
            msg = f"Unexpected LLM output type: {type(result)}"
            raise TypeError(msg)

        logger.info(
            "Fact check complete: verified=%d, modified=%d, unverified=%d",
            report.verified_count,
            report.modified_count,
            report.unverified_count,
        )

        return {"report": report.model_dump()}

    async def check(
        self,
        enhanced_resume: EnhancedResume,
        career_entries: list[dict[str, Any]],
    ) -> FactCheckReport:
        """Verify enhanced resume claims against career history entries.

        Args:
            enhanced_resume: The tailored resume to verify.
            career_entries: Raw career entry dicts (from DB or API).

        Returns:
            FactCheckReport with per-claim verification results.
        """
        initial_state: FactCheckerState = {
            "enhanced_resume": enhanced_resume.model_dump(),
            "career_entries": career_entries,
            "report": None,
        }
        result = await self._graph.ainvoke(initial_state)

        report_data = result.get("report")
        if report_data is None:
            msg = "Fact Checker agent did not produce a report"
            raise RuntimeError(msg)

        if isinstance(report_data, FactCheckReport):
            return report_data
        return FactCheckReport.model_validate(report_data)
