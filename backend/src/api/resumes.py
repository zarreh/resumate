"""Resume PDF endpoints — generate and download PDFs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.dependencies import get_current_user
from src.models.user import User
from src.schemas.resume import EnhancedResume
from src.services.job import JobService
from src.services.pdf_generator import generate_pdf, render_latex
from src.services.resume_session import ResumeSessionService

router = APIRouter()


class RenderRequest(BaseModel):
    """Request to generate a PDF from a session's enhanced resume."""

    template_name: str = Field(default="professional")


class RenderResponse(BaseModel):
    """Response with the LaTeX source (for preview/debug)."""

    latex_source: str


@router.post("/{session_id}/render", response_model=RenderResponse)
async def render_resume_latex(
    session_id: uuid.UUID,
    body: RenderRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RenderResponse:
    """Render the session's enhanced resume as LaTeX source."""
    resume = await _load_resume(session_id, current_user.id, db)
    req = body or RenderRequest()
    latex = render_latex(resume, req.template_name)
    return RenderResponse(latex_source=latex)


@router.get("/{session_id}/pdf")
async def download_pdf(
    session_id: uuid.UUID,
    template: str = "professional",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate and download the resume as PDF."""
    resume = await _load_resume(session_id, current_user.id, db)

    try:
        pdf_bytes = generate_pdf(resume, template)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=resume.pdf"},
    )


async def _load_resume(
    session_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> EnhancedResume:
    """Load the enhanced resume from a session, raising HTTP errors on failure."""
    svc = JobService(db)
    session = await svc.get_session(user_id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    resume_svc = ResumeSessionService(db)
    resume = await resume_svc.get_enhanced_resume(session)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No enhanced resume on this session",
        )

    return resume
