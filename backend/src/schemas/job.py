"""Job description schemas — request/response types for JD analysis."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


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
    """Request body for parsing a job description (text or URL)."""

    text: str | None = Field(default=None, description="Raw job description text")
    url: str | None = Field(default=None, description="URL to fetch job description from")

    @model_validator(mode="after")
    def require_text_or_url(self) -> JobParseRequest:
        if not self.text and not self.url:
            raise ValueError("Either 'text' or 'url' must be provided")
        return self


class JobDescriptionResponse(BaseModel):
    """Response for a stored job description with analysis."""

    id: str
    raw_text: str
    analysis: JDAnalysis | None
    created_at: str

    model_config = {"from_attributes": True}
