"""Structured output schema for the Resume Writer agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.schemas.resume import EnhancedResume


class ResumeWriterOutput(BaseModel):
    """Wrapper for LLM structured output — contains the full enhanced resume."""

    resume: EnhancedResume = Field(description="The complete enhanced resume")
