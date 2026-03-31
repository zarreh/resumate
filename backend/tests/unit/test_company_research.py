"""Tests for company research service (Phase 8.2)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.company_research import CompanyResearch, CompanyResearchService

# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestCompanyResearchSchema:
    def test_minimal(self):
        cr = CompanyResearch(company_name="ACME")
        assert cr.company_name == "ACME"
        assert cr.summary is None
        assert cr.products == []
        assert cr.recent_news == []

    def test_full(self):
        cr = CompanyResearch(
            company_name="ACME Corp",
            summary="A tech company",
            mission="Make stuff",
            products=["Widget", "Gadget"],
            culture="Fast-paced",
            recent_news=["Raised $10M"],
            size_and_funding="200 employees",
            headquarters="San Francisco",
            industry="Technology",
        )
        assert cr.company_name == "ACME Corp"
        assert len(cr.products) == 2
        assert cr.headquarters == "San Francisco"

    def test_model_dump_roundtrip(self):
        cr = CompanyResearch(company_name="Test", summary="A test company")
        data = cr.model_dump()
        restored = CompanyResearch.model_validate(data)
        assert restored.company_name == "Test"
        assert restored.summary == "A test company"


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestCompanyResearchService:
    @pytest.mark.asyncio
    async def test_research_with_results(self):
        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        expected = CompanyResearch(
            company_name="ACME",
            summary="A leading tech company",
            products=["Widget"],
        )

        structured_model = AsyncMock()
        structured_model.ainvoke.return_value = expected
        mock_model.with_structured_output.return_value = structured_model

        svc = CompanyResearchService(mock_llm_config)

        with patch.object(svc, "_search_web", return_value=["ACME is a tech company"]):
            result = await svc.research("ACME")

        assert result.company_name == "ACME"
        assert result.summary == "A leading tech company"
        assert result.products == ["Widget"]

    @pytest.mark.asyncio
    async def test_research_no_search_results(self):
        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        svc = CompanyResearchService(mock_llm_config)

        with patch.object(svc, "_search_web", return_value=[]):
            result = await svc.research("Unknown Corp")

        assert result.company_name == "Unknown Corp"
        assert result.summary is None

    @pytest.mark.asyncio
    async def test_research_llm_failure_returns_minimal(self):
        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        structured_model = AsyncMock()
        structured_model.ainvoke.side_effect = RuntimeError("LLM down")
        mock_model.with_structured_output.return_value = structured_model

        svc = CompanyResearchService(mock_llm_config)

        with patch.object(svc, "_search_web", return_value=["Some snippet"]):
            result = await svc.research("ACME")

        assert result.company_name == "ACME"
        assert result.summary is None

    def test_search_web_success(self):
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text.return_value = [
            {"body": "Snippet 1"},
            {"body": "Snippet 2"},
            {"body": ""},
        ]

        with patch("src.services.company_research.DDGS", return_value=mock_ddgs):
            result = CompanyResearchService._search_web("ACME")

        assert result == ["Snippet 1", "Snippet 2"]

    def test_search_web_exception(self):
        with patch("src.services.company_research.DDGS", side_effect=RuntimeError("Network error")):
            result = CompanyResearchService._search_web("ACME")

        assert result == []

    @pytest.mark.asyncio
    async def test_summarize_dict_response(self):
        """LLM returns a dict instead of CompanyResearch — should still work."""
        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_llm_config.get_chat_model.return_value = mock_model

        structured_model = AsyncMock()
        structured_model.ainvoke.return_value = {
            "company_name": "ACME",
            "summary": "A company",
        }
        mock_model.with_structured_output.return_value = structured_model

        svc = CompanyResearchService(mock_llm_config)
        result = await svc._summarize("ACME", ["snippet"])

        assert result.company_name == "ACME"
        assert result.summary == "A company"


# ---------------------------------------------------------------------------
# Integration: jobs/parse endpoint with company research
# ---------------------------------------------------------------------------


class TestParseJobDescriptionWithCompanyResearch:
    @pytest.mark.asyncio
    async def test_company_research_triggered_when_company_name_present(self):
        from src.schemas.job import JDAnalysis, JobParseRequest

        mock_analysis = JDAnalysis(
            role_title="Engineer",
            company_name="ACME Corp",
            seniority_level="mid",
            industry="Tech",
        )

        mock_research = CompanyResearch(
            company_name="ACME Corp",
            summary="A leading tech company",
        )

        mock_jd = MagicMock()
        mock_jd.id = "jd-id-1"
        mock_jd.raw_text = "Job description text"
        mock_jd.analysis = mock_analysis.model_dump()
        mock_jd.company_research = mock_research.model_dump()
        mock_jd.created_at = MagicMock()
        mock_jd.created_at.isoformat.return_value = "2025-06-01T00:00:00+00:00"

        with (
            patch("src.api.jobs.JobService") as MockJobService,
            patch("src.api.jobs.JobAnalystAgent") as MockAgent,
            patch("src.api.jobs.CompanyResearchService") as MockResearchService,
            patch("src.api.jobs.get_llm_config"),
        ):
            mock_svc = AsyncMock()
            mock_svc.create_job_description.return_value = mock_jd
            mock_svc.update_analysis.return_value = mock_jd
            mock_svc.update_company_research.return_value = mock_jd
            MockJobService.return_value = mock_svc

            mock_agent_inst = AsyncMock()
            mock_agent_inst.analyze.return_value = mock_analysis
            MockAgent.return_value = mock_agent_inst

            mock_research_inst = AsyncMock()
            mock_research_inst.research.return_value = mock_research
            MockResearchService.return_value = mock_research_inst

            from src.api.jobs import parse_job_description

            mock_user = MagicMock()
            mock_user.id = "user-1"
            mock_db = AsyncMock()

            body = JobParseRequest(text="Job description text")
            result = await parse_job_description(
                body=body, current_user=mock_user, db=mock_db
            )

            mock_research_inst.research.assert_called_once_with("ACME Corp")
            mock_svc.update_company_research.assert_called_once()
            assert result.company_research is not None

    @pytest.mark.asyncio
    async def test_company_research_skipped_when_no_company_name(self):
        from src.schemas.job import JDAnalysis, JobParseRequest

        mock_analysis = JDAnalysis(
            role_title="Engineer",
            company_name=None,
            seniority_level="mid",
            industry="Tech",
        )

        mock_jd = MagicMock()
        mock_jd.id = "jd-id-1"
        mock_jd.raw_text = "Job description text"
        mock_jd.analysis = mock_analysis.model_dump()
        mock_jd.company_research = None
        mock_jd.created_at = MagicMock()
        mock_jd.created_at.isoformat.return_value = "2025-06-01T00:00:00+00:00"

        with (
            patch("src.api.jobs.JobService") as MockJobService,
            patch("src.api.jobs.JobAnalystAgent") as MockAgent,
            patch("src.api.jobs.CompanyResearchService") as MockResearchService,
            patch("src.api.jobs.get_llm_config"),
        ):
            mock_svc = AsyncMock()
            mock_svc.create_job_description.return_value = mock_jd
            mock_svc.update_analysis.return_value = mock_jd
            MockJobService.return_value = mock_svc

            mock_agent_inst = AsyncMock()
            mock_agent_inst.analyze.return_value = mock_analysis
            MockAgent.return_value = mock_agent_inst

            from src.api.jobs import parse_job_description

            mock_user = MagicMock()
            mock_user.id = "user-1"
            mock_db = AsyncMock()

            body = JobParseRequest(text="Job description text")
            await parse_job_description(
                body=body, current_user=mock_user, db=mock_db
            )

            MockResearchService.assert_not_called()
