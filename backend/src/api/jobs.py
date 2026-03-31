"""Job description endpoints — parse JD, list history, manage sessions."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.job_analyst import JobAnalystAgent
from src.core.database import get_db
from src.core.dependencies import get_current_user
from src.models.user import User
from src.schemas.job import JDAnalysis, JobDescriptionResponse, JobParseRequest
from src.services.jd_scraper import ScraperError, fetch_job_description
from src.services.job import JobService
from src.services.llm_config import get_llm_config

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _jd_to_response(jd: object) -> JobDescriptionResponse:
    """Convert a JobDescription ORM object to a response schema."""
    analysis_dict = jd.analysis  # type: ignore[attr-defined]
    return JobDescriptionResponse(
        id=str(jd.id),  # type: ignore[attr-defined]
        raw_text=jd.raw_text,  # type: ignore[attr-defined]
        analysis=JDAnalysis.model_validate(analysis_dict) if analysis_dict else None,
        created_at=jd.created_at.isoformat(),  # type: ignore[attr-defined]
    )


# ---------------------------------------------------------------------------
# Parse & Store
# ---------------------------------------------------------------------------


@router.post("/parse", response_model=JobDescriptionResponse, status_code=status.HTTP_201_CREATED)
async def parse_job_description(
    body: JobParseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobDescriptionResponse:
    """Parse a job description text (or fetch from URL) and store the analysis."""
    svc = JobService(db)

    # Resolve text: fetch from URL if provided
    raw_text = body.text
    if body.url:
        try:
            raw_text = await fetch_job_description(body.url)
        except ScraperError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to fetch URL: {exc}",
            ) from exc

    # Create the JD record first
    jd = await svc.create_job_description(current_user.id, raw_text)

    # Run the Job Analyst agent
    try:
        agent = JobAnalystAgent(get_llm_config())
        analysis = await agent.analyze(raw_text)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to analyze job description: {exc}",
        ) from exc

    # Store the analysis
    jd = await svc.update_analysis(jd, analysis)
    return _jd_to_response(jd)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


@router.get("/history", response_model=list[JobDescriptionResponse])
async def list_job_descriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[JobDescriptionResponse]:
    """List all analyzed job descriptions for the current user."""
    svc = JobService(db)
    jds = await svc.list_job_descriptions(current_user.id)
    return [_jd_to_response(jd) for jd in jds]


@router.get("/{job_id}", response_model=JobDescriptionResponse)
async def get_job_description(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobDescriptionResponse:
    """Get a specific job description by ID."""
    svc = JobService(db)
    jd = await svc.get_job_description(current_user.id, job_id)
    if jd is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found"
        )
    return _jd_to_response(jd)
