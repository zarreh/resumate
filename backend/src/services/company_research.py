"""Company research service — web search + LLM summarization."""

from __future__ import annotations

import logging
from typing import Any

from duckduckgo_search import DDGS
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.services.llm_config import LLMConfig

logger = logging.getLogger(__name__)

_SEARCH_SYSTEM_PROMPT = """\
You are a company research analyst. Given web search snippets about a company, \
extract structured information. Only include facts that are clearly supported by \
the snippets. If a field cannot be determined, leave it as null or empty.\
"""


class CompanyResearch(BaseModel):
    """Structured company research data."""

    company_name: str
    summary: str | None = Field(default=None, description="1-2 sentence company overview")
    mission: str | None = Field(default=None, description="Company mission or vision statement")
    products: list[str] = Field(default_factory=list, description="Main products or services")
    culture: str | None = Field(default=None, description="Company culture highlights")
    recent_news: list[str] = Field(default_factory=list, description="Recent notable news items")
    size_and_funding: str | None = Field(default=None, description="Company size, funding, or revenue info")
    headquarters: str | None = Field(default=None, description="HQ location")
    industry: str | None = Field(default=None, description="Primary industry")


class CompanyResearchError(Exception):
    """Raised when company research fails."""


class CompanyResearchService:
    """Searches the web for company info and summarises with an LLM."""

    def __init__(self, llm_config: LLMConfig) -> None:
        self._model: BaseChatModel = llm_config.get_chat_model(
            "company_research", temperature=0.0, streaming=False
        )

    async def research(self, company_name: str) -> CompanyResearch:
        """Run web search and LLM summarisation for *company_name*."""
        snippets = self._search_web(company_name)
        if not snippets:
            logger.warning("No search results for company: %s", company_name)
            return CompanyResearch(company_name=company_name)

        return await self._summarize(company_name, snippets)

    @staticmethod
    def _search_web(company_name: str) -> list[str]:
        """Return top search result snippets for the company."""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(f"{company_name} company overview", max_results=5))
        except Exception:
            logger.exception("DuckDuckGo search failed for %s", company_name)
            return []

        return [r.get("body", "") for r in results if r.get("body")]

    async def _summarize(self, company_name: str, snippets: list[str]) -> CompanyResearch:
        """Ask the LLM to distil snippets into structured research."""
        numbered = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(snippets))
        user_content = (
            f"Company: {company_name}\n\n"
            f"Web search snippets:\n{numbered}\n\n"
            "Extract structured company information from these snippets."
        )

        structured_model = self._model.with_structured_output(CompanyResearch)

        try:
            result: Any = await structured_model.ainvoke([
                SystemMessage(content=_SEARCH_SYSTEM_PROMPT),
                HumanMessage(content=user_content),
            ])
        except Exception:
            logger.exception("LLM summarisation failed for %s", company_name)
            return CompanyResearch(company_name=company_name)

        if isinstance(result, CompanyResearch):
            return result
        if isinstance(result, dict):
            return CompanyResearch.model_validate(result)

        logger.warning("Unexpected LLM output type: %s", type(result))
        return CompanyResearch(company_name=company_name)
