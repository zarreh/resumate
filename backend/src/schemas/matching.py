"""Matching schemas — results from entry retrieval and match scoring."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RankedEntry(BaseModel):
    """A career entry ranked by relevance to a job description."""

    entry_id: str
    entry_type: str
    title: str
    organization: str | None
    start_date: str | None
    end_date: str | None
    bullet_points: list[str]
    tags: list[str]
    source: str
    similarity_score: float = Field(description="Cosine similarity (0-1, higher is better)")


class SkillMatch(BaseModel):
    """A single skill with its match status."""

    skill: str
    matched: bool
    matched_by: list[str] = Field(
        default_factory=list,
        description="Tags from career entries that match this skill",
    )


class GapAnalysis(BaseModel):
    """Analysis of gaps between JD requirements and career entries."""

    unmatched_required: list[str] = Field(
        default_factory=list,
        description="Required skills not covered by any career entry",
    )
    unmatched_preferred: list[str] = Field(
        default_factory=list,
        description="Preferred skills not covered by any career entry",
    )
    missing_tech: list[str] = Field(
        default_factory=list,
        description="Tech stack items not covered by any entry",
    )


class MatchResult(BaseModel):
    """Complete match scoring result."""

    overall_score: float = Field(description="Overall match score 0-100")
    required_skills_score: float = Field(description="Required skills coverage 0-100")
    preferred_skills_score: float = Field(description="Preferred skills coverage 0-100")
    tech_stack_score: float = Field(description="Tech stack coverage 0-100")
    required_matches: list[SkillMatch] = Field(default_factory=list)
    preferred_matches: list[SkillMatch] = Field(default_factory=list)
    tech_matches: list[SkillMatch] = Field(default_factory=list)
    gap_analysis: GapAnalysis = Field(default_factory=GapAnalysis)
    recommended_section_order: list[str] = Field(
        default_factory=list,
        description="Recommended resume section ordering based on JD emphasis",
    )
