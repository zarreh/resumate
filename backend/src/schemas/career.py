"""Career import and parsing request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImportResponse(BaseModel):
    """Response returned after extracting text from an uploaded resume."""

    filename: str
    content_type: str
    text: str
    char_count: int


# ---------------------------------------------------------------------------
# Resume parsing schemas (Phase 2.2b)
# ---------------------------------------------------------------------------


class ParsedBulletPoint(BaseModel):
    """A single bullet point extracted from a resume entry."""

    text: str = Field(description="The bullet point text")
    tags: list[str] = Field(
        default_factory=list,
        description="Technologies, skills, or keywords from this bullet",
    )


class ParsedResumeEntry(BaseModel):
    """A structured career entry extracted from resume text by the LLM."""

    entry_type: str = Field(
        description="Type: work_experience, project, education, certification, or volunteer"
    )
    title: str = Field(description="Job title, degree, or project name")
    organization: str | None = Field(
        default=None, description="Company, university, or organization name"
    )
    start_date: str | None = Field(
        default=None, description="Start date in YYYY-MM format, or YYYY if month unknown"
    )
    end_date: str | None = Field(
        default=None,
        description="End date in YYYY-MM format, YYYY if month unknown, or null if current",
    )
    bullet_points: list[ParsedBulletPoint] = Field(
        default_factory=list,
        description="Bullet points or achievements for this entry",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Aggregated tags: technologies, skills, domains",
    )
    raw_text: str | None = Field(
        default=None,
        description="Original text segment this entry was parsed from",
    )


class ParsedResumeResponse(BaseModel):
    """Response from the resume parsing endpoint."""

    entries: list[ParsedResumeEntry]
    entry_count: int


class CareerEntryCreate(BaseModel):
    """Schema for manually creating a career entry."""

    entry_type: str
    title: str
    organization: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    bullet_points: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    raw_text: str | None = None


class CareerEntryUpdate(BaseModel):
    """Schema for updating a career entry. All fields optional."""

    entry_type: str | None = None
    title: str | None = None
    organization: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    bullet_points: list[str] | None = None
    tags: list[str] | None = None
    source: str | None = None


class CareerEntryResponse(BaseModel):
    """Response schema for a single career entry."""

    id: str
    entry_type: str
    title: str
    organization: str | None
    start_date: str | None
    end_date: str | None
    bullet_points: list[str]
    tags: list[str]
    source: str
    raw_text: str | None

    model_config = {"from_attributes": True}
