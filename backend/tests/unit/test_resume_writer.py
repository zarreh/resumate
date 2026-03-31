"""Tests for the Resume Writer agent and resume generation endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from src.schemas.job import JDAnalysis
from src.schemas.matching import GapAnalysis, MatchResult, RankedEntry, SkillMatch
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
    required_skills=["Python", "FastAPI", "PostgreSQL"],
    preferred_skills=["GraphQL", "AWS"],
    ats_keywords=["Backend Engineer", "Python", "microservices"],
    tech_stack=["Python", "FastAPI", "PostgreSQL", "Docker"],
    responsibilities=["Design and implement RESTful APIs"],
    qualifications=["5+ years experience"],
    domain_expectations=["E-commerce"],
)

SAMPLE_ENTRIES = [
    RankedEntry(
        entry_id="entry-1",
        entry_type="work_experience",
        title="Backend Developer",
        organization="TechCo",
        start_date="2020-01",
        end_date="2023-12",
        bullet_points=[
            "Built RESTful APIs using Python and FastAPI",
            "Managed PostgreSQL databases with complex queries",
        ],
        tags=["Python", "FastAPI", "PostgreSQL"],
        source="user_confirmed",
        similarity_score=0.92,
    ),
    RankedEntry(
        entry_id="entry-2",
        entry_type="project",
        title="Microservice Migration",
        organization="TechCo",
        start_date="2022-06",
        end_date="2023-06",
        bullet_points=[
            "Led migration from monolith to microservices architecture",
            "Implemented Docker-based CI/CD pipeline",
        ],
        tags=["Docker", "microservices", "CI/CD"],
        source="user_confirmed",
        similarity_score=0.85,
    ),
]

SAMPLE_MATCH = MatchResult(
    overall_score=78.0,
    required_skills_score=80.0,
    preferred_skills_score=40.0,
    tech_stack_score=75.0,
    required_matches=[
        SkillMatch(skill="Python", matched=True, matched_by=["Python"]),
        SkillMatch(skill="FastAPI", matched=True, matched_by=["FastAPI"]),
        SkillMatch(skill="PostgreSQL", matched=True, matched_by=["PostgreSQL"]),
    ],
    preferred_matches=[
        SkillMatch(skill="GraphQL", matched=False, matched_by=[]),
        SkillMatch(skill="AWS", matched=False, matched_by=[]),
    ],
    tech_matches=[
        SkillMatch(skill="Python", matched=True, matched_by=["Python"]),
        SkillMatch(skill="Docker", matched=True, matched_by=["Docker"]),
    ],
    gap_analysis=GapAnalysis(
        unmatched_required=[],
        unmatched_preferred=["GraphQL", "AWS"],
        missing_tech=[],
    ),
    recommended_section_order=["experience", "skills", "projects", "education"],
)

SAMPLE_RESUME = EnhancedResume(
    summary="Senior Backend Engineer with 4+ years building scalable APIs and microservices using Python and FastAPI.",
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
                            enhanced_text="Designed and implemented RESTful APIs using Python and FastAPI, serving 10K+ requests/min for marketplace platform",
                            source_entry_id="entry-1",
                            relevance_score=0.95,
                        ),
                        EnhancedBullet(
                            id="0_1",
                            original_text="Managed PostgreSQL databases with complex queries",
                            enhanced_text="Optimized PostgreSQL database performance with advanced query patterns, reducing average response time by 40%",
                            source_entry_id="entry-1",
                            relevance_score=0.90,
                        ),
                    ],
                )
            ],
        ),
        ResumeSection(
            id="sec_1",
            section_type="projects",
            title="Projects",
            entries=[
                ResumeSectionEntry(
                    entry_id="entry-2",
                    title="Microservice Migration",
                    organization="TechCo",
                    start_date="2022-06",
                    end_date="2023-06",
                    bullets=[
                        EnhancedBullet(
                            id="1_0",
                            original_text="Led migration from monolith to microservices architecture",
                            enhanced_text="Spearheaded migration from monolithic architecture to containerized microservices, improving deployment frequency by 5x",
                            source_entry_id="entry-2",
                            relevance_score=0.88,
                        ),
                    ],
                )
            ],
        ),
    ],
    skills=["Python", "FastAPI", "PostgreSQL", "Docker", "microservices", "CI/CD"],
    metadata={
        "section_order": ["experience", "projects", "skills"],
        "total_bullets": 3,
    },
)


# ---------------------------------------------------------------------------
# Agent unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestResumeWriterAgent:
    """Tests for the ResumeWriterAgent class."""

    @patch("src.agents.resume_writer.agent.StateGraph")
    async def test_write_success(self, mock_state_graph_cls: MagicMock) -> None:
        """Agent returns an EnhancedResume on success."""
        from src.agents.resume_writer.agent import ResumeWriterAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        # Mock the compiled graph's ainvoke to return resume data
        mock_graph_instance = MagicMock()
        mock_compiled = AsyncMock()
        mock_compiled.ainvoke.return_value = {
            "resume": SAMPLE_RESUME.model_dump()
        }
        mock_graph_instance.compile.return_value = mock_compiled
        mock_state_graph_cls.return_value = mock_graph_instance

        agent = ResumeWriterAgent(mock_llm_config)
        result = await agent.write(
            jd_analysis=SAMPLE_ANALYSIS,
            ranked_entries=SAMPLE_ENTRIES,
            match_result=SAMPLE_MATCH,
        )

        assert isinstance(result, EnhancedResume)
        assert result.summary == SAMPLE_RESUME.summary
        assert len(result.sections) == 2
        assert len(result.skills) == 6

    @patch("src.agents.resume_writer.agent.StateGraph")
    async def test_write_with_calibration_mode(
        self, mock_state_graph_cls: MagicMock
    ) -> None:
        """Agent passes style feedback in calibration mode."""
        from src.agents.resume_writer.agent import ResumeWriterAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        mock_graph_instance = MagicMock()
        mock_compiled = AsyncMock()
        mock_compiled.ainvoke.return_value = {
            "resume": SAMPLE_RESUME.model_dump()
        }
        mock_graph_instance.compile.return_value = mock_compiled
        mock_state_graph_cls.return_value = mock_graph_instance

        agent = ResumeWriterAgent(mock_llm_config)
        result = await agent.write(
            jd_analysis=SAMPLE_ANALYSIS,
            ranked_entries=SAMPLE_ENTRIES,
            match_result=SAMPLE_MATCH,
            style_feedback="Keep bullets shorter and more technical",
            mode="calibration",
        )

        assert isinstance(result, EnhancedResume)
        # Verify the state passed to ainvoke includes calibration
        call_args = mock_compiled.ainvoke.call_args[0][0]
        assert call_args["mode"] == "calibration"
        assert call_args["style_feedback"] == "Keep bullets shorter and more technical"

    @patch("src.agents.resume_writer.agent.StateGraph")
    async def test_write_no_resume_error(
        self, mock_state_graph_cls: MagicMock
    ) -> None:
        """Agent raises RuntimeError when no resume is produced."""
        from src.agents.resume_writer.agent import ResumeWriterAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        mock_graph_instance = MagicMock()
        mock_compiled = AsyncMock()
        mock_compiled.ainvoke.return_value = {"resume": None}
        mock_graph_instance.compile.return_value = mock_compiled
        mock_state_graph_cls.return_value = mock_graph_instance

        agent = ResumeWriterAgent(mock_llm_config)
        with pytest.raises(RuntimeError, match="did not produce a resume"):
            await agent.write(
                jd_analysis=SAMPLE_ANALYSIS,
                ranked_entries=SAMPLE_ENTRIES,
                match_result=SAMPLE_MATCH,
            )

    @patch("src.agents.resume_writer.agent.StateGraph")
    async def test_write_llm_error(
        self, mock_state_graph_cls: MagicMock
    ) -> None:
        """Agent propagates LLM errors."""
        from src.agents.resume_writer.agent import ResumeWriterAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        mock_graph_instance = MagicMock()
        mock_compiled = AsyncMock()
        mock_compiled.ainvoke.side_effect = RuntimeError("LLM timeout")
        mock_graph_instance.compile.return_value = mock_compiled
        mock_state_graph_cls.return_value = mock_graph_instance

        agent = ResumeWriterAgent(mock_llm_config)
        with pytest.raises(RuntimeError, match="LLM timeout"):
            await agent.write(
                jd_analysis=SAMPLE_ANALYSIS,
                ranked_entries=SAMPLE_ENTRIES,
                match_result=SAMPLE_MATCH,
            )


# ---------------------------------------------------------------------------
# Write node unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestWriteResumeNode:
    """Tests for the _write_resume_node method."""

    async def test_node_pydantic_output(self) -> None:
        """Node handles Pydantic model output from LLM."""
        from src.agents.resume_writer.agent import ResumeWriterAgent
        from src.agents.resume_writer.schemas import ResumeWriterOutput

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        agent = ResumeWriterAgent.__new__(ResumeWriterAgent)
        agent._model = mock_model

        mock_structured = AsyncMock()
        mock_structured.ainvoke.return_value = ResumeWriterOutput(
            resume=SAMPLE_RESUME
        )
        mock_model.with_structured_output.return_value = mock_structured

        state = {
            "jd_analysis": SAMPLE_ANALYSIS.model_dump(),
            "ranked_entries": [e.model_dump() for e in SAMPLE_ENTRIES],
            "match_result": SAMPLE_MATCH.model_dump(),
            "context_text": "",
            "style_feedback": "",
            "mode": "full",
            "resume": None,
        }

        result = await agent._write_resume_node(state)
        assert result["resume"] is not None
        resume = EnhancedResume.model_validate(result["resume"])
        assert resume.summary == SAMPLE_RESUME.summary

    async def test_node_dict_output(self) -> None:
        """Node handles dict output from LLM."""
        from src.agents.resume_writer.agent import ResumeWriterAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        agent = ResumeWriterAgent.__new__(ResumeWriterAgent)
        agent._model = mock_model

        mock_structured = AsyncMock()
        mock_structured.ainvoke.return_value = {
            "resume": SAMPLE_RESUME.model_dump()
        }
        mock_model.with_structured_output.return_value = mock_structured

        state = {
            "jd_analysis": SAMPLE_ANALYSIS.model_dump(),
            "ranked_entries": [e.model_dump() for e in SAMPLE_ENTRIES],
            "match_result": SAMPLE_MATCH.model_dump(),
            "context_text": "",
            "style_feedback": "",
            "mode": "full",
            "resume": None,
        }

        result = await agent._write_resume_node(state)
        assert result["resume"] is not None

    async def test_node_unexpected_type_error(self) -> None:
        """Node raises TypeError for unexpected LLM output."""
        from src.agents.resume_writer.agent import ResumeWriterAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        agent = ResumeWriterAgent.__new__(ResumeWriterAgent)
        agent._model = mock_model

        mock_structured = AsyncMock()
        mock_structured.ainvoke.return_value = "unexpected string"
        mock_model.with_structured_output.return_value = mock_structured

        state = {
            "jd_analysis": SAMPLE_ANALYSIS.model_dump(),
            "ranked_entries": [e.model_dump() for e in SAMPLE_ENTRIES],
            "match_result": SAMPLE_MATCH.model_dump(),
            "context_text": "",
            "style_feedback": "",
            "mode": "full",
            "resume": None,
        }

        with pytest.raises(TypeError, match="Unexpected LLM output type"):
            await agent._write_resume_node(state)

    async def test_node_calibration_mode_prompt(self) -> None:
        """Node includes calibration prompt when mode is calibration."""
        from src.agents.resume_writer.agent import ResumeWriterAgent
        from src.agents.resume_writer.schemas import ResumeWriterOutput

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        agent = ResumeWriterAgent.__new__(ResumeWriterAgent)
        agent._model = mock_model

        mock_structured = AsyncMock()
        mock_structured.ainvoke.return_value = ResumeWriterOutput(
            resume=SAMPLE_RESUME
        )
        mock_model.with_structured_output.return_value = mock_structured

        state = {
            "jd_analysis": SAMPLE_ANALYSIS.model_dump(),
            "ranked_entries": [e.model_dump() for e in SAMPLE_ENTRIES],
            "match_result": SAMPLE_MATCH.model_dump(),
            "context_text": "",
            "style_feedback": "Make bullets punchier",
            "mode": "calibration",
            "resume": None,
        }

        await agent._write_resume_node(state)

        # Verify the system prompt contains the calibration section
        call_args = mock_structured.ainvoke.call_args[0][0]
        system_msg = call_args[0]
        assert "Make bullets punchier" in system_msg.content
        assert "calibrating" in system_msg.content.lower()


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestResumeSchemas:
    """Tests for resume-related Pydantic schemas."""

    def test_enhanced_bullet_serialization(self) -> None:
        bullet = EnhancedBullet(
            id="0_0",
            original_text="Original text",
            enhanced_text="Enhanced text",
            source_entry_id="entry-1",
            relevance_score=0.85,
        )
        data = bullet.model_dump()
        assert data["id"] == "0_0"
        assert data["relevance_score"] == 0.85

    def test_enhanced_bullet_score_validation(self) -> None:
        with pytest.raises(Exception):
            EnhancedBullet(
                id="0_0",
                original_text="text",
                enhanced_text="text",
                source_entry_id="entry-1",
                relevance_score=1.5,  # > 1.0
            )

    def test_enhanced_resume_full_roundtrip(self) -> None:
        data = SAMPLE_RESUME.model_dump()
        restored = EnhancedResume.model_validate(data)
        assert restored.summary == SAMPLE_RESUME.summary
        assert len(restored.sections) == len(SAMPLE_RESUME.sections)
        assert restored.skills == SAMPLE_RESUME.skills

    def test_resume_section_entry(self) -> None:
        entry = ResumeSectionEntry(
            entry_id="entry-1",
            title="Developer",
            organization="Company",
            bullets=[],
        )
        assert entry.start_date is None
        assert entry.end_date is None

    def test_resume_metadata(self) -> None:
        resume = EnhancedResume(
            summary="Test",
            sections=[],
            skills=[],
            metadata={"total_bullets": 0, "section_order": []},
        )
        assert resume.metadata["total_bullets"] == 0


# ---------------------------------------------------------------------------
# User message builder tests
# ---------------------------------------------------------------------------


class TestUserMessageBuilder:
    """Tests for the _build_user_message helper."""

    def test_message_includes_jd_info(self) -> None:
        from src.agents.resume_writer.agent import ResumeWriterAgent

        agent = ResumeWriterAgent.__new__(ResumeWriterAgent)
        state = {
            "jd_analysis": SAMPLE_ANALYSIS.model_dump(),
            "ranked_entries": [e.model_dump() for e in SAMPLE_ENTRIES],
            "match_result": SAMPLE_MATCH.model_dump(),
            "context_text": "",
            "style_feedback": "",
            "mode": "full",
            "resume": None,
        }
        msg = agent._build_user_message(state)
        assert "Senior Backend Engineer" in msg
        assert "Acme Corp" in msg
        assert "Python" in msg

    def test_message_includes_entries(self) -> None:
        from src.agents.resume_writer.agent import ResumeWriterAgent

        agent = ResumeWriterAgent.__new__(ResumeWriterAgent)
        state = {
            "jd_analysis": SAMPLE_ANALYSIS.model_dump(),
            "ranked_entries": [e.model_dump() for e in SAMPLE_ENTRIES],
            "match_result": SAMPLE_MATCH.model_dump(),
            "context_text": "",
            "style_feedback": "",
            "mode": "full",
            "resume": None,
        }
        msg = agent._build_user_message(state)
        assert "Backend Developer" in msg
        assert "Microservice Migration" in msg
        assert "entry-1" in msg

    def test_message_includes_gap_analysis(self) -> None:
        from src.agents.resume_writer.agent import ResumeWriterAgent

        agent = ResumeWriterAgent.__new__(ResumeWriterAgent)
        state = {
            "jd_analysis": SAMPLE_ANALYSIS.model_dump(),
            "ranked_entries": [e.model_dump() for e in SAMPLE_ENTRIES],
            "match_result": SAMPLE_MATCH.model_dump(),
            "context_text": "",
            "style_feedback": "",
            "mode": "full",
            "resume": None,
        }
        msg = agent._build_user_message(state)
        assert "78/100" in msg

    def test_message_includes_context(self) -> None:
        from src.agents.resume_writer.agent import ResumeWriterAgent

        agent = ResumeWriterAgent.__new__(ResumeWriterAgent)
        state = {
            "jd_analysis": SAMPLE_ANALYSIS.model_dump(),
            "ranked_entries": [e.model_dump() for e in SAMPLE_ENTRIES],
            "match_result": SAMPLE_MATCH.model_dump(),
            "context_text": "I also have 2 years of Go experience",
            "style_feedback": "",
            "mode": "full",
            "resume": None,
        }
        msg = agent._build_user_message(state)
        assert "I also have 2 years of Go experience" in msg


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGenerateEndpoint:
    """Tests for the POST /sessions/{id}/generate endpoint."""

    @patch("src.api.sessions.RetrievalService")
    @patch("src.api.sessions.MatchScorer")
    @patch("src.api.sessions.ResumeWriterAgent")
    @patch("src.api.sessions.get_llm_config")
    async def test_generate_success(
        self,
        mock_get_config: MagicMock,
        mock_writer_cls: MagicMock,
        mock_scorer_cls: MagicMock,
        mock_retrieval_cls: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /sessions/{id}/generate returns enhanced resume."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        # 1. Create a session via start
        mock_analyst = MagicMock()
        mock_analyst.analyze = AsyncMock(return_value=SAMPLE_ANALYSIS)
        with patch("src.api.sessions.JobAnalystAgent", return_value=mock_analyst):
            resp = await client.post(
                "/api/v1/sessions/start",
                json={"text": "Senior Backend Engineer at Acme Corp..."},
                headers=auth_headers,
            )
            assert resp.status_code == 201
            session_id = resp.json()["id"]

        # 2. Approve analysis gate
        resp = await client.post(
            f"/api/v1/sessions/{session_id}/approve",
            json={"gate": "analysis", "selected_entry_ids": ["entry-1", "entry-2"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # 3. Set up mocks for generate
        mock_retrieval = MagicMock()
        mock_retrieval.embed_job_description = AsyncMock()
        mock_retrieval.embed_all_entries = AsyncMock()
        mock_retrieval.find_relevant_entries = AsyncMock(return_value=SAMPLE_ENTRIES)
        mock_retrieval_cls.return_value = mock_retrieval

        mock_scorer = MagicMock()
        mock_scorer.score.return_value = SAMPLE_MATCH
        mock_scorer_cls.return_value = mock_scorer

        mock_writer = MagicMock()
        mock_writer.write = AsyncMock(return_value=SAMPLE_RESUME)
        mock_writer_cls.return_value = mock_writer

        # 4. Generate
        resp = await client.post(
            f"/api/v1/sessions/{session_id}/generate",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "resume" in data
        assert data["resume"]["summary"] == SAMPLE_RESUME.summary
        assert len(data["resume"]["sections"]) == 2

    @patch("src.api.sessions.get_llm_config")
    async def test_generate_session_not_found(
        self,
        mock_get_config: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /sessions/{id}/generate returns 404 for unknown session."""
        import uuid

        resp = await client.post(
            f"/api/v1/sessions/{uuid.uuid4()}/generate",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @patch("src.api.sessions.RetrievalService")
    @patch("src.api.sessions.MatchScorer")
    @patch("src.api.sessions.ResumeWriterAgent")
    @patch("src.api.sessions.get_llm_config")
    async def test_generate_writer_failure(
        self,
        mock_get_config: MagicMock,
        mock_writer_cls: MagicMock,
        mock_scorer_cls: MagicMock,
        mock_retrieval_cls: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /sessions/{id}/generate returns 422 when writer fails."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        # Create session
        mock_analyst = MagicMock()
        mock_analyst.analyze = AsyncMock(return_value=SAMPLE_ANALYSIS)
        with patch("src.api.sessions.JobAnalystAgent", return_value=mock_analyst):
            resp = await client.post(
                "/api/v1/sessions/start",
                json={"text": "Engineer at Corp..."},
                headers=auth_headers,
            )
            assert resp.status_code == 201
            session_id = resp.json()["id"]

        # Approve
        resp = await client.post(
            f"/api/v1/sessions/{session_id}/approve",
            json={"gate": "analysis", "selected_entry_ids": ["entry-1"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # Mock retrieval + scorer
        mock_retrieval = MagicMock()
        mock_retrieval.embed_job_description = AsyncMock()
        mock_retrieval.embed_all_entries = AsyncMock()
        mock_retrieval.find_relevant_entries = AsyncMock(return_value=SAMPLE_ENTRIES)
        mock_retrieval_cls.return_value = mock_retrieval

        mock_scorer = MagicMock()
        mock_scorer.score.return_value = SAMPLE_MATCH
        mock_scorer_cls.return_value = mock_scorer

        # Writer fails
        mock_writer = MagicMock()
        mock_writer.write = AsyncMock(side_effect=RuntimeError("LLM error"))
        mock_writer_cls.return_value = mock_writer

        resp = await client.post(
            f"/api/v1/sessions/{session_id}/generate",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert "Failed to generate resume" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Resume session service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestResumeSessionService:
    """Tests for the ResumeSessionService."""

    @patch("src.api.sessions.get_llm_config")
    async def test_resume_stored_on_session(
        self,
        mock_get_config: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """After generate, the session stores the enhanced_resume."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        # Create session
        mock_analyst = MagicMock()
        mock_analyst.analyze = AsyncMock(return_value=SAMPLE_ANALYSIS)
        with patch("src.api.sessions.JobAnalystAgent", return_value=mock_analyst):
            resp = await client.post(
                "/api/v1/sessions/start",
                json={"text": "Engineer position..."},
                headers=auth_headers,
            )
            session_id = resp.json()["id"]

        # Approve
        await client.post(
            f"/api/v1/sessions/{session_id}/approve",
            json={"gate": "analysis", "selected_entry_ids": ["entry-1"]},
            headers=auth_headers,
        )

        # Generate
        with (
            patch("src.api.sessions.RetrievalService") as mock_ret_cls,
            patch("src.api.sessions.MatchScorer") as mock_sc_cls,
            patch("src.api.sessions.ResumeWriterAgent") as mock_wr_cls,
        ):
            mock_ret = MagicMock()
            mock_ret.embed_job_description = AsyncMock()
            mock_ret.embed_all_entries = AsyncMock()
            mock_ret.find_relevant_entries = AsyncMock(return_value=SAMPLE_ENTRIES)
            mock_ret_cls.return_value = mock_ret

            mock_sc = MagicMock()
            mock_sc.score.return_value = SAMPLE_MATCH
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

        # Verify the session now has the enhanced_resume (visible via GET)
        resp = await client.get(
            f"/api/v1/sessions/{session_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        session_data = resp.json()
        assert session_data["id"] == session_id


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestFeedbackHelpers:
    """Tests for the feedback helper functions."""

    def test_find_bullet_text(self) -> None:
        from src.api.sessions import _find_bullet_text

        text = _find_bullet_text(SAMPLE_RESUME, "0_0")
        assert "Designed and implemented" in text

    def test_find_bullet_text_not_found(self) -> None:
        from src.api.sessions import _find_bullet_text

        text = _find_bullet_text(SAMPLE_RESUME, "nonexistent")
        assert text == "(not found)"

    def test_apply_edit(self) -> None:
        from src.api.sessions import _apply_edit

        resume = SAMPLE_RESUME.model_copy(deep=True)
        _apply_edit(resume, "0_0", "New bullet text")
        found = False
        for s in resume.sections:
            for e in s.entries:
                for b in e.bullets:
                    if b.id == "0_0":
                        assert b.enhanced_text == "New bullet text"
                        found = True
        assert found

    def test_merge_revisions(self) -> None:
        from src.api.sessions import _merge_revisions

        current = SAMPLE_RESUME.model_copy(deep=True)
        # Create a revised resume with different text for bullet 0_0
        revised = SAMPLE_RESUME.model_copy(deep=True)
        for s in revised.sections:
            for e in s.entries:
                for b in e.bullets:
                    if b.id == "0_0":
                        b.enhanced_text = "Revised bullet text"

        updated = _merge_revisions(current, revised, ["0_0"])
        assert "0_0" in updated
        # Verify current was updated
        for s in current.sections:
            for e in s.entries:
                for b in e.bullets:
                    if b.id == "0_0":
                        assert b.enhanced_text == "Revised bullet text"

    def test_merge_revisions_no_match(self) -> None:
        from src.api.sessions import _merge_revisions

        current = SAMPLE_RESUME.model_copy(deep=True)
        revised = SAMPLE_RESUME.model_copy(deep=True)

        updated = _merge_revisions(current, revised, ["nonexistent"])
        assert updated == []


# ---------------------------------------------------------------------------
# Feedback endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestFeedbackEndpoint:
    """Tests for the POST /sessions/{id}/feedback endpoint."""

    async def _create_session_with_resume(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> str:
        """Helper: create a session and generate a resume on it."""
        with patch("src.api.sessions.get_llm_config") as mock_config:
            mock_config.return_value = MagicMock()

            # Start session
            mock_analyst = MagicMock()
            mock_analyst.analyze = AsyncMock(return_value=SAMPLE_ANALYSIS)
            with patch("src.api.sessions.JobAnalystAgent", return_value=mock_analyst):
                resp = await client.post(
                    "/api/v1/sessions/start",
                    json={"text": "Engineer..."},
                    headers=auth_headers,
                )
                session_id = resp.json()["id"]

            # Approve analysis
            await client.post(
                f"/api/v1/sessions/{session_id}/approve",
                json={"gate": "analysis", "selected_entry_ids": ["entry-1"]},
                headers=auth_headers,
            )

            # Generate resume
            with (
                patch("src.api.sessions.RetrievalService") as mock_ret_cls,
                patch("src.api.sessions.MatchScorer") as mock_sc_cls,
                patch("src.api.sessions.ResumeWriterAgent") as mock_wr_cls,
            ):
                mock_ret = MagicMock()
                mock_ret.embed_job_description = AsyncMock()
                mock_ret.embed_all_entries = AsyncMock()
                mock_ret.find_relevant_entries = AsyncMock(return_value=SAMPLE_ENTRIES)
                mock_ret_cls.return_value = mock_ret
                mock_sc = MagicMock()
                mock_sc.score.return_value = SAMPLE_MATCH
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
    async def test_feedback_approve_only(
        self,
        mock_config: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Submitting only approvals returns the same resume."""
        mock_config.return_value = MagicMock()
        session_id = await self._create_session_with_resume(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sessions/{session_id}/feedback",
            json={
                "decisions": [
                    {"bullet_id": "0_0", "decision": "approved"},
                    {"bullet_id": "0_1", "decision": "approved"},
                ]
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["revised_bullet_ids"] == []

    @patch("src.api.sessions.get_llm_config")
    async def test_feedback_edit(
        self,
        mock_config: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Submitting edits applies new text directly."""
        mock_config.return_value = MagicMock()
        session_id = await self._create_session_with_resume(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sessions/{session_id}/feedback",
            json={
                "decisions": [
                    {
                        "bullet_id": "0_0",
                        "decision": "edited",
                        "edited_text": "My custom bullet text",
                    },
                ]
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "0_0" in data["revised_bullet_ids"]

    @patch("src.api.sessions.RetrievalService")
    @patch("src.api.sessions.MatchScorer")
    @patch("src.api.sessions.ResumeWriterAgent")
    @patch("src.api.sessions.get_llm_config")
    async def test_feedback_reject_triggers_revision(
        self,
        mock_config: MagicMock,
        mock_writer_cls: MagicMock,
        mock_scorer_cls: MagicMock,
        mock_retrieval_cls: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Submitting rejections triggers LLM revision."""
        mock_config.return_value = MagicMock()
        session_id = await self._create_session_with_resume(client, auth_headers)

        # Mock the revision call
        revised_resume = SAMPLE_RESUME.model_copy(deep=True)
        for s in revised_resume.sections:
            for e in s.entries:
                for b in e.bullets:
                    if b.id == "0_0":
                        b.enhanced_text = "Revised by LLM"

        mock_ret = MagicMock()
        mock_ret.embed_job_description = AsyncMock()
        mock_ret.embed_all_entries = AsyncMock()
        mock_ret.find_relevant_entries = AsyncMock(return_value=SAMPLE_ENTRIES)
        mock_retrieval_cls.return_value = mock_ret
        mock_sc = MagicMock()
        mock_sc.score.return_value = SAMPLE_MATCH
        mock_scorer_cls.return_value = mock_sc
        mock_wr = MagicMock()
        mock_wr.write = AsyncMock(return_value=revised_resume)
        mock_writer_cls.return_value = mock_wr

        resp = await client.post(
            f"/api/v1/sessions/{session_id}/feedback",
            json={
                "decisions": [
                    {
                        "bullet_id": "0_0",
                        "decision": "rejected",
                        "feedback_text": "Too vague, be more specific",
                    },
                ]
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "0_0" in data["revised_bullet_ids"]

    @patch("src.api.sessions.get_llm_config")
    async def test_feedback_no_resume(
        self,
        mock_config: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Feedback on session without resume returns 400."""
        mock_config.return_value = MagicMock()

        # Create session without generating resume
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
            f"/api/v1/sessions/{session_id}/feedback",
            json={"decisions": [{"bullet_id": "0_0", "decision": "approved"}]},
            headers=auth_headers,
        )
        assert resp.status_code == 400
