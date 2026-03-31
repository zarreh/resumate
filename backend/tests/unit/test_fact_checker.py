"""Tests for the Fact Checker agent and fact-check endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from src.agents.fact_checker.schemas import (
    ClaimVerification,
    FactCheckOutput,
    FactCheckReport,
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
                            relevance_score=0.95,
                        ),
                        EnhancedBullet(
                            id="0_1",
                            original_text="Managed PostgreSQL databases",
                            enhanced_text="Managed PostgreSQL databases",
                            source_entry_id="entry-1",
                            relevance_score=0.90,
                        ),
                    ],
                )
            ],
        ),
    ],
    skills=["Python", "FastAPI", "PostgreSQL"],
    metadata={"total_bullets": 2},
)

SAMPLE_CAREER_ENTRIES = [
    {
        "id": "entry-1",
        "entry_type": "work_experience",
        "title": "Backend Developer",
        "organization": "TechCo",
        "start_date": "2020-01-01",
        "end_date": "2023-12-31",
        "bullet_points": [
            "Built RESTful APIs using Python and FastAPI",
            "Managed PostgreSQL databases",
        ],
        "tags": ["Python", "FastAPI", "PostgreSQL"],
        "source": "user_confirmed",
    },
]

SAMPLE_REPORT = FactCheckReport(
    verifications=[
        ClaimVerification(
            claim_text="Designed and implemented RESTful APIs using Python and FastAPI, serving 10K+ requests/min",
            bullet_id="0_0",
            status="modified",
            source_entry_id="entry-1",
            source_text="Built RESTful APIs using Python and FastAPI",
            notes="Added '10K+ requests/min' metric not in original",
        ),
        ClaimVerification(
            claim_text="Managed PostgreSQL databases",
            bullet_id="0_1",
            status="verified",
            source_entry_id="entry-1",
            source_text="Managed PostgreSQL databases",
        ),
        ClaimVerification(
            claim_text="Senior Backend Engineer with 4+ years building scalable APIs.",
            bullet_id="summary",
            status="verified",
            source_entry_id=None,
            source_text=None,
            notes="Experience dates span 2020-2023 (approx 4 years)",
        ),
    ],
    summary="Resume is mostly accurate. One bullet adds an unverified metric.",
    verified_count=2,
    unverified_count=0,
    modified_count=1,
)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestFactCheckSchemas:
    """Tests for fact-check Pydantic schemas."""

    def test_claim_verification_verified(self) -> None:
        claim = ClaimVerification(
            claim_text="Built APIs",
            bullet_id="0_0",
            status="verified",
            source_entry_id="entry-1",
            source_text="Built REST APIs",
        )
        assert claim.status == "verified"
        assert claim.notes is None

    def test_claim_verification_modified(self) -> None:
        claim = ClaimVerification(
            claim_text="Built APIs serving 10K req/s",
            bullet_id="0_0",
            status="modified",
            source_entry_id="entry-1",
            source_text="Built APIs",
            notes="Added metric",
        )
        assert claim.status == "modified"
        assert claim.notes == "Added metric"

    def test_claim_verification_unverified(self) -> None:
        claim = ClaimVerification(
            claim_text="Led a team of 20 engineers",
            bullet_id="1_0",
            status="unverified",
            notes="No evidence of leadership role",
        )
        assert claim.status == "unverified"
        assert claim.source_entry_id is None

    def test_fact_check_report_roundtrip(self) -> None:
        data = SAMPLE_REPORT.model_dump()
        restored = FactCheckReport.model_validate(data)
        assert restored.verified_count == 2
        assert restored.modified_count == 1
        assert restored.unverified_count == 0
        assert len(restored.verifications) == 3

    def test_fact_check_output_wrapper(self) -> None:
        output = FactCheckOutput(report=SAMPLE_REPORT)
        assert output.report.verified_count == 2


# ---------------------------------------------------------------------------
# Agent unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestFactCheckerAgent:
    """Tests for the FactCheckerAgent class."""

    @patch("src.agents.fact_checker.agent.StateGraph")
    async def test_check_success(self, mock_state_graph_cls: MagicMock) -> None:
        """Agent returns a FactCheckReport on success."""
        from src.agents.fact_checker.agent import FactCheckerAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        mock_graph_instance = MagicMock()
        mock_compiled = AsyncMock()
        mock_compiled.ainvoke.return_value = {
            "report": SAMPLE_REPORT.model_dump()
        }
        mock_graph_instance.compile.return_value = mock_compiled
        mock_state_graph_cls.return_value = mock_graph_instance

        agent = FactCheckerAgent(mock_llm_config)
        result = await agent.check(SAMPLE_RESUME, SAMPLE_CAREER_ENTRIES)

        assert isinstance(result, FactCheckReport)
        assert result.verified_count == 2
        assert result.modified_count == 1
        assert len(result.verifications) == 3

    @patch("src.agents.fact_checker.agent.StateGraph")
    async def test_check_no_report_error(self, mock_state_graph_cls: MagicMock) -> None:
        """Agent raises RuntimeError when no report is produced."""
        from src.agents.fact_checker.agent import FactCheckerAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        mock_graph_instance = MagicMock()
        mock_compiled = AsyncMock()
        mock_compiled.ainvoke.return_value = {"report": None}
        mock_graph_instance.compile.return_value = mock_compiled
        mock_state_graph_cls.return_value = mock_graph_instance

        agent = FactCheckerAgent(mock_llm_config)
        with pytest.raises(RuntimeError, match="did not produce a report"):
            await agent.check(SAMPLE_RESUME, SAMPLE_CAREER_ENTRIES)

    @patch("src.agents.fact_checker.agent.StateGraph")
    async def test_check_llm_error(self, mock_state_graph_cls: MagicMock) -> None:
        """Agent propagates LLM errors."""
        from src.agents.fact_checker.agent import FactCheckerAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        mock_graph_instance = MagicMock()
        mock_compiled = AsyncMock()
        mock_compiled.ainvoke.side_effect = RuntimeError("LLM timeout")
        mock_graph_instance.compile.return_value = mock_compiled
        mock_state_graph_cls.return_value = mock_graph_instance

        agent = FactCheckerAgent(mock_llm_config)
        with pytest.raises(RuntimeError, match="LLM timeout"):
            await agent.check(SAMPLE_RESUME, SAMPLE_CAREER_ENTRIES)


# ---------------------------------------------------------------------------
# Node unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestFactCheckNode:
    """Tests for the _fact_check_node method."""

    async def test_node_pydantic_output(self) -> None:
        """Node handles Pydantic model output from LLM."""
        from src.agents.fact_checker.agent import FactCheckerAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        agent = FactCheckerAgent.__new__(FactCheckerAgent)
        agent._model = mock_model

        mock_structured = AsyncMock()
        mock_structured.ainvoke.return_value = FactCheckOutput(report=SAMPLE_REPORT)
        mock_model.with_structured_output.return_value = mock_structured

        state = {
            "enhanced_resume": SAMPLE_RESUME.model_dump(),
            "career_entries": SAMPLE_CAREER_ENTRIES,
            "report": None,
        }

        result = await agent._fact_check_node(state)
        assert result["report"] is not None
        report = FactCheckReport.model_validate(result["report"])
        assert report.verified_count == 2

    async def test_node_dict_output(self) -> None:
        """Node handles dict output from LLM."""
        from src.agents.fact_checker.agent import FactCheckerAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        agent = FactCheckerAgent.__new__(FactCheckerAgent)
        agent._model = mock_model

        mock_structured = AsyncMock()
        mock_structured.ainvoke.return_value = {
            "report": SAMPLE_REPORT.model_dump()
        }
        mock_model.with_structured_output.return_value = mock_structured

        state = {
            "enhanced_resume": SAMPLE_RESUME.model_dump(),
            "career_entries": SAMPLE_CAREER_ENTRIES,
            "report": None,
        }

        result = await agent._fact_check_node(state)
        assert result["report"] is not None

    async def test_node_unexpected_type_error(self) -> None:
        """Node raises TypeError for unexpected LLM output."""
        from src.agents.fact_checker.agent import FactCheckerAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        agent = FactCheckerAgent.__new__(FactCheckerAgent)
        agent._model = mock_model

        mock_structured = AsyncMock()
        mock_structured.ainvoke.return_value = "unexpected string"
        mock_model.with_structured_output.return_value = mock_structured

        state = {
            "enhanced_resume": SAMPLE_RESUME.model_dump(),
            "career_entries": SAMPLE_CAREER_ENTRIES,
            "report": None,
        }

        with pytest.raises(TypeError, match="Unexpected LLM output type"):
            await agent._fact_check_node(state)


# ---------------------------------------------------------------------------
# Message builder tests
# ---------------------------------------------------------------------------


class TestFactCheckMessageBuilder:
    """Tests for the _build_user_message helper."""

    def test_message_includes_resume_bullets(self) -> None:
        from src.agents.fact_checker.agent import FactCheckerAgent

        agent = FactCheckerAgent.__new__(FactCheckerAgent)
        state = {
            "enhanced_resume": SAMPLE_RESUME.model_dump(),
            "career_entries": SAMPLE_CAREER_ENTRIES,
            "report": None,
        }
        msg = agent._build_user_message(state)
        assert "10K+ requests/min" in msg
        assert "0_0" in msg
        assert "0_1" in msg

    def test_message_includes_career_entries(self) -> None:
        from src.agents.fact_checker.agent import FactCheckerAgent

        agent = FactCheckerAgent.__new__(FactCheckerAgent)
        state = {
            "enhanced_resume": SAMPLE_RESUME.model_dump(),
            "career_entries": SAMPLE_CAREER_ENTRIES,
            "report": None,
        }
        msg = agent._build_user_message(state)
        assert "Career History Entries" in msg
        assert "Backend Developer" in msg
        assert "TechCo" in msg

    def test_message_includes_original_and_enhanced(self) -> None:
        from src.agents.fact_checker.agent import FactCheckerAgent

        agent = FactCheckerAgent.__new__(FactCheckerAgent)
        state = {
            "enhanced_resume": SAMPLE_RESUME.model_dump(),
            "career_entries": SAMPLE_CAREER_ENTRIES,
            "report": None,
        }
        msg = agent._build_user_message(state)
        assert "Original:" in msg
        assert "Enhanced:" in msg


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestFactCheckEndpoint:
    """Tests for the POST /sessions/{id}/fact-check endpoint."""

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

    @patch("src.api.sessions.FactCheckerAgent")
    @patch("src.api.sessions.get_llm_config")
    async def test_fact_check_success(
        self,
        mock_get_config: MagicMock,
        mock_checker_cls: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /sessions/{id}/fact-check returns a fact-check report."""
        mock_get_config.return_value = MagicMock()
        session_id = await self._create_session_with_resume(client, auth_headers)

        mock_checker = MagicMock()
        mock_checker.check = AsyncMock(return_value=SAMPLE_REPORT)
        mock_checker_cls.return_value = mock_checker

        resp = await client.post(
            f"/api/v1/sessions/{session_id}/fact-check",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "report" in data
        assert data["report"]["verified_count"] == 2
        assert data["report"]["modified_count"] == 1
        assert len(data["report"]["verifications"]) == 3

    @patch("src.api.sessions.get_llm_config")
    async def test_fact_check_no_resume(
        self,
        mock_get_config: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /sessions/{id}/fact-check returns 400 when no resume."""
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
            f"/api/v1/sessions/{session_id}/fact-check",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    @patch("src.api.sessions.get_llm_config")
    async def test_fact_check_session_not_found(
        self,
        mock_get_config: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /sessions/{id}/fact-check returns 404 for unknown session."""
        import uuid

        mock_get_config.return_value = MagicMock()
        resp = await client.post(
            f"/api/v1/sessions/{uuid.uuid4()}/fact-check",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @patch("src.api.sessions.FactCheckerAgent")
    @patch("src.api.sessions.get_llm_config")
    async def test_fact_check_agent_failure(
        self,
        mock_get_config: MagicMock,
        mock_checker_cls: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /sessions/{id}/fact-check returns 422 when agent fails."""
        mock_get_config.return_value = MagicMock()
        session_id = await self._create_session_with_resume(client, auth_headers)

        mock_checker = MagicMock()
        mock_checker.check = AsyncMock(side_effect=RuntimeError("LLM error"))
        mock_checker_cls.return_value = mock_checker

        resp = await client.post(
            f"/api/v1/sessions/{session_id}/fact-check",
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert "Failed to fact-check" in resp.json()["detail"]
