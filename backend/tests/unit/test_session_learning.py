"""Tests for the Session Learning service, completion endpoint, and
resume writer past-session context integration."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.resume import (
    EnhancedBullet,
    EnhancedResume,
    ResumeSection,
    ResumeSectionEntry,
)
from src.services.session_learning import SessionLearningService

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------


def _make_enhanced_resume() -> EnhancedResume:
    return EnhancedResume(
        summary="Experienced backend engineer with 5+ years of Python and FastAPI.",
        sections=[
            ResumeSection(
                id="s0",
                section_type="experience",
                title="Work Experience",
                entries=[
                    ResumeSectionEntry(
                        entry_id="entry-1",
                        title="Backend Developer",
                        organization="TechCo",
                        start_date="2020-01",
                        end_date="2023-12",
                        bullets=[
                            EnhancedBullet(
                                id="0_0",
                                original_text="Built APIs using Python",
                                enhanced_text="Designed and implemented production RESTful APIs using Python and FastAPI",
                                source_entry_id="entry-1",
                                relevance_score=0.95,
                            ),
                            EnhancedBullet(
                                id="0_1",
                                original_text="Managed databases",
                                enhanced_text="Managed PostgreSQL databases with complex queries supporting 10K+ daily users",
                                source_entry_id="entry-1",
                                relevance_score=0.88,
                            ),
                        ],
                    )
                ],
            )
        ],
        skills=["Python", "FastAPI", "PostgreSQL"],
        metadata={"section_order": ["experience", "skills"]},
    )


def _make_mock_session(*, gate: str = "final", has_resume: bool = True):
    session = MagicMock()
    session.id = uuid.uuid4()
    session.user_id = uuid.uuid4()
    session.job_description_id = uuid.uuid4()
    session.current_gate = gate
    session.selected_entry_ids = ["entry-1"]
    session.style_preference = "moderate"
    session.context_text = "I prefer concise bullets"
    if has_resume:
        session.enhanced_resume = _make_enhanced_resume().model_dump()
    else:
        session.enhanced_resume = None
    return session


def _make_mock_jd(*, has_embedding: bool = True):
    jd = MagicMock()
    jd.id = uuid.uuid4()
    jd.raw_text = "Senior Backend Engineer wanted..."
    jd.analysis = {
        "role_title": "Senior Backend Engineer",
        "industry": "technology",
        "required_skills": ["Python", "FastAPI"],
        "preferred_skills": ["GraphQL"],
        "ats_keywords": ["Backend", "Python"],
        "tech_stack": ["Python", "FastAPI"],
        "responsibilities": ["Build APIs"],
        "qualifications": ["5+ years"],
        "domain_expectations": [],
        "seniority_level": "senior",
        "company_name": "Acme",
    }
    jd.embedding = [0.1] * 1536 if has_embedding else None
    return jd


# ---------------------------------------------------------------------------
# format_past_sessions_context tests
# ---------------------------------------------------------------------------


class TestFormatPastSessionsContext:
    """Tests for the context formatting function (no DB needed)."""

    def test_empty_list_returns_empty(self) -> None:
        svc = SessionLearningService.__new__(SessionLearningService)
        result = svc.format_past_sessions_context([])
        assert result == ""

    def test_single_session_with_rewrites(self) -> None:
        svc = SessionLearningService.__new__(SessionLearningService)
        sessions = [
            {
                "_similarity": 0.91,
                "_session_id": str(uuid.uuid4()),
                "role_title": "Backend Developer",
                "industry": "fintech",
                "style_preference": "aggressive",
                "section_order": ["experience", "skills", "education"],
                "bullet_rewrites": [
                    {
                        "bullet_id": "0_0",
                        "original": "Built APIs",
                        "enhanced": "Designed and deployed RESTful APIs",
                    }
                ],
                "feedback": {
                    "approved": [{"bullet_id": "0_0"}],
                    "rejected": [],
                    "edited": [],
                },
            }
        ]

        result = svc.format_past_sessions_context(sessions)

        assert "## Past Session Insights" in result
        assert "Backend Developer" in result
        assert "fintech" in result
        assert "aggressive" in result
        assert "experience, skills, education" in result
        assert "Built APIs" in result
        assert "Designed and deployed RESTful APIs" in result
        assert "1 approved" in result
        assert "0 rejected" in result

    def test_multiple_sessions_capped_rewrites(self) -> None:
        svc = SessionLearningService.__new__(SessionLearningService)
        sessions = [
            {
                "_similarity": 0.95,
                "_session_id": str(uuid.uuid4()),
                "role_title": "SRE",
                "industry": "cloud",
                "style_preference": "conservative",
                "section_order": ["experience"],
                "bullet_rewrites": [
                    {"bullet_id": f"b{i}", "original": f"orig{i}", "enhanced": f"enh{i}"}
                    for i in range(10)  # More than 3 — should be capped in display
                ],
                "feedback": {"approved": [], "rejected": [], "edited": []},
            },
            {
                "_similarity": 0.82,
                "_session_id": str(uuid.uuid4()),
                "role_title": "DevOps",
                "industry": "saas",
                "style_preference": "moderate",
                "section_order": [],
                "bullet_rewrites": [],
                "feedback": {"approved": [], "rejected": [], "edited": []},
            },
        ]

        result = svc.format_past_sessions_context(sessions)

        assert "Past Session 1" in result
        assert "Past Session 2" in result
        assert "SRE" in result
        assert "DevOps" in result
        # Only 3 rewrites shown per session
        assert result.count("Original:") == 3

    def test_session_without_optional_fields(self) -> None:
        svc = SessionLearningService.__new__(SessionLearningService)
        sessions = [
            {
                "_similarity": 0.75,
                "_session_id": str(uuid.uuid4()),
            }
        ]

        result = svc.format_past_sessions_context(sessions)

        assert "Past Session 1" in result
        assert "Unknown Role" in result
        assert "Unknown" in result


# ---------------------------------------------------------------------------
# complete_session tests (mock DB)
# ---------------------------------------------------------------------------


class TestCompleteSession:
    """Tests for the SessionLearningService.complete_session method."""

    @pytest.mark.asyncio
    async def test_creates_decision_with_snapshot(self) -> None:
        db = AsyncMock()
        db.execute = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        mock_jd = _make_mock_jd()
        mock_session = _make_mock_session()

        # Mock JD query
        jd_result = MagicMock()
        jd_result.scalar_one_or_none.return_value = mock_jd

        # Mock feedback query
        feedback_result = MagicMock()
        feedback_result.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(side_effect=[jd_result, feedback_result])

        llm_config = MagicMock()
        svc = SessionLearningService(db, llm_config)

        await svc.complete_session(mock_session, mock_session.user_id)

        # Verify db.add was called with a SessionDecision
        db.add.assert_called_once()
        added_obj = db.add.call_args[0][0]
        assert added_obj.session_id == mock_session.id
        assert added_obj.user_id == mock_session.user_id
        assert added_obj.decisions_snapshot is not None
        assert added_obj.decisions_snapshot["role_title"] == "Senior Backend Engineer"
        assert added_obj.decisions_snapshot["style_preference"] == "moderate"
        assert len(added_obj.decisions_snapshot["bullet_rewrites"]) == 2  # Both bullets differ

    @pytest.mark.asyncio
    async def test_copies_jd_embedding(self) -> None:
        db = AsyncMock()
        db.execute = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        mock_jd = _make_mock_jd(has_embedding=True)
        mock_session = _make_mock_session()

        jd_result = MagicMock()
        jd_result.scalar_one_or_none.return_value = mock_jd

        feedback_result = MagicMock()
        feedback_result.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(side_effect=[jd_result, feedback_result])

        llm_config = MagicMock()
        svc = SessionLearningService(db, llm_config)

        await svc.complete_session(mock_session, mock_session.user_id)

        added_obj = db.add.call_args[0][0]
        assert added_obj.embedding is not None
        assert len(added_obj.embedding) == 1536

    @pytest.mark.asyncio
    async def test_handles_no_jd_embedding_generates_one(self) -> None:
        db = AsyncMock()
        db.execute = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        mock_jd = _make_mock_jd(has_embedding=False)
        mock_session = _make_mock_session()

        jd_result = MagicMock()
        jd_result.scalar_one_or_none.return_value = mock_jd

        feedback_result = MagicMock()
        feedback_result.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(side_effect=[jd_result, feedback_result])

        # After embed_job_description, the JD gets an embedding
        def set_embedding(jd):
            jd.embedding = [0.2] * 1536

        llm_config = MagicMock()
        svc = SessionLearningService(db, llm_config)
        svc._retrieval = MagicMock()
        svc._retrieval.embed_job_description = AsyncMock(side_effect=lambda jd: set_embedding(jd))

        await svc.complete_session(mock_session, mock_session.user_id)

        svc._retrieval.embed_job_description.assert_called_once()


# ---------------------------------------------------------------------------
# find_similar_sessions tests (mock DB)
# ---------------------------------------------------------------------------


class TestFindSimilarSessions:
    """Tests for the SessionLearningService.find_similar_sessions method."""

    @pytest.mark.asyncio
    async def test_returns_sorted_by_similarity(self) -> None:
        db = AsyncMock()

        row1 = MagicMock()
        row1.id = uuid.uuid4()
        row1.session_id = uuid.uuid4()
        row1.decisions_snapshot = {"role_title": "Backend Dev", "industry": "tech"}
        row1.similarity = 0.95

        row2 = MagicMock()
        row2.id = uuid.uuid4()
        row2.session_id = uuid.uuid4()
        row2.decisions_snapshot = {"role_title": "Frontend Dev", "industry": "saas"}
        row2.similarity = 0.82

        result_mock = MagicMock()
        result_mock.fetchall.return_value = [row1, row2]
        db.execute = AsyncMock(return_value=result_mock)

        llm_config = MagicMock()
        svc = SessionLearningService(db, llm_config)

        results = await svc.find_similar_sessions(uuid.uuid4(), [0.1] * 1536)

        assert len(results) == 2
        assert results[0]["_similarity"] == 0.95
        assert results[0]["role_title"] == "Backend Dev"
        assert results[1]["_similarity"] == 0.82

    @pytest.mark.asyncio
    async def test_excludes_current_session(self) -> None:
        db = AsyncMock()

        result_mock = MagicMock()
        result_mock.fetchall.return_value = []
        db.execute = AsyncMock(return_value=result_mock)

        llm_config = MagicMock()
        svc = SessionLearningService(db, llm_config)

        exclude_id = uuid.uuid4()
        await svc.find_similar_sessions(
            uuid.uuid4(), [0.1] * 1536, exclude_session_id=exclude_id
        )

        # Verify the SQL includes the exclusion
        call_args = db.execute.call_args
        params = call_args[0][1]
        assert params["exclude_session_id"] == exclude_id

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        db = AsyncMock()

        result_mock = MagicMock()
        result_mock.fetchall.return_value = []
        db.execute = AsyncMock(return_value=result_mock)

        llm_config = MagicMock()
        svc = SessionLearningService(db, llm_config)

        results = await svc.find_similar_sessions(uuid.uuid4(), [0.1] * 1536)

        assert results == []


# ---------------------------------------------------------------------------
# Resume Writer agent past_session_context tests
# ---------------------------------------------------------------------------


class TestWriterPastSessionContext:
    """Tests that the Resume Writer agent correctly handles past session context."""

    def test_build_user_message_includes_past_context(self) -> None:
        from src.agents.resume_writer.agent import ResumeWriterAgent, WriterState

        # Create a mock agent to test the message builder
        with patch.object(ResumeWriterAgent, "__init__", lambda self, *a, **kw: None):
            agent = ResumeWriterAgent.__new__(ResumeWriterAgent)

        state: WriterState = {
            "jd_analysis": {
                "role_title": "Backend Dev",
                "company_name": None,
                "seniority_level": "senior",
                "industry": "tech",
                "required_skills": ["Python"],
                "preferred_skills": [],
                "ats_keywords": ["Python"],
                "tech_stack": ["Python"],
                "responsibilities": ["Build APIs"],
                "qualifications": [],
                "domain_expectations": [],
            },
            "ranked_entries": [],
            "match_result": {
                "overall_score": 80,
                "gap_analysis": {},
                "recommended_section_order": [],
            },
            "context_text": "",
            "style_feedback": "",
            "style_preference": "moderate",
            "mode": "full",
            "past_session_context": "## Past Session Insights\nUse aggressive style for senior roles.",
            "resume": None,
        }

        message = agent._build_user_message(state)  # noqa: SLF001

        assert "## Past Session Insights" in message
        assert "aggressive style for senior roles" in message

    def test_build_user_message_empty_past_context(self) -> None:
        from src.agents.resume_writer.agent import ResumeWriterAgent, WriterState

        with patch.object(ResumeWriterAgent, "__init__", lambda self, *a, **kw: None):
            agent = ResumeWriterAgent.__new__(ResumeWriterAgent)

        state: WriterState = {
            "jd_analysis": {
                "role_title": "Backend Dev",
                "company_name": None,
                "seniority_level": "senior",
                "industry": "tech",
                "required_skills": [],
                "preferred_skills": [],
                "ats_keywords": [],
                "tech_stack": [],
                "responsibilities": [],
                "qualifications": [],
                "domain_expectations": [],
            },
            "ranked_entries": [],
            "match_result": {"overall_score": 0, "gap_analysis": {}, "recommended_section_order": []},
            "context_text": "",
            "style_feedback": "",
            "style_preference": "moderate",
            "mode": "full",
            "past_session_context": "",
            "resume": None,
        }

        message = agent._build_user_message(state)  # noqa: SLF001

        assert "Past Session" not in message


# ---------------------------------------------------------------------------
# Completion endpoint tests (mock everything)
# ---------------------------------------------------------------------------


class TestCompleteEndpoint:
    """Tests for the POST /sessions/{id}/complete endpoint."""

    @pytest.mark.asyncio
    async def test_complete_requires_final_gate(self) -> None:
        """Session must be at 'final' gate to complete."""
        mock_session = _make_mock_session(gate="review")

        with (
            patch("src.api.sessions.JobService") as MockJobService,
            patch("src.api.sessions.get_llm_config"),
        ):
            MockJobService.return_value.get_session = AsyncMock(return_value=mock_session)

            from httpx import ASGITransport, AsyncClient

            from src.main import app

            transport = ASGITransport(app=app)  # type: ignore[arg-type]
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Register a user to get a token
                email = f"test-{uuid.uuid4().hex[:8]}@example.com"
                resp = await client.post(
                    "/api/v1/auth/register",
                    json={"name": "T", "email": email, "password": "password123"},
                )
                token = resp.json()["access_token"]

                resp = await client.post(
                    f"/api/v1/sessions/{uuid.uuid4()}/complete",
                    headers={"Authorization": f"Bearer {token}"},
                )

                assert resp.status_code == 400
                assert "final" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_complete_requires_resume(self) -> None:
        """Session must have an enhanced resume to complete."""
        mock_session = _make_mock_session(gate="final", has_resume=False)

        with (
            patch("src.api.sessions.JobService") as MockJobService,
            patch("src.api.sessions.get_llm_config"),
        ):
            MockJobService.return_value.get_session = AsyncMock(return_value=mock_session)

            from httpx import ASGITransport, AsyncClient

            from src.main import app

            transport = ASGITransport(app=app)  # type: ignore[arg-type]
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                email = f"test-{uuid.uuid4().hex[:8]}@example.com"
                resp = await client.post(
                    "/api/v1/auth/register",
                    json={"name": "T", "email": email, "password": "password123"},
                )
                token = resp.json()["access_token"]

                resp = await client.post(
                    f"/api/v1/sessions/{uuid.uuid4()}/complete",
                    headers={"Authorization": f"Bearer {token}"},
                )

                assert resp.status_code == 400
                assert "enhanced resume" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_complete_success(self) -> None:
        """Successful session completion returns decision ID."""
        mock_session = _make_mock_session(gate="final")
        mock_decision = MagicMock()
        mock_decision.id = uuid.uuid4()

        with (
            patch("src.api.sessions.JobService") as MockJobService,
            patch("src.api.sessions.get_llm_config"),
            patch("src.api.sessions.SessionLearningService") as MockLearning,
        ):
            MockJobService.return_value.get_session = AsyncMock(return_value=mock_session)
            MockLearning.return_value.complete_session = AsyncMock(return_value=mock_decision)

            from httpx import ASGITransport, AsyncClient

            from src.main import app

            transport = ASGITransport(app=app)  # type: ignore[arg-type]
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                email = f"test-{uuid.uuid4().hex[:8]}@example.com"
                resp = await client.post(
                    "/api/v1/auth/register",
                    json={"name": "T", "email": email, "password": "password123"},
                )
                token = resp.json()["access_token"]

                resp = await client.post(
                    f"/api/v1/sessions/{uuid.uuid4()}/complete",
                    headers={"Authorization": f"Bearer {token}"},
                )

                assert resp.status_code == 200
                data = resp.json()
                assert data["decision_id"] == str(mock_decision.id)
                assert data["session_id"] == str(mock_session.id)
