"""Resume schemas — EnhancedResume, bullets, sections."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EnhancedBullet(BaseModel):
    """A single enhanced bullet point in the tailored resume."""

    id: str = Field(description="Deterministic ID: '{section_idx}_{bullet_idx}'")
    original_text: str = Field(description="Original bullet text from career entry")
    enhanced_text: str = Field(description="Tailored/enhanced bullet text")
    source_entry_id: str = Field(description="UUID of the source career entry")
    relevance_score: float = Field(
        ge=0.0, le=1.0, description="How relevant this bullet is to the JD"
    )


class ResumeSectionEntry(BaseModel):
    """A single entry within a resume section (e.g., one job or project)."""

    entry_id: str = Field(description="UUID of the source career entry")
    title: str
    organization: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[EnhancedBullet] = Field(default_factory=list)


class ResumeSection(BaseModel):
    """A section in the enhanced resume (e.g., Experience, Education)."""

    id: str = Field(description="Section identifier")
    section_type: str = Field(
        description="Type: summary, experience, education, skills, projects, certifications, volunteer"
    )
    title: str = Field(description="Display title for this section")
    entries: list[ResumeSectionEntry] = Field(default_factory=list)


class EnhancedResume(BaseModel):
    """Complete enhanced resume produced by the Resume Writer agent."""

    summary: str = Field(description="Professional summary tailored to the JD")
    sections: list[ResumeSection] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list, description="Tailored skills list")
    metadata: dict = Field(  # type: ignore[type-arg]
        default_factory=dict,
        description="Additional metadata: section_order, total_bullets, etc.",
    )


class EnhancedResumeOutput(BaseModel):
    """Wrapper for LLM structured output of the enhanced resume."""

    resume: EnhancedResume
