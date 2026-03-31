"""Structured output schemas for the Job Analyst agent."""

from pydantic import BaseModel, Field

from src.schemas.job import JDAnalysis


class JDAnalysisOutput(BaseModel):
    """Wrapper for structured LLM output from the Job Analyst agent."""

    analysis: JDAnalysis = Field(
        description="The structured analysis of the job description"
    )
