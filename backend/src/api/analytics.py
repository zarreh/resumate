"""Analytics API — feedback quality metrics."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.dependencies import get_current_user
from src.models.user import User
from src.services.analytics import AnalyticsService

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SessionFeedbackSummary(BaseModel):
    session_id: str
    role_title: str | None = None
    company_name: str | None = None
    approved: int
    rejected: int
    edited: int
    total: int
    created_at: str


class FeedbackMetrics(BaseModel):
    total_decisions: int
    approved_count: int
    rejected_count: int
    edited_count: int
    approval_rate: float
    rejection_rate: float
    edit_rate: float
    sessions_with_feedback: int
    per_session: list[SessionFeedbackSummary]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/feedback", response_model=FeedbackMetrics)
async def get_feedback_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackMetrics:
    svc = AnalyticsService(db)
    data = await svc.get_feedback_metrics(current_user.id)
    return FeedbackMetrics(**data)
