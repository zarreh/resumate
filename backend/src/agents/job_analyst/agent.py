"""Job Analyst agent — analyzes job descriptions using LangGraph with structured output."""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from src.agents.job_analyst.prompts import SYSTEM_PROMPT
from src.agents.job_analyst.schemas import JDAnalysisOutput
from src.schemas.job import JDAnalysis
from src.services.llm_config import LLMConfig

logger = logging.getLogger(__name__)


class AnalystState(TypedDict):
    """State for the Job Analyst graph."""

    raw_text: str
    analysis: JDAnalysis | None


class JobAnalystAgent:
    """LangGraph agent that parses a raw job description into a structured
    ``JDAnalysis`` object."""

    def __init__(self, llm_config: LLMConfig) -> None:
        self._model: BaseChatModel = llm_config.get_chat_model(
            "job_analyst", temperature=0.0, streaming=False
        )
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:  # noqa: ANN401
        """Build the LangGraph state graph."""
        graph = StateGraph(AnalystState)
        graph.add_node("analyze", self._analyze_node)
        graph.set_entry_point("analyze")
        graph.add_edge("analyze", END)
        return graph.compile()

    async def _analyze_node(self, state: AnalystState) -> dict[str, Any]:
        """Run the LLM to produce a structured JD analysis."""
        structured_model = self._model.with_structured_output(JDAnalysisOutput)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=f"Analyze the following job description:\n\n{state['raw_text']}"
            ),
        ]

        result: Any = await structured_model.ainvoke(messages)

        if isinstance(result, JDAnalysisOutput):
            analysis = result.analysis
        elif isinstance(result, dict):
            parsed = JDAnalysisOutput.model_validate(result)
            analysis = parsed.analysis
        else:
            msg = f"Unexpected LLM output type: {type(result)}"
            raise TypeError(msg)

        logger.info(
            "Analyzed JD: role=%s, required_skills=%d, tech_stack=%d",
            analysis.role_title,
            len(analysis.required_skills),
            len(analysis.tech_stack),
        )
        return {"analysis": analysis}

    async def analyze(self, raw_text: str) -> JDAnalysis:
        """Analyze a job description and return structured analysis."""
        initial_state: AnalystState = {"raw_text": raw_text, "analysis": None}
        result = await self._graph.ainvoke(initial_state)
        analysis: JDAnalysis | None = result.get("analysis")
        if analysis is None:
            msg = "Job Analyst agent did not produce an analysis"
            raise RuntimeError(msg)
        return analysis
