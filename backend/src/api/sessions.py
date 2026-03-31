"""Session endpoints — create, retrieve, and manage tailoring sessions."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.job_analyst import JobAnalystAgent
from src.core.database import get_db
from src.core.dependencies import get_current_user
from src.models.user import User
from src.schemas.job import JDAnalysis
from src.services.job import JobService
from src.services.llm_config import get_llm_config

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas (session-specific, kept close to the routes)
# ---------------------------------------------------------------------------


class SessionStartRequest(BaseModel):
    """Request body to start a new tailoring session."""

    text: str = Field(min_length=1, description="Raw job description text")


class SessionResponse(BaseModel):
    """Response for a tailoring session."""

    id: str
    job_description_id: str
    current_gate: str
    selected_entry_ids: list[str]
    context_text: str | None
    style_preference: str | None
    analysis: JDAnalysis | None = None
    created_at: str

    model_config = {"from_attributes": True}


class GateApprovalRequest(BaseModel):
    """Request body to approve a gate and advance the session."""

    gate: str = Field(description="The gate being approved (e.g. 'analysis')")
    selected_entry_ids: list[str] = Field(default_factory=list)
    context_text: str | None = None


# Gate progression map
_GATE_NEXT = {
    "analysis": "calibration",
    "calibration": "review",
    "review": "final",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session_to_response(
    session: object, analysis: JDAnalysis | None = None
) -> SessionResponse:
    """Convert a Session ORM object to a response schema."""
    return SessionResponse(
        id=str(session.id),  # type: ignore[attr-defined]
        job_description_id=str(session.job_description_id),  # type: ignore[attr-defined]
        current_gate=session.current_gate,  # type: ignore[attr-defined]
        selected_entry_ids=session.selected_entry_ids or [],  # type: ignore[attr-defined]
        context_text=session.context_text,  # type: ignore[attr-defined]
        style_preference=session.style_preference,  # type: ignore[attr-defined]
        analysis=analysis,
        created_at=session.created_at.isoformat(),  # type: ignore[attr-defined]
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/start", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    body: SessionStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Start a new tailoring session: parse JD, create session, return analysis."""
    svc = JobService(db)

    # 1. Create job description record
    jd = await svc.create_job_description(current_user.id, body.text)

    # 2. Analyze the JD
    try:
        agent = JobAnalystAgent(get_llm_config())
        analysis = await agent.analyze(body.text)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to analyze job description: {exc}",
        ) from exc

    # 3. Store analysis on the JD
    jd = await svc.update_analysis(jd, analysis)

    # 4. Create session
    session = await svc.create_session(current_user.id, jd.id)

    return _session_to_response(session, analysis=analysis)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Get session details including the JD analysis."""
    svc = JobService(db)
    session = await svc.get_session(current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    # Load the JD analysis
    jd = await svc.get_job_description(current_user.id, session.job_description_id)
    analysis = JDAnalysis.model_validate(jd.analysis) if jd and jd.analysis else None

    return _session_to_response(session, analysis=analysis)


@router.post("/{session_id}/approve", response_model=SessionResponse)
async def approve_gate(
    session_id: uuid.UUID,
    body: GateApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Approve the current gate and advance the session."""
    svc = JobService(db)
    session = await svc.get_session(current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    if session.current_gate != body.gate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is at gate '{session.current_gate}', not '{body.gate}'",
        )

    next_gate = _GATE_NEXT.get(body.gate)
    if next_gate is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gate '{body.gate}' cannot be approved (already final or unknown)",
        )

    # Save selections and context
    if body.selected_entry_ids or body.context_text is not None:
        session = await svc.update_session_selections(
            session, body.selected_entry_ids, body.context_text
        )

    # Advance gate
    session = await svc.update_session_gate(session, next_gate)

    # Load JD analysis for response
    jd = await svc.get_job_description(current_user.id, session.job_description_id)
    analysis = JDAnalysis.model_validate(jd.analysis) if jd and jd.analysis else None

    return _session_to_response(session, analysis=analysis)
