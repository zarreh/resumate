"""Tests for URL-based JD scraper (Phase 8.1)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.services.jd_scraper import (
    ScraperError,
    _extract_text,
    fetch_job_description,
)

# ---------------------------------------------------------------------------
# _extract_text unit tests (pure HTML parsing, no network)
# ---------------------------------------------------------------------------


class TestExtractText:
    def test_basic_html(self):
        html = "<html><body><p>Software Engineer at ACME Corp</p></body></html>"
        text = _extract_text(html)
        assert "Software Engineer at ACME Corp" in text

    def test_strips_script_and_style(self):
        html = """
        <html><body>
            <script>var x = 1;</script>
            <style>.foo { color: red; }</style>
            <p>Job Description</p>
        </body></html>
        """
        text = _extract_text(html)
        assert "var x" not in text
        assert ".foo" not in text
        assert "Job Description" in text

    def test_strips_nav_and_footer(self):
        html = """
        <html><body>
            <nav><a href="/">Home</a><a href="/jobs">Jobs</a></nav>
            <main><p>We are hiring a developer.</p></main>
            <footer>Copyright 2025</footer>
        </body></html>
        """
        text = _extract_text(html)
        assert "Home" not in text
        assert "Copyright" not in text
        assert "We are hiring a developer." in text

    def test_prefers_main_element(self):
        html = """
        <html><body>
            <div>Site header stuff</div>
            <main>
                <h1>Senior Engineer</h1>
                <p>Requirements: Python, SQL</p>
            </main>
            <div>Footer stuff</div>
        </body></html>
        """
        text = _extract_text(html)
        assert "Senior Engineer" in text
        assert "Requirements: Python, SQL" in text

    def test_prefers_article_element(self):
        html = """
        <html><body>
            <div>Sidebar</div>
            <article>
                <h2>Data Scientist</h2>
                <p>We need ML experience</p>
            </article>
        </body></html>
        """
        text = _extract_text(html)
        assert "Data Scientist" in text
        assert "ML experience" in text

    def test_finds_job_class(self):
        html = """
        <html><body>
            <div>Header</div>
            <div class="job-description">
                <h2>DevOps Engineer</h2>
                <ul><li>Kubernetes</li><li>Docker</li></ul>
            </div>
        </body></html>
        """
        text = _extract_text(html)
        assert "DevOps Engineer" in text
        assert "Kubernetes" in text

    def test_collapses_blank_lines(self):
        html = """
        <html><body>
            <p>Line 1</p>
            <br/><br/><br/>
            <p>Line 2</p>
        </body></html>
        """
        text = _extract_text(html)
        # Should not have more than one consecutive blank line
        assert "\n\n\n" not in text

    def test_empty_body_returns_empty(self):
        html = "<html><body></body></html>"
        text = _extract_text(html)
        assert text == ""


# ---------------------------------------------------------------------------
# fetch_job_description tests (with mocked HTTP)
# ---------------------------------------------------------------------------


class TestFetchJobDescription:
    @pytest.mark.asyncio
    async def test_success(self):
        mock_response = httpx.Response(
            200,
            text="<html><body><p>Engineer needed</p></body></html>",
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", "https://example.com/job/123"),
        )
        with patch("src.services.jd_scraper.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            text = await fetch_job_description("https://example.com/job/123")
            assert "Engineer needed" in text

    @pytest.mark.asyncio
    async def test_http_error(self):
        mock_response = httpx.Response(
            404,
            request=httpx.Request("GET", "https://example.com/job/404"),
            headers={"content-type": "text/html"},
        )
        with patch("src.services.jd_scraper.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ScraperError, match="HTTP 404"):
                await fetch_job_description("https://example.com/job/404")

    @pytest.mark.asyncio
    async def test_connection_error(self):
        with patch("src.services.jd_scraper.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ScraperError, match="Failed to fetch URL"):
                await fetch_job_description("https://example.com/down")

    @pytest.mark.asyncio
    async def test_unsupported_content_type(self):
        mock_response = httpx.Response(
            200,
            content=b"%PDF-1.4...",
            headers={"content-type": "application/pdf"},
            request=httpx.Request("GET", "https://example.com/job.pdf"),
        )
        with patch("src.services.jd_scraper.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ScraperError, match="Unsupported content type"):
                await fetch_job_description("https://example.com/job.pdf")

    @pytest.mark.asyncio
    async def test_empty_content_raises(self):
        mock_response = httpx.Response(
            200,
            text="<html><body></body></html>",
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", "https://example.com/empty"),
        )
        with patch("src.services.jd_scraper.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ScraperError, match="No text content"):
                await fetch_job_description("https://example.com/empty")
