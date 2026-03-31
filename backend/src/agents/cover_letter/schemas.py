"""Structured output schemas for the Cover Letter agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CoverLetterContent(BaseModel):
    """Generated cover letter content."""

    body: str = Field(description="The complete cover letter text")


class CoverLetterOutput(BaseModel):
    """Wrapper for structured LLM output from the Cover Letter agent."""

    cover_letter: CoverLetterContent = Field(
        description="The generated cover letter"
    )
