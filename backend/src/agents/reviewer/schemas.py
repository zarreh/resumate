"""Structured output schemas for the Reviewer agent."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReviewAnnotation(BaseModel):
    """A review annotation tied to a specific bullet in the enhanced resume."""

    bullet_id: str = Field(description="ID of the EnhancedBullet this annotation belongs to")
    perspective: Literal["recruiter", "hiring_manager"] = Field(
        description="Which review pass produced this annotation"
    )
    rating: Literal["strong", "adequate", "weak"] = Field(
        description=(
            "'strong' = highly effective for the target role; "
            "'adequate' = acceptable but could be improved; "
            "'weak' = unlikely to impress or missing the mark"
        )
    )
    comment: str = Field(
        description="Brief explanation of the rating with actionable feedback"
    )


class ReviewReport(BaseModel):
    """Complete review report from both recruiter and hiring manager perspectives."""

    annotations: list[ReviewAnnotation] = Field(default_factory=list)
    recruiter_summary: str = Field(
        description="Overall assessment from the recruiter perspective"
    )
    hiring_manager_summary: str = Field(
        description="Overall assessment from the hiring manager perspective"
    )
    strong_count: int = Field(default=0)
    adequate_count: int = Field(default=0)
    weak_count: int = Field(default=0)


class ReviewOutput(BaseModel):
    """Wrapper for structured LLM output from the Reviewer agent."""

    report: ReviewReport = Field(
        description="The complete two-pass review report"
    )
