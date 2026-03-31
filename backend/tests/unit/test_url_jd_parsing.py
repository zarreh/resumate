"""Tests for URL-based JD parsing endpoints (Phase 8.1)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.job import JDAnalysis, JobParseRequest

# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestJobParseRequestSchema:
    def test_text_only(self):
        req = JobParseRequest(text="Some JD text")
        assert req.text == "Some JD text"
        assert req.url is None

    def test_url_only(self):
        req = JobParseRequest(url="https://example.com/job/123")
        assert req.url == "https://example.com/job/123"
        assert req.text is None

    def test_both_text_and_url(self):
        req = JobParseRequest(text="Some text", url="https://example.com/job")
        assert req.text == "Some text"
        assert req.url == "https://example.com/job"

    def test_neither_raises(self):
        with pytest.raises(ValueError, match="Either 'text' or 'url' must be provided"):
            JobParseRequest()

    def test_empty_strings_raise(self):
        with pytest.raises(ValueError, match="Either 'text' or 'url' must be provided"):
            JobParseRequest(text="", url="")


class TestSessionStartRequestSchema:
    def test_text_only(self):
        from src.api.sessions import SessionStartRequest

        req = SessionStartRequest(text="JD text here")
        assert req.text == "JD text here"
        assert req.url is None

    def test_url_only(self):
        from src.api.sessions import SessionStartRequest

        req = SessionStartRequest(url="https://example.com/job/456")
        assert req.url == "https://example.com/job/456"

    def test_neither_raises(self):
        from src.api.sessions import SessionStartRequest

        with pytest.raises(ValueError, match="Either 'text' or 'url' must be provided"):
            SessionStartRequest()


# ---------------------------------------------------------------------------
# Endpoint tests — jobs/parse with URL
# ---------------------------------------------------------------------------


class TestParseJobDescriptionWithUrl:
    @pytest.mark.asyncio
    async def test_parse_with_url_success(self):
        mock_analysis = MagicMock()
        mock_analysis.model_dump.return_value = {
            "role_title": "Engineer",
            "company_name": "ACME",
            "seniority_level": "mid",
            "industry": "Tech",
            "required_skills": [],
            "preferred_skills": [],
            "ats_keywords": [],
            "tech_stack": [],
            "responsibilities": [],
            "qualifications": [],
            "domain_expectations": [],
        }

        with (
            patch("src.api.jobs.fetch_job_description", new_callable=AsyncMock) as mock_fetch,
            patch("src.api.jobs.JobService") as MockJobService,
            patch("src.api.jobs.JobAnalystAgent") as MockAgent,
            patch("src.api.jobs.get_llm_config"),
        ):
            mock_fetch.return_value = "Scraped JD text from URL"

            mock_jd = MagicMock()
            mock_jd.id = "jd-id-1"
            mock_jd.raw_text = "Scraped JD text from URL"
            mock_jd.analysis = mock_analysis.model_dump.return_value
            mock_jd.created_at = MagicMock()
            mock_jd.created_at.isoformat.return_value = "2025-06-01T00:00:00+00:00"

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

            body = JobParseRequest(url="https://example.com/job/123")
            result = await parse_job_description(
                body=body, current_user=mock_user, db=mock_db
            )

            mock_fetch.assert_called_once_with("https://example.com/job/123")
            mock_svc.create_job_description.assert_called_once_with(
                "user-1", "Scraped JD text from URL"
            )
            assert result.raw_text == "Scraped JD text from URL"

    @pytest.mark.asyncio
    async def test_parse_with_url_scraper_error(self):
        from src.services.jd_scraper import ScraperError

        with patch(
            "src.api.jobs.fetch_job_description",
            new_callable=AsyncMock,
            side_effect=ScraperError("HTTP 404"),
        ):
            from fastapi import HTTPException

            from src.api.jobs import parse_job_description

            mock_user = MagicMock()
            mock_user.id = "user-1"
            mock_db = AsyncMock()

            body = JobParseRequest(url="https://example.com/missing")
            with pytest.raises(HTTPException) as exc_info:
                await parse_job_description(
                    body=body, current_user=mock_user, db=mock_db
                )
            assert exc_info.value.status_code == 422
            assert "Failed to fetch URL" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Endpoint tests — sessions/start with URL
# ---------------------------------------------------------------------------


class TestStartSessionWithUrl:
    @pytest.mark.asyncio
    async def test_start_with_url_calls_scraper(self):
        from src.api.sessions import SessionStartRequest

        with (
            patch("src.api.sessions.fetch_job_description", new_callable=AsyncMock) as mock_fetch,
            patch("src.api.sessions.JobService") as MockJobService,
            patch("src.api.sessions.JobAnalystAgent") as MockAgent,
            patch("src.api.sessions.get_llm_config"),
        ):
            mock_fetch.return_value = "Scraped text"

            mock_analysis = JDAnalysis(
                role_title="Dev",
                company_name=None,
                seniority_level="mid",
                industry="Tech",
            )

            mock_jd = MagicMock()
            mock_jd.id = "jd-1"
            mock_jd.analysis = mock_analysis.model_dump()

            mock_session = MagicMock()
            mock_session.id = "sess-1"
            mock_session.job_description_id = "jd-1"
            mock_session.current_gate = "analysis"
            mock_session.selected_entry_ids = []
            mock_session.context_text = None
            mock_session.style_preference = None
            mock_session.enhanced_resume = None
            mock_session.forked_from_id = None
            mock_session.created_at = MagicMock()
            mock_session.created_at.isoformat.return_value = "2025-06-01"

            mock_svc = AsyncMock()
            mock_svc.create_job_description.return_value = mock_jd
            mock_svc.update_analysis.return_value = mock_jd
            mock_svc.create_session.return_value = mock_session
            MockJobService.return_value = mock_svc

            mock_agent_inst = AsyncMock()
            mock_agent_inst.analyze.return_value = mock_analysis
            MockAgent.return_value = mock_agent_inst

            from src.api.sessions import start_session

            mock_user = MagicMock()
            mock_user.id = "user-1"
            mock_db = AsyncMock()

            body = SessionStartRequest(url="https://jobs.example.com/42")
            await start_session(body=body, current_user=mock_user, db=mock_db)

            mock_fetch.assert_called_once_with("https://jobs.example.com/42")
            mock_svc.create_job_description.assert_called_once_with(
                "user-1", "Scraped text"
            )

    @pytest.mark.asyncio
    async def test_start_with_url_scraper_error(self):
        from src.api.sessions import SessionStartRequest
        from src.services.jd_scraper import ScraperError

        with patch(
            "src.api.sessions.fetch_job_description",
            new_callable=AsyncMock,
            side_effect=ScraperError("Connection refused"),
        ):
            from fastapi import HTTPException

            from src.api.sessions import start_session

            mock_user = MagicMock()
            mock_user.id = "user-1"
            mock_db = AsyncMock()

            body = SessionStartRequest(url="https://down.example.com/job")
            with pytest.raises(HTTPException) as exc_info:
                await start_session(body=body, current_user=mock_user, db=mock_db)
            assert exc_info.value.status_code == 422
            assert "Failed to fetch URL" in exc_info.value.detail
