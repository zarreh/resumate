"""Tests for the Cover Letter agent and endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from src.agents.cover_letter.schemas import CoverLetterContent, CoverLetterOutput
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
    responsibilities=["Design APIs", "Lead backend team"],
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
                            original_text="Built APIs",
                            enhanced_text="Designed and implemented RESTful APIs using Python and FastAPI, serving 10K+ requests/min",
                            source_entry_id="entry-1",
                            relevance_score=0.92,
                        ),
                    ],
                ),
            ],
        ),
    ],
    skills=["Python", "FastAPI", "PostgreSQL"],
)

SAMPLE_COVER_LETTER = "As an experienced backend engineer with deep Python expertise..."


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestCoverLetterSchemas:
    """Test schema validation."""

    def test_cover_letter_content(self) -> None:
        content = CoverLetterContent(body="Dear hiring manager...")
        assert content.body == "Dear hiring manager..."

    def test_cover_letter_output(self) -> None:
        output = CoverLetterOutput(
            cover_letter=CoverLetterContent(body="Lorem ipsum...")
        )
        assert output.cover_letter.body == "Lorem ipsum..."


# ---------------------------------------------------------------------------
# Agent tests
# ---------------------------------------------------------------------------


class TestCoverLetterAgent:
    """Test the CoverLetterAgent class."""

    @pytest.mark.asyncio
    async def test_generate_returns_string(self) -> None:
        mock_output = CoverLetterOutput(
            cover_letter=CoverLetterContent(body=SAMPLE_COVER_LETTER)
        )

        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_output)
        mock_llm.with_structured_output.return_value = mock_structured

        mock_config = MagicMock()
        mock_config.get_chat_model.return_value = mock_llm

        from src.agents.cover_letter.agent import CoverLetterAgent

        agent = CoverLetterAgent(mock_config)
        result = await agent.generate(SAMPLE_RESUME, SAMPLE_ANALYSIS)

        assert isinstance(result, str)
        assert "backend engineer" in result.lower()

    @pytest.mark.asyncio
    async def test_generate_handles_dict_output(self) -> None:
        mock_output = CoverLetterOutput(
            cover_letter=CoverLetterContent(body=SAMPLE_COVER_LETTER)
        ).model_dump()

        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_output)
        mock_llm.with_structured_output.return_value = mock_structured

        mock_config = MagicMock()
        mock_config.get_chat_model.return_value = mock_llm

        from src.agents.cover_letter.agent import CoverLetterAgent

        agent = CoverLetterAgent(mock_config)
        result = await agent.generate(SAMPLE_RESUME, SAMPLE_ANALYSIS)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_generate_raises_on_no_content(self) -> None:
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(
            return_value=CoverLetterOutput(
                cover_letter=CoverLetterContent(body=SAMPLE_COVER_LETTER)
            )
        )
        mock_llm.with_structured_output.return_value = mock_structured

        mock_config = MagicMock()
        mock_config.get_chat_model.return_value = mock_llm

        from src.agents.cover_letter.agent import CoverLetterAgent

        agent = CoverLetterAgent(mock_config)
        agent._graph = AsyncMock()
        agent._graph.ainvoke = AsyncMock(return_value={"cover_letter": None})

        with pytest.raises(RuntimeError, match="did not produce content"):
            await agent.generate(SAMPLE_RESUME, SAMPLE_ANALYSIS)


# ---------------------------------------------------------------------------
# Message builder tests
# ---------------------------------------------------------------------------


class TestCoverLetterMessageBuilder:
    """Test the internal message building."""

    def test_message_contains_jd_info(self) -> None:
        from src.agents.cover_letter.agent import CoverLetterAgent

        agent = CoverLetterAgent.__new__(CoverLetterAgent)
        state = {
            "enhanced_resume": SAMPLE_RESUME.model_dump(),
            "jd_analysis": SAMPLE_ANALYSIS.model_dump(),
            "cover_letter": None,
        }
        msg = agent._build_user_message(state)

        assert "Senior Backend Engineer" in msg
        assert "Acme Corp" in msg
        assert "Design APIs" in msg

    def test_message_contains_resume_info(self) -> None:
        from src.agents.cover_letter.agent import CoverLetterAgent

        agent = CoverLetterAgent.__new__(CoverLetterAgent)
        state = {
            "enhanced_resume": SAMPLE_RESUME.model_dump(),
            "jd_analysis": SAMPLE_ANALYSIS.model_dump(),
            "cover_letter": None,
        }
        msg = agent._build_user_message(state)

        assert "Python" in msg
        assert "10K+ requests/min" in msg
        assert "Top Achievements" in msg


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCoverLetterEndpoint:
    """Tests for the cover letter endpoints."""

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

    @patch("src.api.sessions.get_llm_config")
    async def test_generate_cover_letter_success(
        self,
        mock_get_config: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /sessions/{id}/cover-letter generates and stores a cover letter."""
        mock_get_config.return_value = MagicMock()
        session_id = await self._create_session_with_resume(client, auth_headers)

        mock_agent = MagicMock()
        mock_agent.generate = AsyncMock(return_value=SAMPLE_COVER_LETTER)

        with patch("src.agents.cover_letter.CoverLetterAgent", return_value=mock_agent):
            resp = await client.post(
                f"/api/v1/sessions/{session_id}/cover-letter",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "content" in data
        assert "backend engineer" in data["content"].lower()

    @patch("src.api.sessions.get_llm_config")
    async def test_get_cover_letter(
        self,
        mock_get_config: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /sessions/{id}/cover-letter retrieves the latest."""
        mock_get_config.return_value = MagicMock()
        session_id = await self._create_session_with_resume(client, auth_headers)

        # Generate one first
        with patch("src.agents.cover_letter.CoverLetterAgent") as mock_cls:
            mock_agent = MagicMock()
            mock_agent.generate = AsyncMock(return_value=SAMPLE_COVER_LETTER)
            mock_cls.return_value = mock_agent

            await client.post(
                f"/api/v1/sessions/{session_id}/cover-letter",
                headers=auth_headers,
            )

        resp = await client.get(
            f"/api/v1/sessions/{session_id}/cover-letter",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == SAMPLE_COVER_LETTER

    async def test_get_cover_letter_none(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /sessions/{id}/cover-letter returns null when none exists."""
        with patch("src.api.sessions.get_llm_config") as mock_config:
            mock_config.return_value = MagicMock()
            session_id = await self._create_session_with_resume(client, auth_headers)

        resp = await client.get(
            f"/api/v1/sessions/{session_id}/cover-letter",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() is None
