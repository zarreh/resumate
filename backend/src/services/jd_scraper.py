"""URL-based job description scraper.

Fetches a URL with httpx and extracts clean text from the HTML using
BeautifulSoup.  The extracted text is sanitized (no scripts, styles, or
navigation boilerplate) before being returned for LLM analysis.
"""

from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

# Tags whose content is never useful for JD extraction.
_STRIP_TAGS = {
    "script",
    "style",
    "nav",
    "footer",
    "header",
    "noscript",
    "svg",
    "img",
    "iframe",
    "form",
}

# Maximum response size to prevent memory exhaustion (5 MB).
_MAX_CONTENT_LENGTH = 5 * 1024 * 1024

# Timeout for the HTTP request.
_REQUEST_TIMEOUT = 15.0


class ScraperError(Exception):
    """Raised when URL fetching or content extraction fails."""


async def fetch_job_description(url: str) -> str:
    """Fetch a URL and extract the main text content.

    Args:
        url: The URL to fetch.

    Returns:
        Cleaned text extracted from the page.

    Raises:
        ScraperError: If the URL cannot be fetched or contains no text.
    """
    html = await _fetch_html(url)
    text = _extract_text(html)
    if not text.strip():
        raise ScraperError("No text content could be extracted from the page")
    return text


async def _fetch_html(url: str) -> str:
    """Fetch the raw HTML from a URL."""
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=_REQUEST_TIMEOUT,
        ) as client:
            resp = await client.get(url, headers={"User-Agent": "ResuMate/1.0"})
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ScraperError(
            f"HTTP {exc.response.status_code} when fetching {url}"
        ) from exc
    except httpx.RequestError as exc:
        raise ScraperError(f"Failed to fetch URL: {exc}") from exc

    content_type = resp.headers.get("content-type", "")
    if "text/html" not in content_type and "text/plain" not in content_type:
        raise ScraperError(
            f"Unsupported content type: {content_type}. Expected HTML or text."
        )

    if len(resp.content) > _MAX_CONTENT_LENGTH:
        raise ScraperError(
            f"Response too large ({len(resp.content)} bytes, max {_MAX_CONTENT_LENGTH})"
        )

    return resp.text


def _extract_text(html: str) -> str:
    """Parse HTML and return clean, readable text."""
    soup = BeautifulSoup(html, "lxml")

    # Remove unwanted tags entirely.
    for tag in soup.find_all(_STRIP_TAGS):
        tag.decompose()

    # Try to find common JD container elements first.
    main_content = (
        soup.find("main")
        or soup.find("article")
        or soup.find(attrs={"role": "main"})
        or soup.find(class_=re.compile(r"job|description|posting|content", re.I))
    )

    target = main_content if main_content else soup.body or soup

    # Get text with separator to preserve structure.
    raw_text = target.get_text(separator="\n", strip=True)

    # Collapse excessive blank lines.
    lines = raw_text.splitlines()
    cleaned: list[str] = []
    prev_blank = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if not prev_blank:
                cleaned.append("")
            prev_blank = True
        else:
            cleaned.append(stripped)
            prev_blank = False

    return "\n".join(cleaned).strip()
