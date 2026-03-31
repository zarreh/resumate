"""Structured output schemas for the Fact Checker agent."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ClaimVerification(BaseModel):
    """Verification result for a single claim in the enhanced resume."""

    claim_text: str = Field(description="The claim being verified (enhanced bullet text)")
    bullet_id: str = Field(description="ID of the EnhancedBullet this claim belongs to")
    status: Literal["verified", "unverified", "modified"] = Field(
        description=(
            "'verified' = claim is directly supported by source material; "
            "'unverified' = no supporting evidence found; "
            "'modified' = claim is based on source but includes embellishments"
        )
    )
    source_entry_id: str | None = Field(
        default=None, description="UUID of the career entry backing this claim"
    )
    source_text: str | None = Field(
        default=None, description="Original text from the career entry that supports the claim"
    )
    notes: str | None = Field(
        default=None,
        description="Explanation of what was modified or why claim is unverified",
    )


class FactCheckReport(BaseModel):
    """Complete fact-check report for an enhanced resume."""

    verifications: list[ClaimVerification] = Field(default_factory=list)
    summary: str = Field(
        description="Brief overall assessment of the resume's factual accuracy"
    )
    verified_count: int = Field(default=0)
    unverified_count: int = Field(default=0)
    modified_count: int = Field(default=0)


class FactCheckOutput(BaseModel):
    """Wrapper for structured LLM output from the Fact Checker agent."""

    report: FactCheckReport = Field(
        description="The complete fact-check report for the resume"
    )
