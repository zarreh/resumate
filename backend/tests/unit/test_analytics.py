"""Tests for analytics service and endpoint (Phase 7.3 — Quality Dashboard)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.analytics import FeedbackMetrics, SessionFeedbackSummary
from src.services.analytics import AnalyticsService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_session(*, role_title: str = "Engineer", company: str = "ACME"):
    session = MagicMock()
    session.id = uuid.uuid4()
    session.created_at = datetime(2025, 6, 1, tzinfo=UTC)
    jd = MagicMock()
    jd.analysis = {"role_title": role_title, "company_name": company}
    session.job_description = jd
    return session


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestSessionFeedbackSummary:
    def test_basic(self):
        item = SessionFeedbackSummary(
            session_id="abc",
            role_title="Engineer",
            company_name="ACME",
            approved=5,
            rejected=2,
            edited=1,
            total=8,
            created_at="2025-06-01T00:00:00+00:00",
        )
        assert item.total == 8
        assert item.role_title == "Engineer"

    def test_nullable_fields(self):
        item = SessionFeedbackSummary(
            session_id="abc",
            approved=3,
            rejected=0,
            edited=0,
            total=3,
            created_at="2025-06-01T00:00:00+00:00",
        )
        assert item.role_title is None
        assert item.company_name is None


class TestFeedbackMetrics:
    def test_basic(self):
        metrics = FeedbackMetrics(
            total_decisions=10,
            approved_count=7,
            rejected_count=2,
            edited_count=1,
            approval_rate=0.7,
            rejection_rate=0.2,
            edit_rate=0.1,
            sessions_with_feedback=2,
            per_session=[],
        )
        assert metrics.total_decisions == 10
        assert metrics.approval_rate == 0.7

    def test_empty(self):
        metrics = FeedbackMetrics(
            total_decisions=0,
            approved_count=0,
            rejected_count=0,
            edited_count=0,
            approval_rate=0.0,
            rejection_rate=0.0,
            edit_rate=0.0,
            sessions_with_feedback=0,
            per_session=[],
        )
        assert metrics.sessions_with_feedback == 0


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestAnalyticsService:
    @pytest.mark.asyncio
    async def test_empty_feedback(self):
        db = AsyncMock()
        # First query: feedback aggregation returns empty
        result_mock = MagicMock()
        result_mock.all.return_value = []
        db.execute.return_value = result_mock

        svc = AnalyticsService(db)
        data = await svc.get_feedback_metrics(uuid.uuid4())

        assert data["total_decisions"] == 0
        assert data["approved_count"] == 0
        assert data["rejected_count"] == 0
        assert data["edited_count"] == 0
        assert data["approval_rate"] == 0.0
        assert data["rejection_rate"] == 0.0
        assert data["edit_rate"] == 0.0
        assert data["sessions_with_feedback"] == 0
        assert data["per_session"] == []

    @pytest.mark.asyncio
    async def test_aggregates_correctly(self):
        session = _make_mock_session()
        sid = session.id

        db = AsyncMock()

        # First call: aggregation query returns rows
        agg_result = MagicMock()
        agg_result.all.return_value = [
            (sid, "approved", 5),
            (sid, "rejected", 2),
            (sid, "edited", 1),
        ]

        # Second call: session metadata query
        session_result = MagicMock()
        session_result.scalars.return_value.all.return_value = [session]

        db.execute.side_effect = [agg_result, session_result]

        svc = AnalyticsService(db)
        data = await svc.get_feedback_metrics(uuid.uuid4())

        assert data["total_decisions"] == 8
        assert data["approved_count"] == 5
        assert data["rejected_count"] == 2
        assert data["edited_count"] == 1
        assert data["approval_rate"] == 0.625
        assert data["rejection_rate"] == 0.25
        assert data["edit_rate"] == 0.125
        assert data["sessions_with_feedback"] == 1
        assert len(data["per_session"]) == 1

        ps = data["per_session"][0]
        assert ps["session_id"] == str(sid)
        assert ps["role_title"] == "Engineer"
        assert ps["company_name"] == "ACME"
        assert ps["approved"] == 5
        assert ps["rejected"] == 2
        assert ps["edited"] == 1
        assert ps["total"] == 8

    @pytest.mark.asyncio
    async def test_multiple_sessions(self):
        s1 = _make_mock_session(role_title="Frontend Dev", company="Startup")
        s2 = _make_mock_session(role_title="Backend Dev", company="BigCo")

        db = AsyncMock()

        agg_result = MagicMock()
        agg_result.all.return_value = [
            (s1.id, "approved", 3),
            (s1.id, "rejected", 1),
            (s2.id, "approved", 6),
            (s2.id, "edited", 2),
        ]

        session_result = MagicMock()
        session_result.scalars.return_value.all.return_value = [s2, s1]

        db.execute.side_effect = [agg_result, session_result]

        svc = AnalyticsService(db)
        data = await svc.get_feedback_metrics(uuid.uuid4())

        assert data["total_decisions"] == 12
        assert data["approved_count"] == 9
        assert data["rejected_count"] == 1
        assert data["edited_count"] == 2
        assert data["sessions_with_feedback"] == 2
        assert len(data["per_session"]) == 2


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


class TestFeedbackMetricsEndpoint:
    @pytest.mark.asyncio
    async def test_returns_metrics(self):
        mock_data = {
            "total_decisions": 10,
            "approved_count": 7,
            "rejected_count": 2,
            "edited_count": 1,
            "approval_rate": 0.7,
            "rejection_rate": 0.2,
            "edit_rate": 0.1,
            "sessions_with_feedback": 2,
            "per_session": [],
        }

        with patch("src.api.analytics.AnalyticsService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.get_feedback_metrics.return_value = mock_data
            MockService.return_value = mock_svc

            from src.api.analytics import get_feedback_metrics

            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_db = AsyncMock()

            result = await get_feedback_metrics(current_user=mock_user, db=mock_db)
            assert result.total_decisions == 10
            assert result.approval_rate == 0.7
            assert result.sessions_with_feedback == 2

    @pytest.mark.asyncio
    async def test_returns_empty_metrics(self):
        mock_data = {
            "total_decisions": 0,
            "approved_count": 0,
            "rejected_count": 0,
            "edited_count": 0,
            "approval_rate": 0.0,
            "rejection_rate": 0.0,
            "edit_rate": 0.0,
            "sessions_with_feedback": 0,
            "per_session": [],
        }

        with patch("src.api.analytics.AnalyticsService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.get_feedback_metrics.return_value = mock_data
            MockService.return_value = mock_svc

            from src.api.analytics import get_feedback_metrics

            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_db = AsyncMock()

            result = await get_feedback_metrics(current_user=mock_user, db=mock_db)
            assert result.total_decisions == 0
            assert result.per_session == []
