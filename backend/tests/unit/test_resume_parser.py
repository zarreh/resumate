"""Tests for LLM-based resume parsing (Phase 2.2b)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from src.schemas.career import ParsedBulletPoint, ParsedResumeEntry
from src.services.resume_parser import ParsedResumeOutput, ResumeParser

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_RESUME_TEXT = """\
John Doe
Software Engineer

Experience

Senior Software Engineer, Acme Corp (2020-2023)
- Built scalable REST APIs serving 1M+ daily requests using Python and FastAPI
- Led migration from monolith to microservices architecture on AWS
- Mentored 3 junior developers

Software Engineer, Startup Inc (2018-2020)
- Developed real-time data pipeline with Apache Kafka and Python
- Implemented CI/CD pipelines using GitHub Actions

Education

B.S. Computer Science, MIT, 2018
- GPA: 3.8/4.0, Dean's List
"""

MOCK_PARSED_ENTRIES = [
    ParsedResumeEntry(
        entry_type="work_experience",
        title="Senior Software Engineer",
        organization="Acme Corp",
        start_date="2020",
        end_date="2023",
        bullet_points=[
            ParsedBulletPoint(
                text="Built scalable REST APIs serving 1M+ daily requests using Python and FastAPI",
                tags=["Python", "FastAPI", "REST APIs"],
            ),
            ParsedBulletPoint(
                text="Led migration from monolith to microservices architecture on AWS",
                tags=["AWS", "microservices"],
            ),
            ParsedBulletPoint(text="Mentored 3 junior developers", tags=[]),
        ],
        tags=["Python", "FastAPI", "REST APIs", "AWS", "microservices"],
        raw_text="Senior Software Engineer, Acme Corp (2020-2023)\n- Built scalable REST APIs...",
    ),
    ParsedResumeEntry(
        entry_type="work_experience",
        title="Software Engineer",
        organization="Startup Inc",
        start_date="2018",
        end_date="2020",
        bullet_points=[
            ParsedBulletPoint(
                text="Developed real-time data pipeline with Apache Kafka and Python",
                tags=["Apache Kafka", "Python"],
            ),
            ParsedBulletPoint(
                text="Implemented CI/CD pipelines using GitHub Actions",
                tags=["GitHub Actions", "CI/CD"],
            ),
        ],
        tags=["Apache Kafka", "Python", "GitHub Actions", "CI/CD"],
        raw_text="Software Engineer, Startup Inc (2018-2020)...",
    ),
    ParsedResumeEntry(
        entry_type="education",
        title="B.S. Computer Science",
        organization="MIT",
        start_date=None,
        end_date="2018",
        bullet_points=[
            ParsedBulletPoint(text="GPA: 3.8/4.0, Dean's List", tags=[]),
        ],
        tags=[],
        raw_text="B.S. Computer Science, MIT, 2018...",
    ),
]


def _mock_llm_config() -> MagicMock:
    """Create a mock LLMConfig that returns a mock chat model."""
    config = MagicMock()
    config.get_chat_model.return_value = MagicMock()
    return config


# ---------------------------------------------------------------------------
# Unit tests — ResumeParser
# ---------------------------------------------------------------------------


class TestResumeParser:
    @pytest.mark.asyncio
    async def test_parse_returns_entries(self) -> None:
        """Parser returns structured entries from LLM response."""
        config = _mock_llm_config()
        parser = ResumeParser(config)

        mock_structured = AsyncMock(
            return_value=ParsedResumeOutput(entries=MOCK_PARSED_ENTRIES)
        )
        parser._model = MagicMock()
        parser._model.with_structured_output.return_value = MagicMock(
            ainvoke=mock_structured
        )

        entries = await parser.parse(SAMPLE_RESUME_TEXT)

        assert len(entries) == 3
        assert entries[0].title == "Senior Software Engineer"
        assert entries[0].organization == "Acme Corp"
        assert entries[0].entry_type == "work_experience"
        assert len(entries[0].bullet_points) == 3
        assert "Python" in entries[0].tags

    @pytest.mark.asyncio
    async def test_parse_education_entry(self) -> None:
        """Parser correctly handles education entries."""
        config = _mock_llm_config()
        parser = ResumeParser(config)

        mock_structured = AsyncMock(
            return_value=ParsedResumeOutput(entries=[MOCK_PARSED_ENTRIES[2]])
        )
        parser._model = MagicMock()
        parser._model.with_structured_output.return_value = MagicMock(
            ainvoke=mock_structured
        )

        entries = await parser.parse("B.S. Computer Science, MIT, 2018")

        assert len(entries) == 1
        assert entries[0].entry_type == "education"
        assert entries[0].title == "B.S. Computer Science"
        assert entries[0].organization == "MIT"

    @pytest.mark.asyncio
    async def test_parse_handles_dict_response(self) -> None:
        """Parser handles LLM returning a dict instead of Pydantic model."""
        config = _mock_llm_config()
        parser = ResumeParser(config)

        dict_response = {
            "entries": [
                {
                    "entry_type": "work_experience",
                    "title": "Engineer",
                    "organization": "Corp",
                    "bullet_points": [],
                    "tags": ["Python"],
                }
            ]
        }
        mock_structured = AsyncMock(return_value=dict_response)
        parser._model = MagicMock()
        parser._model.with_structured_output.return_value = MagicMock(
            ainvoke=mock_structured
        )

        entries = await parser.parse("Some resume text")

        assert len(entries) == 1
        assert entries[0].title == "Engineer"
        assert entries[0].tags == ["Python"]

    @pytest.mark.asyncio
    async def test_parse_empty_resume(self) -> None:
        """Parser returns empty list for resume with no identifiable entries."""
        config = _mock_llm_config()
        parser = ResumeParser(config)

        mock_structured = AsyncMock(
            return_value=ParsedResumeOutput(entries=[])
        )
        parser._model = MagicMock()
        parser._model.with_structured_output.return_value = MagicMock(
            ainvoke=mock_structured
        )

        entries = await parser.parse("Just some random text without structure")
        assert entries == []

    @pytest.mark.asyncio
    async def test_parse_preserves_bullet_tags(self) -> None:
        """Each bullet point has its own tags extracted."""
        config = _mock_llm_config()
        parser = ResumeParser(config)

        mock_structured = AsyncMock(
            return_value=ParsedResumeOutput(entries=MOCK_PARSED_ENTRIES[:1])
        )
        parser._model = MagicMock()
        parser._model.with_structured_output.return_value = MagicMock(
            ainvoke=mock_structured
        )

        entries = await parser.parse(SAMPLE_RESUME_TEXT)

        bullet = entries[0].bullet_points[0]
        assert "Python" in bullet.tags
        assert "FastAPI" in bullet.tags

    @pytest.mark.asyncio
    async def test_parse_llm_error_propagates(self) -> None:
        """LLM errors propagate as exceptions."""
        config = _mock_llm_config()
        parser = ResumeParser(config)

        mock_structured = AsyncMock(side_effect=RuntimeError("LLM API error"))
        parser._model = MagicMock()
        parser._model.with_structured_output.return_value = MagicMock(
            ainvoke=mock_structured
        )

        with pytest.raises(RuntimeError, match="LLM API error"):
            await parser.parse(SAMPLE_RESUME_TEXT)

    @pytest.mark.asyncio
    async def test_parse_unexpected_type_raises(self) -> None:
        """Unexpected LLM output type raises TypeError."""
        config = _mock_llm_config()
        parser = ResumeParser(config)

        mock_structured = AsyncMock(return_value="unexpected string")
        parser._model = MagicMock()
        parser._model.with_structured_output.return_value = MagicMock(
            ainvoke=mock_structured
        )

        with pytest.raises(TypeError, match="Unexpected LLM output type"):
            await parser.parse(SAMPLE_RESUME_TEXT)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestParsedResumeEntry:
    def test_defaults(self) -> None:
        entry = ParsedResumeEntry(entry_type="work_experience", title="Engineer")
        assert entry.organization is None
        assert entry.start_date is None
        assert entry.end_date is None
        assert entry.bullet_points == []
        assert entry.tags == []
        assert entry.raw_text is None

    def test_full_entry(self) -> None:
        entry = ParsedResumeEntry(
            entry_type="work_experience",
            title="Senior Engineer",
            organization="BigCo",
            start_date="2020-01",
            end_date="2023-06",
            bullet_points=[
                ParsedBulletPoint(text="Did things", tags=["Python"]),
            ],
            tags=["Python", "AWS"],
            raw_text="Original text...",
        )
        assert entry.title == "Senior Engineer"
        assert len(entry.bullet_points) == 1
        assert entry.bullet_points[0].tags == ["Python"]


# ---------------------------------------------------------------------------
# Integration tests — API endpoint
# ---------------------------------------------------------------------------


class TestParseEndpoint:
    @pytest.mark.asyncio
    async def test_parse_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """POST /parse returns structured entries."""
        mock_entries = MOCK_PARSED_ENTRIES[:1]

        with patch(
            "src.api.career.get_llm_config"
        ) as mock_config_fn:
            mock_config = _mock_llm_config()
            mock_config_fn.return_value = mock_config

            with patch.object(
                ResumeParser,
                "parse",
                new_callable=AsyncMock,
                return_value=mock_entries,
            ):
                resp = await client.post(
                    "/api/v1/career/parse",
                    headers=auth_headers,
                    json={"text": SAMPLE_RESUME_TEXT},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["entry_count"] == 1
        assert len(data["entries"]) == 1
        assert data["entries"][0]["title"] == "Senior Software Engineer"

    @pytest.mark.asyncio
    async def test_parse_empty_text(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """POST /parse rejects empty text."""
        resp = await client.post(
            "/api/v1/career/parse",
            headers=auth_headers,
            json={"text": "   "},
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_parse_requires_auth(self, client: AsyncClient) -> None:
        """POST /parse requires authentication."""
        resp = await client.post(
            "/api/v1/career/parse",
            json={"text": "Some resume text"},
        )
        assert resp.status_code == 403
