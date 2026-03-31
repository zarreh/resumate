"""Job description schemas — request/response types for JD analysis."""

from __future__ import annotations

from pydantic import BaseModel, Field


class JDAnalysis(BaseModel):
    """Structured analysis of a job description."""

    role_title: str = Field(description="The job title or role name")
    company_name: str | None = Field(default=None, description="Company name if mentioned")
    seniority_level: str = Field(description="Seniority level: junior, mid, senior, staff, lead, principal, manager, director, vp, c-level")
    industry: str = Field(description="Primary industry or domain")
    required_skills: list[str] = Field(default_factory=list, description="Hard requirements / must-haves")
    preferred_skills: list[str] = Field(default_factory=list, description="Nice-to-haves / preferred qualifications")
    ats_keywords: list[str] = Field(default_factory=list, description="Keywords likely used by ATS systems for filtering")
    tech_stack: list[str] = Field(default_factory=list, description="Specific technologies, frameworks, tools mentioned")
    responsibilities: list[str] = Field(default_factory=list, description="Key responsibilities of the role")
    qualifications: list[str] = Field(default_factory=list, description="Education, years of experience, certifications")
    domain_expectations: list[str] = Field(default_factory=list, description="Domain-specific expectations (e.g. HIPAA, SOC2, clearance)")


class JobParseRequest(BaseModel):
    """Request body for parsing a job description."""

    text: str = Field(min_length=1, description="Raw job description text")


class JobDescriptionResponse(BaseModel):
    """Response for a stored job description with analysis."""

    id: str
    raw_text: str
    analysis: JDAnalysis | None
    created_at: str

    model_config = {"from_attributes": True}
