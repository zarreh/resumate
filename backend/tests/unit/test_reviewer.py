"""Tests for the Reviewer agent and review endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from src.agents.reviewer.schemas import (
    ReviewAnnotation,
    ReviewOutput,
    ReviewReport,
)
from src.schemas.job import JDAnalysis
from src.schemas.resume import (
    EnhancedBullet,
    EnhancedResume,
    ResumeSection,
    ResumeSectionEntry,
)

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_ANALYSIS = JDAnalysis(
    role_title="Senior Backend Engineer",
    company_name="Acme Corp",
    seniority_level="senior",
    industry="marketplace",
    required_skills=["Python", "FastAPI"],
    preferred_skills=["GraphQL"],
    ats_keywords=["Backend Engineer", "Python"],
    tech_stack=["Python", "FastAPI", "PostgreSQL"],
    responsibilities=["Design APIs"],
    qualifications=["5+ years"],
    domain_expectations=["E-commerce"],
)

SAMPLE_RESUME = EnhancedResume(
    summary="Senior Backend Engineer with 4+ years building scalable APIs.",
    sections=[
        ResumeSection(
            id="sec_0",
            section_type="experience",
            title="Professional Experience",
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
                            original_text="Built RESTful APIs using Python and FastAPI",
                            enhanced_text="Designed and implemented RESTful APIs using Python and FastAPI, serving 10K+ requests/min",
                            source_entry_id="entry-1",
                            relevance_score=0.92,
                        ),
                        EnhancedBullet(
                            id="0_1",
                            original_text="Wrote unit tests",
                            enhanced_text="Developed comprehensive test suite achieving 95% code coverage",
                            source_entry_id="entry-1",
                            relevance_score=0.75,
                        ),
                    ],
                ),
            ],
        ),
    ],
    skills=["Python", "FastAPI", "PostgreSQL"],
)


SAMPLE_REPORT = ReviewReport(
    annotations=[
        ReviewAnnotation(
            bullet_id="0_0",
            perspective="recruiter",
            rating="strong",
            comment="Excellent keyword match with quantified impact.",
        ),
        ReviewAnnotation(
            bullet_id="0_0",
            perspective="hiring_manager",
            rating="strong",
            comment="Shows real engineering judgment with concrete scale numbers.",
        ),
        ReviewAnnotation(
            bullet_id="0_1",
            perspective="recruiter",
            rating="adequate",
            comment="Testing is relevant but 95% coverage claims need specifics.",
        ),
        ReviewAnnotation(
            bullet_id="0_1",
            perspective="hiring_manager",
            rating="adequate",
            comment="Good to show testing discipline, but lacks detail on test types.",
        ),
    ],
    recruiter_summary="Strong technical resume with good keyword alignment.",
    hiring_manager_summary="Solid engineering background with quantified results.",
    strong_count=2,
    adequate_count=2,
    weak_count=0,
)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestReviewerSchemas:
    """Test schema validation for reviewer models."""

    def test_review_annotation_valid(self) -> None:
        ann = ReviewAnnotation(
            bullet_id="0_0",
            perspective="recruiter",
            rating="strong",
            comment="Great bullet.",
        )
        assert ann.perspective == "recruiter"
        assert ann.rating == "strong"

    def test_review_annotation_invalid_perspective(self) -> None:
        with pytest.raises(Exception):
            ReviewAnnotation(
                bullet_id="0_0",
                perspective="invalid",  # type: ignore[arg-type]
                rating="strong",
                comment="Bad.",
            )

    def test_review_annotation_invalid_rating(self) -> None:
        with pytest.raises(Exception):
            ReviewAnnotation(
                bullet_id="0_0",
                perspective="recruiter",
                rating="excellent",  # type: ignore[arg-type]
                comment="Bad.",
            )

    def test_review_report_defaults(self) -> None:
        report = ReviewReport(
            recruiter_summary="Good.",
            hiring_manager_summary="Good.",
        )
        assert report.annotations == []
        assert report.strong_count == 0
        assert report.adequate_count == 0
        assert report.weak_count == 0

    def test_review_output_wraps_report(self) -> None:
        output = ReviewOutput(report=SAMPLE_REPORT)
        assert output.report.strong_count == 2
        assert len(output.report.annotations) == 4


# ---------------------------------------------------------------------------
# Agent tests
# ---------------------------------------------------------------------------


class TestReviewerAgent:
    """Test the ReviewerAgent class."""

    @pytest.mark.asyncio
    async def test_review_returns_report(self) -> None:
        """Agent.review() returns a ReviewReport."""
        mock_output = ReviewOutput(report=SAMPLE_REPORT)

        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_output)
        mock_llm.with_structured_output.return_value = mock_structured

        mock_config = MagicMock()
        mock_config.get_chat_model.return_value = mock_llm

        from src.agents.reviewer.agent import ReviewerAgent

        agent = ReviewerAgent(mock_config)
        report = await agent.review(SAMPLE_RESUME, SAMPLE_ANALYSIS)

        assert isinstance(report, ReviewReport)
        assert report.strong_count == 2
        assert len(report.annotations) == 4

    @pytest.mark.asyncio
    async def test_review_handles_dict_output(self) -> None:
        """Agent handles dict output from LLM."""
        mock_output = ReviewOutput(report=SAMPLE_REPORT).model_dump()

        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_output)
        mock_llm.with_structured_output.return_value = mock_structured

        mock_config = MagicMock()
        mock_config.get_chat_model.return_value = mock_llm

        from src.agents.reviewer.agent import ReviewerAgent

        agent = ReviewerAgent(mock_config)
        report = await agent.review(SAMPLE_RESUME, SAMPLE_ANALYSIS)

        assert isinstance(report, ReviewReport)
        assert report.strong_count == 2

    @pytest.mark.asyncio
    async def test_review_raises_on_no_report(self) -> None:
        """Agent raises RuntimeError if no report produced."""
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(
            return_value=ReviewOutput(report=SAMPLE_REPORT)
        )
        mock_llm.with_structured_output.return_value = mock_structured

        mock_config = MagicMock()
        mock_config.get_chat_model.return_value = mock_llm

        from src.agents.reviewer.agent import ReviewerAgent

        agent = ReviewerAgent(mock_config)
        agent._graph = AsyncMock(return_value={"report": None})
        agent._graph.ainvoke = AsyncMock(return_value={"report": None})

        with pytest.raises(RuntimeError, match="did not produce a report"):
            await agent.review(SAMPLE_RESUME, SAMPLE_ANALYSIS)


# ---------------------------------------------------------------------------
# Node / message builder tests
# ---------------------------------------------------------------------------


class TestReviewerNodeAndMessage:
    """Test the internal node and message building."""

    def test_build_user_message_contains_jd(self) -> None:
        """User message includes JD analysis fields."""
        from src.agents.reviewer.agent import ReviewerAgent

        agent = ReviewerAgent.__new__(ReviewerAgent)
        state = {
            "enhanced_resume": SAMPLE_RESUME.model_dump(),
            "jd_analysis": SAMPLE_ANALYSIS.model_dump(),
            "report": None,
        }
        msg = agent._build_user_message(state)

        assert "Senior Backend Engineer" in msg
        assert "Acme Corp" in msg
        assert "Python" in msg
        assert "FastAPI" in msg

    def test_build_user_message_contains_bullets(self) -> None:
        """User message includes all bullet IDs and enhanced text."""
        from src.agents.reviewer.agent import ReviewerAgent

        agent = ReviewerAgent.__new__(ReviewerAgent)
        state = {
            "enhanced_resume": SAMPLE_RESUME.model_dump(),
            "jd_analysis": SAMPLE_ANALYSIS.model_dump(),
            "report": None,
        }
        msg = agent._build_user_message(state)

        assert "[0_0]" in msg
        assert "[0_1]" in msg
        assert "10K+ requests/min" in msg
        assert "Total bullets: 2" in msg
        assert "Expected annotations: 4" in msg

    def test_build_user_message_contains_responsibilities(self) -> None:
        """User message includes JD responsibilities."""
        from src.agents.reviewer.agent import ReviewerAgent

        agent = ReviewerAgent.__new__(ReviewerAgent)
        state = {
            "enhanced_resume": SAMPLE_RESUME.model_dump(),
            "jd_analysis": SAMPLE_ANALYSIS.model_dump(),
            "report": None,
        }
        msg = agent._build_user_message(state)

        assert "Design APIs" in msg


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestReviewEndpoint:
    """Tests for the POST /sessions/{id}/review endpoint."""

    async def _create_session_with_resume(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> str:
        """Helper: create a session and generate a resume on it."""
        with patch("src.api.sessions.get_llm_config") as mock_config:
            mock_config.return_value = MagicMock()

            mock_analyst = MagicMock()
            mock_analyst.analyze = AsyncMock(return_value=SAMPLE_ANALYSIS)
            with patch("src.api.sessions.JobAnalystAgent", return_value=mock_analyst):
                resp = await client.post(
                    "/api/v1/sessions/start",
                    json={"text": "Engineer at Corp..."},
                    headers=auth_headers,
                )
                session_id = resp.json()["id"]

            await client.post(
                f"/api/v1/sessions/{session_id}/approve",
                json={"gate": "analysis", "selected_entry_ids": ["entry-1"]},
                headers=auth_headers,
            )

            with (
                patch("src.api.sessions.RetrievalService") as mock_ret_cls,
                patch("src.api.sessions.MatchScorer") as mock_sc_cls,
                patch("src.api.sessions.ResumeWriterAgent") as mock_wr_cls,
            ):
                from src.schemas.matching import GapAnalysis, MatchResult, RankedEntry, SkillMatch

                mock_ret = MagicMock()
                mock_ret.embed_job_description = AsyncMock()
                mock_ret.embed_all_entries = AsyncMock()
                mock_ret.find_relevant_entries = AsyncMock(return_value=[
                    RankedEntry(
                        entry_id="entry-1", entry_type="work_experience",
                        title="Backend Developer", organization="TechCo",
                        start_date="2020-01", end_date="2023-12",
                        bullet_points=["Built APIs"], tags=["Python"],
                        source="user_confirmed", similarity_score=0.9,
                    ),
                ])
                mock_ret_cls.return_value = mock_ret
                mock_sc = MagicMock()
                mock_sc.score.return_value = MatchResult(
                    overall_score=80.0, required_skills_score=80.0,
                    preferred_skills_score=40.0, tech_stack_score=75.0,
                    required_matches=[SkillMatch(skill="Python", matched=True, matched_by=["Python"])],
                    preferred_matches=[], tech_matches=[],
                    gap_analysis=GapAnalysis(unmatched_required=[], unmatched_preferred=[], missing_tech=[]),
                    recommended_section_order=["experience"],
                )
                mock_sc_cls.return_value = mock_sc
                mock_wr = MagicMock()
                mock_wr.write = AsyncMock(return_value=SAMPLE_RESUME)
                mock_wr_cls.return_value = mock_wr

                resp = await client.post(
                    f"/api/v1/sessions/{session_id}/generate",
                    json={},
                    headers=auth_headers,
                )
                assert resp.status_code == 200

        return session_id

    @patch("src.api.sessions.ReviewerAgent")
    @patch("src.api.sessions.get_llm_config")
    async def test_review_success(
        self,
        mock_get_config: MagicMock,
        mock_reviewer_cls: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /sessions/{id}/review returns a review report."""
        mock_get_config.return_value = MagicMock()
        session_id = await self._create_session_with_resume(client, auth_headers)

        mock_reviewer = MagicMock()
        mock_reviewer.review = AsyncMock(return_value=SAMPLE_REPORT)
        mock_reviewer_cls.return_value = mock_reviewer

        resp = await client.post(
            f"/api/v1/sessions/{session_id}/review",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "report" in data
        assert data["report"]["strong_count"] == 2
        assert data["report"]["adequate_count"] == 2
        assert len(data["report"]["annotations"]) == 4

    @patch("src.api.sessions.get_llm_config")
    async def test_review_no_resume(
        self,
        mock_get_config: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /sessions/{id}/review returns 400 when no resume."""
        mock_get_config.return_value = MagicMock()

        mock_analyst = MagicMock()
        mock_analyst.analyze = AsyncMock(return_value=SAMPLE_ANALYSIS)
        with patch("src.api.sessions.JobAnalystAgent", return_value=mock_analyst):
            resp = await client.post(
                "/api/v1/sessions/start",
                json={"text": "Engineer..."},
                headers=auth_headers,
            )
            session_id = resp.json()["id"]

        resp = await client.post(
            f"/api/v1/sessions/{session_id}/review",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    @patch("src.api.sessions.get_llm_config")
    async def test_review_session_not_found(
        self,
        mock_get_config: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /sessions/{id}/review returns 404 for unknown session."""
        import uuid

        mock_get_config.return_value = MagicMock()
        resp = await client.post(
            f"/api/v1/sessions/{uuid.uuid4()}/review",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @patch("src.api.sessions.ReviewerAgent")
    @patch("src.api.sessions.get_llm_config")
    async def test_review_agent_failure(
        self,
        mock_get_config: MagicMock,
        mock_reviewer_cls: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /sessions/{id}/review returns 422 when agent fails."""
        mock_get_config.return_value = MagicMock()
        session_id = await self._create_session_with_resume(client, auth_headers)

        mock_reviewer = MagicMock()
        mock_reviewer.review = AsyncMock(side_effect=RuntimeError("LLM error"))
        mock_reviewer_cls.return_value = mock_reviewer

        resp = await client.post(
            f"/api/v1/sessions/{session_id}/review",
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert "Failed to review" in resp.json()["detail"]
