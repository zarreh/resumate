"""LLM-based resume parsing — converts raw extracted text into structured
CareerHistoryEntry objects using structured output."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.schemas.career import ParsedResumeEntry
from src.services.llm_config import LLMConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Structured output wrapper — used by model.with_structured_output()
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert resume parser. Given raw text extracted from a resume, \
identify and structure ALL career entries into a JSON list.

For each entry you MUST extract:
- entry_type: one of "work_experience", "project", "education", "certification", "volunteer"
- title: job title, degree name, project name, or certification name
- organization: company, university, or organization (null if not stated)
- start_date: in YYYY-MM format if month is known, YYYY if only year is known, null if missing
- end_date: same format as start_date, null if the position is current or date is missing
- bullet_points: list of objects with "text" (the bullet/achievement) and "tags" (skills/technologies mentioned)
- tags: aggregated list of all technologies, skills, tools, frameworks, and domains from the entry
- raw_text: the original text segment this entry was parsed from

Rules:
1. Preserve the ORIGINAL wording of bullet points — do NOT rephrase or enhance.
2. Extract ALL entries, even if they seem minor.
3. For education entries, the "title" is the degree (e.g., "B.S. Computer Science") and \
"organization" is the university.
4. Tags should be specific and normalized (e.g., "Python" not "python programming", \
"AWS" not "Amazon Web Services").
5. If a section has no bullets but has descriptive text, create a single bullet from it.
6. Dates like "2020-Present" should have end_date as null.
7. Do NOT infer information that is not explicitly stated in the resume text.
"""


class ParsedResumeOutput(BaseModel):
    """Structured output schema for the LLM resume parser."""

    entries: list[ParsedResumeEntry] = Field(
        description="All career entries extracted from the resume"
    )


class ResumeParser:
    """Parses raw resume text into structured career entries using an LLM."""

    def __init__(self, llm_config: LLMConfig) -> None:
        self._model: BaseChatModel = llm_config.get_chat_model(
            "resume_parser", temperature=0.0, streaming=False
        )

    async def parse(self, raw_text: str) -> list[ParsedResumeEntry]:
        """Send raw resume text to the LLM and return structured entries.

        Uses ``with_structured_output`` for reliable JSON parsing.
        """
        structured_model = self._model.with_structured_output(ParsedResumeOutput)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Parse the following resume text:\n\n{raw_text}"),
        ]

        result: Any = await structured_model.ainvoke(messages)

        if isinstance(result, ParsedResumeOutput):
            entries = result.entries
        elif isinstance(result, dict):
            parsed = ParsedResumeOutput.model_validate(result)
            entries = parsed.entries
        else:
            msg = f"Unexpected LLM output type: {type(result)}"
            raise TypeError(msg)

        logger.info("Parsed %d entries from resume text", len(entries))
        return entries
