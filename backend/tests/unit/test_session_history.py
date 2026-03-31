"""Tests for session list and fork (Phase 7.2 — Version History)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.sessions import SessionListItem
from src.services.job import JobService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_jd(*, role_title: str = "Backend Engineer", company: str = "TechCo"):
    jd = MagicMock()
    jd.id = uuid.uuid4()
    jd.analysis = {
        "role_title": role_title,
        "company_name": company,
        "seniority_level": "mid",
        "industry": "Technology",
    }
    jd.embedding = [0.1] * 10
    jd.company_research = None
    return jd


def _make_mock_session(
    *,
    gate: str = "final",
    jd: object | None = None,
    forked_from_id: uuid.UUID | None = None,
    has_resume: bool = True,
):
    session = MagicMock()
    session.id = uuid.uuid4()
    session.user_id = uuid.uuid4()
    session.job_description_id = uuid.uuid4()
    session.current_gate = gate
    session.selected_entry_ids = ["entry-1"]
    session.style_preference = "moderate"
    session.context_text = "I prefer concise bullets"
    session.enhanced_resume = {"summary": "test"} if has_resume else None
    session.forked_from_id = forked_from_id
    session.job_description = jd or _make_mock_jd()
    session.created_at = datetime(2025, 6, 1, tzinfo=UTC)
    session.updated_at = datetime(2025, 6, 2, tzinfo=UTC)
    return session


# ---------------------------------------------------------------------------
# SessionListItem schema tests
# ---------------------------------------------------------------------------


class TestSessionListItem:
    def test_basic_item(self):
        item = SessionListItem(
            id="abc",
            current_gate="final",
            role_title="Engineer",
            company_name="ACME",
            created_at="2025-06-01T00:00:00+00:00",
            updated_at="2025-06-02T00:00:00+00:00",
        )
        assert item.role_title == "Engineer"
        assert item.has_resume is False
        assert item.forked_from_id is None

    def test_nullable_fields(self):
        item = SessionListItem(
            id="abc",
            current_gate="analysis",
            created_at="2025-06-01T00:00:00+00:00",
            updated_at="2025-06-02T00:00:00+00:00",
        )
        assert item.role_title is None
        assert item.company_name is None
        assert item.industry is None


# ---------------------------------------------------------------------------
# list_sessions tests
# ---------------------------------------------------------------------------


class TestListSessions:
    @pytest.mark.asyncio
    async def test_returns_empty_for_new_user(self):
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute.return_value = result_mock

        svc = JobService(db)
        sessions = await svc.list_sessions(uuid.uuid4())
        assert sessions == []

    @pytest.mark.asyncio
    async def test_returns_sessions_with_jd(self):
        jd = _make_mock_jd()
        s1 = _make_mock_session(jd=jd)
        s2 = _make_mock_session(jd=jd, gate="analysis", has_resume=False)

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [s1, s2]
        db.execute.return_value = result_mock

        svc = JobService(db)
        sessions = await svc.list_sessions(s1.user_id)
        assert len(sessions) == 2
        assert sessions[0].current_gate == "final"
        assert sessions[1].current_gate == "analysis"


# ---------------------------------------------------------------------------
# fork_session tests
# ---------------------------------------------------------------------------


class TestForkSession:
    @pytest.mark.asyncio
    async def test_fork_creates_new_session(self):
        source = _make_mock_session(gate="final")
        user_id = source.user_id

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = source
        db.execute.return_value = result_mock

        svc = JobService(db)
        await svc.fork_session(user_id, source.id)

        # The Session constructor is called via db.add
        db.add.assert_called_once()
        added = db.add.call_args[0][0]
        assert added.current_gate == "analysis"
        assert added.job_description_id == source.job_description_id
        assert added.selected_entry_ids == source.selected_entry_ids
        assert added.context_text == source.context_text
        assert added.style_preference == source.style_preference
        assert added.forked_from_id == source.id
        # enhanced_resume should NOT be set (defaults to None via model)

    @pytest.mark.asyncio
    async def test_fork_raises_for_missing_session(self):
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        svc = JobService(db)
        with pytest.raises(ValueError, match="Source session not found"):
            await svc.fork_session(uuid.uuid4(), uuid.uuid4())


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


class TestListEndpoint:
    @pytest.mark.asyncio
    async def test_list_returns_items(self):
        jd = _make_mock_jd()
        s1 = _make_mock_session(jd=jd)

        with patch(
            "src.api.sessions.JobService"
        ) as MockJobService:
            mock_svc = AsyncMock()
            mock_svc.list_sessions.return_value = [s1]
            MockJobService.return_value = mock_svc

            from src.api.sessions import list_sessions

            mock_user = MagicMock()
            mock_user.id = s1.user_id
            mock_db = AsyncMock()

            result = await list_sessions(current_user=mock_user, db=mock_db)
            assert len(result) == 1
            assert result[0].role_title == "Backend Engineer"
            assert result[0].company_name == "TechCo"
            assert result[0].has_resume is True


class TestForkEndpoint:
    @pytest.mark.asyncio
    async def test_fork_returns_201(self):
        source = _make_mock_session()
        new_session = _make_mock_session(forked_from_id=source.id)

        with patch(
            "src.api.sessions.JobService"
        ) as MockJobService:
            mock_svc = AsyncMock()
            mock_svc.fork_session.return_value = new_session
            mock_jd = _make_mock_jd()
            mock_svc.get_job_description.return_value = mock_jd
            MockJobService.return_value = mock_svc

            from src.api.sessions import fork_session

            mock_user = MagicMock()
            mock_user.id = new_session.user_id
            mock_db = AsyncMock()

            result = await fork_session(
                session_id=source.id, current_user=mock_user, db=mock_db
            )
            assert result.forked_from_id == str(source.id)

    @pytest.mark.asyncio
    async def test_fork_returns_404(self):
        with patch(
            "src.api.sessions.JobService"
        ) as MockJobService:
            mock_svc = AsyncMock()
            mock_svc.fork_session.side_effect = ValueError("Source session not found")
            MockJobService.return_value = mock_svc

            from fastapi import HTTPException

            from src.api.sessions import fork_session

            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_db = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await fork_session(
                    session_id=uuid.uuid4(), current_user=mock_user, db=mock_db
                )
            assert exc_info.value.status_code == 404
