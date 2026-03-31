"""Session endpoints — create, retrieve, and manage tailoring sessions."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.fact_checker import FactCheckerAgent
from src.agents.job_analyst import JobAnalystAgent
from src.agents.resume_writer import ResumeWriterAgent
from src.agents.reviewer import ReviewerAgent
from src.core.database import get_db
from src.core.dependencies import get_current_user
from src.models.feedback import FeedbackLog
from src.models.user import User
from src.schemas.job import JDAnalysis
from src.schemas.matching import MatchResult, RankedEntry
from src.schemas.resume import EnhancedResume
from src.services.job import JobService
from src.services.llm_config import get_llm_config
from src.services.match_scoring import MatchScorer
from src.services.resume_session import ResumeSessionService
from src.services.retrieval import RetrievalService
from src.services.session_learning import SessionLearningService

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
    enhanced_resume: dict | None = None  # type: ignore[type-arg]
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
        enhanced_resume=session.enhanced_resume,  # type: ignore[attr-defined]
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


# ---------------------------------------------------------------------------
# Match scoring
# ---------------------------------------------------------------------------


class MatchResponse(BaseModel):
    """Response for match scoring on a session."""

    ranked_entries: list[RankedEntry]
    match_result: MatchResult


@router.get("/{session_id}/match", response_model=MatchResponse)
async def get_match(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchResponse:
    """Get ranked entries and match scoring for a session's JD."""
    svc = JobService(db)
    session = await svc.get_session(current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    # Load the JD and its analysis
    jd = await svc.get_job_description(current_user.id, session.job_description_id)
    if jd is None or jd.analysis is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description has no analysis",
        )

    llm_config = get_llm_config()
    retrieval = RetrievalService(db, llm_config)

    # Ensure JD has an embedding
    if jd.embedding is None:
        await retrieval.embed_job_description(jd)

    # Ensure career entries have embeddings
    await retrieval.embed_all_entries(current_user.id)

    # Find relevant entries
    ranked = await retrieval.find_relevant_entries(
        current_user.id, list(jd.embedding), top_k=20
    )

    # Score the match
    analysis = JDAnalysis.model_validate(jd.analysis)
    scorer = MatchScorer()
    match_result = scorer.score(analysis, ranked)

    return MatchResponse(ranked_entries=ranked, match_result=match_result)


# ---------------------------------------------------------------------------
# Resume generation
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    """Optional overrides for resume generation."""

    style_feedback: str = ""
    mode: str = Field(default="full", pattern="^(full|calibration)$")
    style_preference: str = Field(
        default="moderate", pattern="^(conservative|moderate|aggressive)$"
    )


class EnhancedResumeResponse(BaseModel):
    """Response containing the generated enhanced resume."""

    resume: dict = Field(description="Complete EnhancedResume JSON")  # type: ignore[type-arg]


@router.post("/{session_id}/generate", response_model=EnhancedResumeResponse)
async def generate_resume(
    session_id: uuid.UUID,
    body: GenerateRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EnhancedResumeResponse:
    """Generate a tailored resume for this session using the Resume Writer agent."""
    svc = JobService(db)
    resume_svc = ResumeSessionService(db)

    session = await svc.get_session(current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    # Load JD and analysis
    jd = await svc.get_job_description(current_user.id, session.job_description_id)
    if jd is None or jd.analysis is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description has no analysis",
        )

    jd_analysis = JDAnalysis.model_validate(jd.analysis)

    # Get ranked entries and match result
    llm_config = get_llm_config()
    retrieval = RetrievalService(db, llm_config)

    if jd.embedding is None:
        await retrieval.embed_job_description(jd)
        await db.refresh(jd)
    await retrieval.embed_all_entries(current_user.id)

    jd_embedding = list(jd.embedding) if jd.embedding is not None else []
    ranked = await retrieval.find_relevant_entries(
        current_user.id, jd_embedding, top_k=20
    )

    # Filter to selected entries only
    selected_ids = set(session.selected_entry_ids or [])
    if selected_ids:
        ranked = [e for e in ranked if e.entry_id in selected_ids]

    scorer = MatchScorer()
    match_result = scorer.score(jd_analysis, ranked)

    # Generate the resume
    req = body or GenerateRequest()

    # Save style preference on session
    if req.style_preference:
        await resume_svc.update_style_preference(session, req.style_preference)

    try:
        agent = ResumeWriterAgent(llm_config)
        resume = await agent.write(
            jd_analysis=jd_analysis,
            ranked_entries=ranked,
            match_result=match_result,
            context_text=session.context_text or "",
            style_feedback=req.style_feedback,
            style_preference=req.style_preference,
            mode=req.mode,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to generate resume: {exc}",
        ) from exc

    # Store on session
    await resume_svc.store_enhanced_resume(session, resume)

    return EnhancedResumeResponse(resume=resume.model_dump())


# ---------------------------------------------------------------------------
# Bullet feedback and revision
# ---------------------------------------------------------------------------


class BulletDecision(BaseModel):
    """A single bullet's review decision."""

    bullet_id: str
    decision: str = Field(pattern="^(approved|rejected|edited)$")
    feedback_text: str | None = None
    edited_text: str | None = None


class FeedbackRequest(BaseModel):
    """Submit review decisions for bullets in a session."""

    decisions: list[BulletDecision]


class FeedbackResponse(BaseModel):
    """Response after processing feedback — returns revised resume."""

    resume: dict  # type: ignore[type-arg]
    revised_bullet_ids: list[str]


@router.post("/{session_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    session_id: uuid.UUID,
    body: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """Submit bullet-level feedback and get revised resume."""
    svc = JobService(db)
    resume_svc = ResumeSessionService(db)

    session = await svc.get_session(current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    current_resume = await resume_svc.get_enhanced_resume(session)
    if current_resume is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No enhanced resume exists on this session",
        )

    # 1. Log all feedback
    for d in body.decisions:
        log = FeedbackLog(
            session_id=session.id,
            bullet_id=d.bullet_id,
            decision=d.decision,
            feedback_text=d.feedback_text,
        )
        db.add(log)
    await db.commit()

    # 2. Apply edits directly for "edited" decisions
    edited_ids: list[str] = []
    for d in body.decisions:
        if d.decision == "edited" and d.edited_text:
            _apply_edit(current_resume, d.bullet_id, d.edited_text)
            edited_ids.append(d.bullet_id)

    # 3. Collect rejected bullets for revision
    rejected = [d for d in body.decisions if d.decision == "rejected"]

    if not rejected:
        # No rejections — just save edits and return
        await resume_svc.store_enhanced_resume(session, current_resume)
        return FeedbackResponse(
            resume=current_resume.model_dump(),
            revised_bullet_ids=edited_ids,
        )

    # 4. Build revision context and regenerate rejected bullets
    jd = await svc.get_job_description(current_user.id, session.job_description_id)
    if jd is None or jd.analysis is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description has no analysis",
        )

    jd_analysis = JDAnalysis.model_validate(jd.analysis)

    # Build feedback string for the LLM
    feedback_parts = []
    for d in rejected:
        bullet_text = _find_bullet_text(current_resume, d.bullet_id)
        feedback_parts.append(
            f"Bullet '{d.bullet_id}' ({bullet_text}): "
            f"REJECTED — {d.feedback_text or 'no specific feedback'}"
        )

    revision_feedback = (
        "The user rejected the following bullets. Rewrite ONLY these bullets "
        "while keeping all other bullets unchanged:\n\n"
        + "\n".join(feedback_parts)
    )

    # Get Match data for context
    llm_config = get_llm_config()
    retrieval = RetrievalService(db, llm_config)

    if jd.embedding is None:
        await retrieval.embed_job_description(jd)
        await db.refresh(jd)
    await retrieval.embed_all_entries(current_user.id)

    jd_embedding = list(jd.embedding) if jd.embedding is not None else []
    ranked = await retrieval.find_relevant_entries(
        current_user.id, jd_embedding, top_k=20
    )

    selected_ids = set(session.selected_entry_ids or [])
    if selected_ids:
        ranked = [e for e in ranked if e.entry_id in selected_ids]

    scorer = MatchScorer()
    match_result = scorer.score(jd_analysis, ranked)

    try:
        agent = ResumeWriterAgent(llm_config)
        revised_resume = await agent.write(
            jd_analysis=jd_analysis,
            ranked_entries=ranked,
            match_result=match_result,
            context_text=session.context_text or "",
            style_feedback=revision_feedback,
            style_preference=session.style_preference or "moderate",
            mode="calibration",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to revise resume: {exc}",
        ) from exc

    # 5. Merge: only replace rejected bullets in the current resume
    revised_ids = _merge_revisions(
        current_resume, revised_resume, [d.bullet_id for d in rejected]
    )

    await resume_svc.store_enhanced_resume(session, current_resume)

    return FeedbackResponse(
        resume=current_resume.model_dump(),
        revised_bullet_ids=edited_ids + revised_ids,
    )


def _find_bullet_text(resume: EnhancedResume, bullet_id: str) -> str:
    """Find a bullet's enhanced text by ID."""
    for section in resume.sections:
        for entry in section.entries:
            for bullet in entry.bullets:
                if bullet.id == bullet_id:
                    return bullet.enhanced_text
    return "(not found)"


def _apply_edit(resume: EnhancedResume, bullet_id: str, new_text: str) -> None:
    """Apply a direct text edit to a bullet in the resume."""
    for section in resume.sections:
        for entry in section.entries:
            for bullet in entry.bullets:
                if bullet.id == bullet_id:
                    bullet.enhanced_text = new_text
                    return


def _merge_revisions(
    current: EnhancedResume,
    revised: EnhancedResume,
    rejected_ids: list[str],
) -> list[str]:
    """Replace rejected bullets in current resume with revised versions.

    Returns list of bullet IDs that were actually updated.
    """
    # Build a lookup of revised bullets
    revised_lookup: dict[str, str] = {}
    for section in revised.sections:
        for entry in section.entries:
            for bullet in entry.bullets:
                if bullet.id in rejected_ids:
                    revised_lookup[bullet.id] = bullet.enhanced_text

    updated_ids: list[str] = []
    for section in current.sections:
        for entry in section.entries:
            for bullet in entry.bullets:
                if bullet.id in revised_lookup:
                    bullet.enhanced_text = revised_lookup[bullet.id]
                    updated_ids.append(bullet.id)

    return updated_ids


# ---------------------------------------------------------------------------
# Fact checking
# ---------------------------------------------------------------------------


class FactCheckResponse(BaseModel):
    """Response containing the fact-check report."""

    report: dict = Field(description="Complete FactCheckReport JSON")  # type: ignore[type-arg]


@router.post("/{session_id}/fact-check", response_model=FactCheckResponse)
async def fact_check_resume(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FactCheckResponse:
    """Run the Fact Checker agent on the session's enhanced resume."""
    svc = JobService(db)
    resume_svc = ResumeSessionService(db)

    session = await svc.get_session(current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    current_resume = await resume_svc.get_enhanced_resume(session)
    if current_resume is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No enhanced resume exists on this session",
        )

    # Load career entries for the user
    from sqlalchemy import select

    from src.models.career import CareerHistoryEntry

    result = await db.execute(
        select(CareerHistoryEntry).where(
            CareerHistoryEntry.user_id == current_user.id
        )
    )
    entries = result.scalars().all()

    career_dicts = [
        {
            "id": str(e.id),
            "entry_type": e.entry_type,
            "title": e.title,
            "organization": e.organization,
            "start_date": e.start_date.isoformat() if e.start_date else None,
            "end_date": e.end_date.isoformat() if e.end_date else None,
            "bullet_points": e.bullet_points or [],
            "tags": e.tags or [],
            "source": e.source,
        }
        for e in entries
    ]

    try:
        llm_config = get_llm_config()
        agent = FactCheckerAgent(llm_config)
        report = await agent.check(current_resume, career_dicts)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to fact-check resume: {exc}",
        ) from exc

    return FactCheckResponse(report=report.model_dump())


# ---------------------------------------------------------------------------
# Resume review
# ---------------------------------------------------------------------------


class ReviewResponse(BaseModel):
    """Response containing the two-pass review report."""

    report: dict = Field(description="Complete ReviewReport JSON")  # type: ignore[type-arg]


@router.post("/{session_id}/review", response_model=ReviewResponse)
async def review_resume(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Run the Reviewer agent on the session's enhanced resume."""
    svc = JobService(db)
    resume_svc = ResumeSessionService(db)

    session = await svc.get_session(current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    current_resume = await resume_svc.get_enhanced_resume(session)
    if current_resume is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No enhanced resume exists on this session",
        )

    # Load the JD analysis
    jd = await svc.get_job_description(current_user.id, session.job_description_id)
    if jd is None or jd.analysis is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description has no analysis",
        )

    jd_analysis = JDAnalysis.model_validate(jd.analysis)

    try:
        llm_config = get_llm_config()
        agent = ReviewerAgent(llm_config)
        report = await agent.review(current_resume, jd_analysis)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to review resume: {exc}",
        ) from exc

    return ReviewResponse(report=report.model_dump())


# ---------------------------------------------------------------------------
# ATS Scoring
# ---------------------------------------------------------------------------


class ATSScoreResponse(BaseModel):
    """Response containing the ATS score."""

    score: dict = Field(description="Complete ATSScore JSON")  # type: ignore[type-arg]


@router.post("/{session_id}/ats-score", response_model=ATSScoreResponse)
async def ats_score_resume(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ATSScoreResponse:
    """Run ATS scoring on the session's enhanced resume."""
    from src.services.ats_scoring import ATSScorer

    svc = JobService(db)
    resume_svc = ResumeSessionService(db)

    session = await svc.get_session(current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    current_resume = await resume_svc.get_enhanced_resume(session)
    if current_resume is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No enhanced resume exists on this session",
        )

    jd = await svc.get_job_description(current_user.id, session.job_description_id)
    if jd is None or jd.analysis is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description has no analysis",
        )

    jd_analysis = JDAnalysis.model_validate(jd.analysis)

    scorer = ATSScorer()
    result = scorer.score(current_resume, jd_analysis)

    return ATSScoreResponse(score=result.model_dump())


# ---------------------------------------------------------------------------
# Session Completion — record decisions for future learning
# ---------------------------------------------------------------------------


class CompleteResponse(BaseModel):
    """Response after completing a session and recording decisions."""

    session_id: str
    decision_id: str
    message: str = "Session completed and decisions recorded"


@router.post("/{session_id}/complete", response_model=CompleteResponse)
async def complete_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompleteResponse:
    """Mark a session as complete and store decisions for future learning.

    Should be called when the user is satisfied with the final resume.
    Records the session's decisions snapshot with the JD embedding for
    cosine similarity retrieval in future sessions.
    """
    svc = JobService(db)
    session = await svc.get_session(current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    if session.current_gate != "final":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session must be at 'final' gate to complete (currently at '{session.current_gate}')",
        )

    if session.enhanced_resume is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has no enhanced resume to record",
        )

    llm_config = get_llm_config()
    learning_svc = SessionLearningService(db, llm_config)

    try:
        decision = await learning_svc.complete_session(session, current_user.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record session decisions: {exc}",
        ) from exc

    return CompleteResponse(
        session_id=str(session.id),
        decision_id=str(decision.id),
    )


# ---------------------------------------------------------------------------
# Cover Letter Generation
# ---------------------------------------------------------------------------


class CoverLetterResponse(BaseModel):
    """Response containing the generated cover letter."""

    id: str
    content: str


@router.post("/{session_id}/cover-letter", response_model=CoverLetterResponse)
async def generate_cover_letter(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CoverLetterResponse:
    """Generate a cover letter for the session's enhanced resume."""
    from src.agents.cover_letter import CoverLetterAgent
    from src.models.cover_letter import CoverLetter

    svc = JobService(db)
    resume_svc = ResumeSessionService(db)

    session = await svc.get_session(current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    current_resume = await resume_svc.get_enhanced_resume(session)
    if current_resume is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No enhanced resume exists on this session",
        )

    jd = await svc.get_job_description(current_user.id, session.job_description_id)
    if jd is None or jd.analysis is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description has no analysis",
        )

    jd_analysis = JDAnalysis.model_validate(jd.analysis)

    try:
        llm_config = get_llm_config()
        agent = CoverLetterAgent(llm_config)
        content = await agent.generate(current_resume, jd_analysis)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to generate cover letter: {exc}",
        ) from exc

    # Store in DB
    cover_letter = CoverLetter(
        session_id=session.id,
        user_id=current_user.id,
        content=content,
    )
    db.add(cover_letter)
    await db.commit()
    await db.refresh(cover_letter)

    return CoverLetterResponse(id=str(cover_letter.id), content=content)


@router.get("/{session_id}/cover-letter", response_model=CoverLetterResponse | None)
async def get_cover_letter(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CoverLetterResponse | None:
    """Get the latest cover letter for a session."""
    from sqlalchemy import select

    from src.models.cover_letter import CoverLetter

    svc = JobService(db)
    session = await svc.get_session(current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    result = await db.execute(
        select(CoverLetter)
        .where(
            CoverLetter.session_id == session.id,
            CoverLetter.user_id == current_user.id,
        )
        .order_by(CoverLetter.created_at.desc())
        .limit(1)
    )
    cl = result.scalar_one_or_none()
    if cl is None:
        return None

    return CoverLetterResponse(id=str(cl.id), content=cl.content)
