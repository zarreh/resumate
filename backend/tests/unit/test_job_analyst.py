"""Tests for the Job Analyst agent and Job Description API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from src.schemas.job import JDAnalysis

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_JD_TEXT = """
Senior Backend Engineer — Acme Corp

About the Role:
We're looking for a Senior Backend Engineer to join our platform team.
You will design and build scalable microservices powering our marketplace.

Requirements:
- 5+ years of backend development experience
- Strong proficiency in Python and FastAPI or Django
- Experience with PostgreSQL, Redis, and message queues (RabbitMQ/Kafka)
- Familiarity with Docker, Kubernetes, and CI/CD pipelines
- Bachelor's degree in Computer Science or equivalent

Nice to Have:
- Experience with event-driven architectures
- Knowledge of GraphQL
- AWS or GCP cloud platform experience

Responsibilities:
- Design and implement RESTful APIs and microservices
- Optimize database performance and query patterns
- Collaborate with frontend and infrastructure teams
- Participate in code reviews and mentor junior engineers
"""

SAMPLE_ANALYSIS = JDAnalysis(
    role_title="Senior Backend Engineer",
    company_name="Acme Corp",
    seniority_level="senior",
    industry="marketplace",
    required_skills=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Kubernetes"],
    preferred_skills=["Event-driven architecture", "GraphQL", "AWS", "GCP"],
    ats_keywords=["Backend Engineer", "Python", "FastAPI", "PostgreSQL", "microservices"],
    tech_stack=["Python", "FastAPI", "Django", "PostgreSQL", "Redis", "RabbitMQ", "Kafka", "Docker", "Kubernetes"],
    responsibilities=["Design RESTful APIs", "Optimize database performance", "Code reviews"],
    qualifications=["5+ years backend experience", "Bachelor's in CS"],
    domain_expectations=[],
)


# ---------------------------------------------------------------------------
# Unit tests — JobAnalystAgent
# ---------------------------------------------------------------------------


class TestJobAnalystAgent:
    """Unit tests for the JobAnalystAgent."""

    @pytest.mark.asyncio
    async def test_analyze_returns_jd_analysis(self) -> None:
        """Agent produces a JDAnalysis from raw text."""
        from src.agents.job_analyst.schemas import JDAnalysisOutput

        mock_output = JDAnalysisOutput(analysis=SAMPLE_ANALYSIS)

        mock_structured = AsyncMock(return_value=mock_output)
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = MagicMock(ainvoke=mock_structured)

        mock_config = MagicMock()
        mock_config.get_chat_model.return_value = mock_model

        from src.agents.job_analyst.agent import JobAnalystAgent

        agent = JobAnalystAgent(mock_config)
        result = await agent.analyze(SAMPLE_JD_TEXT)

        assert isinstance(result, JDAnalysis)
        assert result.role_title == "Senior Backend Engineer"
        assert result.company_name == "Acme Corp"
        assert result.seniority_level == "senior"
        assert len(result.required_skills) > 0
        mock_config.get_chat_model.assert_called_once_with(
            "job_analyst", temperature=0.0, streaming=False
        )

    @pytest.mark.asyncio
    async def test_analyze_handles_dict_response(self) -> None:
        """Agent handles dict response from LLM."""
        dict_output = {"analysis": SAMPLE_ANALYSIS.model_dump()}

        mock_structured = AsyncMock(return_value=dict_output)
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = MagicMock(ainvoke=mock_structured)

        mock_config = MagicMock()
        mock_config.get_chat_model.return_value = mock_model

        from src.agents.job_analyst.agent import JobAnalystAgent

        agent = JobAnalystAgent(mock_config)
        result = await agent.analyze(SAMPLE_JD_TEXT)

        assert isinstance(result, JDAnalysis)
        assert result.role_title == "Senior Backend Engineer"

    @pytest.mark.asyncio
    async def test_analyze_raises_on_unexpected_type(self) -> None:
        """Agent raises TypeError for unexpected LLM output."""
        mock_structured = AsyncMock(return_value="unexpected string")
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = MagicMock(ainvoke=mock_structured)

        mock_config = MagicMock()
        mock_config.get_chat_model.return_value = mock_model

        from src.agents.job_analyst.agent import JobAnalystAgent

        agent = JobAnalystAgent(mock_config)
        with pytest.raises(TypeError, match="Unexpected LLM output type"):
            await agent.analyze(SAMPLE_JD_TEXT)

    @pytest.mark.asyncio
    async def test_analyze_raises_on_llm_error(self) -> None:
        """Agent propagates LLM errors."""
        mock_structured = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = MagicMock(ainvoke=mock_structured)

        mock_config = MagicMock()
        mock_config.get_chat_model.return_value = mock_model

        from src.agents.job_analyst.agent import JobAnalystAgent

        agent = JobAnalystAgent(mock_config)
        with pytest.raises(RuntimeError, match="LLM unavailable"):
            await agent.analyze(SAMPLE_JD_TEXT)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestJDAnalysisSchema:
    """Tests for the JDAnalysis Pydantic schema."""

    def test_full_schema(self) -> None:
        """Schema accepts all fields."""
        data = SAMPLE_ANALYSIS.model_dump()
        analysis = JDAnalysis.model_validate(data)
        assert analysis.role_title == "Senior Backend Engineer"
        assert analysis.company_name == "Acme Corp"

    def test_minimal_schema(self) -> None:
        """Schema works with only required fields."""
        analysis = JDAnalysis(
            role_title="Software Engineer",
            seniority_level="mid",
            industry="SaaS",
        )
        assert analysis.company_name is None
        assert analysis.required_skills == []
        assert analysis.domain_expectations == []

    def test_serialization_roundtrip(self) -> None:
        """Schema serializes and deserializes correctly."""
        data = SAMPLE_ANALYSIS.model_dump()
        restored = JDAnalysis.model_validate(data)
        assert restored == SAMPLE_ANALYSIS


# ---------------------------------------------------------------------------
# Integration tests — API endpoints
# ---------------------------------------------------------------------------


def _mock_agent_analyze(analysis: JDAnalysis) -> AsyncMock:
    """Create a mock for JobAnalystAgent.analyze that returns the given analysis."""
    mock_agent_instance = AsyncMock()
    mock_agent_instance.analyze = AsyncMock(return_value=analysis)
    return mock_agent_instance


class TestParseJobDescriptionEndpoint:
    """Tests for POST /api/v1/jobs/parse."""

    @pytest.mark.asyncio
    async def test_parse_success(self, client: AsyncClient, auth_headers: dict) -> None:
        """Successful JD parsing returns analysis."""
        mock_agent = _mock_agent_analyze(SAMPLE_ANALYSIS)

        with (
            patch("src.api.jobs.get_llm_config") as mock_config,
            patch("src.api.jobs.JobAnalystAgent", return_value=mock_agent),
        ):
            mock_config.return_value = MagicMock()
            resp = await client.post(
                "/api/v1/jobs/parse",
                json={"text": SAMPLE_JD_TEXT},
                headers=auth_headers,
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["analysis"]["role_title"] == "Senior Backend Engineer"
        assert data["raw_text"] == SAMPLE_JD_TEXT
        assert "id" in data

    @pytest.mark.asyncio
    async def test_parse_empty_text(self, client: AsyncClient, auth_headers: dict) -> None:
        """Empty text returns 422 (validation error)."""
        resp = await client.post(
            "/api/v1/jobs/parse",
            json={"text": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_parse_requires_auth(self, client: AsyncClient) -> None:
        """Endpoint requires authentication."""
        resp = await client.post(
            "/api/v1/jobs/parse",
            json={"text": SAMPLE_JD_TEXT},
        )
        assert resp.status_code in (401, 403)


class TestJobHistoryEndpoint:
    """Tests for GET /api/v1/jobs/history."""

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict) -> None:
        """Empty history returns empty list."""
        resp = await client.get("/api/v1/jobs/history", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_after_parse(self, client: AsyncClient, auth_headers: dict) -> None:
        """After parsing a JD, it appears in history."""
        mock_agent = _mock_agent_analyze(SAMPLE_ANALYSIS)

        with (
            patch("src.api.jobs.get_llm_config") as mock_config,
            patch("src.api.jobs.JobAnalystAgent", return_value=mock_agent),
        ):
            mock_config.return_value = MagicMock()
            await client.post(
                "/api/v1/jobs/parse",
                json={"text": SAMPLE_JD_TEXT},
                headers=auth_headers,
            )

        resp = await client.get("/api/v1/jobs/history", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["analysis"]["role_title"] == "Senior Backend Engineer"


class TestGetJobDescriptionEndpoint:
    """Tests for GET /api/v1/jobs/{job_id}."""

    @pytest.mark.asyncio
    async def test_get_not_found(self, client: AsyncClient, auth_headers: dict) -> None:
        """Non-existent JD returns 404."""
        import uuid

        resp = await client.get(
            f"/api/v1/jobs/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_after_parse(self, client: AsyncClient, auth_headers: dict) -> None:
        """Can retrieve a parsed JD by ID."""
        mock_agent = _mock_agent_analyze(SAMPLE_ANALYSIS)

        with (
            patch("src.api.jobs.get_llm_config") as mock_config,
            patch("src.api.jobs.JobAnalystAgent", return_value=mock_agent),
        ):
            mock_config.return_value = MagicMock()
            parse_resp = await client.post(
                "/api/v1/jobs/parse",
                json={"text": SAMPLE_JD_TEXT},
                headers=auth_headers,
            )

        jd_id = parse_resp.json()["id"]
        resp = await client.get(f"/api/v1/jobs/{jd_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["analysis"]["role_title"] == "Senior Backend Engineer"


class TestSessionEndpoints:
    """Tests for session management endpoints."""

    @pytest.mark.asyncio
    async def test_start_session(self, client: AsyncClient, auth_headers: dict) -> None:
        """Starting a session creates it with analysis gate."""
        mock_agent = _mock_agent_analyze(SAMPLE_ANALYSIS)

        with (
            patch("src.api.sessions.get_llm_config") as mock_config,
            patch("src.api.sessions.JobAnalystAgent", return_value=mock_agent),
        ):
            mock_config.return_value = MagicMock()
            resp = await client.post(
                "/api/v1/sessions/start",
                json={"text": SAMPLE_JD_TEXT},
                headers=auth_headers,
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["current_gate"] == "analysis"
        assert data["analysis"]["role_title"] == "Senior Backend Engineer"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_session(self, client: AsyncClient, auth_headers: dict) -> None:
        """Can retrieve a session by ID."""
        mock_agent = _mock_agent_analyze(SAMPLE_ANALYSIS)

        with (
            patch("src.api.sessions.get_llm_config") as mock_config,
            patch("src.api.sessions.JobAnalystAgent", return_value=mock_agent),
        ):
            mock_config.return_value = MagicMock()
            start_resp = await client.post(
                "/api/v1/sessions/start",
                json={"text": SAMPLE_JD_TEXT},
                headers=auth_headers,
            )

        session_id = start_resp.json()["id"]
        resp = await client.get(f"/api/v1/sessions/{session_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["current_gate"] == "analysis"

    @pytest.mark.asyncio
    async def test_approve_analysis_gate(self, client: AsyncClient, auth_headers: dict) -> None:
        """Approving the analysis gate advances to calibration."""
        mock_agent = _mock_agent_analyze(SAMPLE_ANALYSIS)

        with (
            patch("src.api.sessions.get_llm_config") as mock_config,
            patch("src.api.sessions.JobAnalystAgent", return_value=mock_agent),
        ):
            mock_config.return_value = MagicMock()
            start_resp = await client.post(
                "/api/v1/sessions/start",
                json={"text": SAMPLE_JD_TEXT},
                headers=auth_headers,
            )

        session_id = start_resp.json()["id"]
        resp = await client.post(
            f"/api/v1/sessions/{session_id}/approve",
            json={"gate": "analysis", "selected_entry_ids": ["entry-1"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["current_gate"] == "calibration"

    @pytest.mark.asyncio
    async def test_approve_wrong_gate(self, client: AsyncClient, auth_headers: dict) -> None:
        """Approving the wrong gate returns 400."""
        mock_agent = _mock_agent_analyze(SAMPLE_ANALYSIS)

        with (
            patch("src.api.sessions.get_llm_config") as mock_config,
            patch("src.api.sessions.JobAnalystAgent", return_value=mock_agent),
        ):
            mock_config.return_value = MagicMock()
            start_resp = await client.post(
                "/api/v1/sessions/start",
                json={"text": SAMPLE_JD_TEXT},
                headers=auth_headers,
            )

        session_id = start_resp.json()["id"]
        resp = await client.post(
            f"/api/v1/sessions/{session_id}/approve",
            json={"gate": "review"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_session_not_found(self, client: AsyncClient, auth_headers: dict) -> None:
        """Non-existent session returns 404."""
        import uuid

        resp = await client.get(
            f"/api/v1/sessions/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_start_session_requires_auth(self, client: AsyncClient) -> None:
        """Starting a session requires authentication."""
        resp = await client.post(
            "/api/v1/sessions/start",
            json={"text": SAMPLE_JD_TEXT},
        )
        assert resp.status_code in (401, 403)
