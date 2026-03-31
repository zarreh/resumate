"""Tests for the ATS scoring service and endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from src.schemas.job import JDAnalysis
from src.schemas.resume import (
    EnhancedBullet,
    EnhancedResume,
    ResumeSection,
    ResumeSectionEntry,
)
from src.services.ats_scoring import ATSScore, ATSScorer, KeywordMatch

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_ANALYSIS = JDAnalysis(
    role_title="Senior Backend Engineer",
    company_name="Acme Corp",
    seniority_level="senior",
    industry="marketplace",
    required_skills=["Python", "FastAPI", "PostgreSQL"],
    preferred_skills=["GraphQL", "Redis"],
    ats_keywords=["Backend Engineer", "Python", "API", "microservices"],
    tech_stack=["Python", "FastAPI", "PostgreSQL", "Docker"],
    responsibilities=["Design APIs"],
    qualifications=["5+ years"],
    domain_expectations=["E-commerce"],
)

SAMPLE_RESUME = EnhancedResume(
    summary="Senior Backend Engineer with 4+ years building scalable APIs using Python and FastAPI for microservices architectures.",
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
                            enhanced_text="Designed and implemented RESTful APIs using Python and FastAPI, serving 10K+ requests/min with PostgreSQL backend",
                            source_entry_id="entry-1",
                            relevance_score=0.92,
                        ),
                        EnhancedBullet(
                            id="0_1",
                            original_text="Wrote unit tests",
                            enhanced_text="Developed comprehensive test suite with Docker containerization achieving 95% code coverage",
                            source_entry_id="entry-1",
                            relevance_score=0.75,
                        ),
                    ],
                ),
            ],
        ),
    ],
    skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
)


# Resume with few skills and short summary for testing format issues
SPARSE_RESUME = EnhancedResume(
    summary="Backend developer.",
    sections=[
        ResumeSection(
            id="sec_0",
            section_type="experience",
            title="Experience",
            entries=[
                ResumeSectionEntry(
                    entry_id="entry-1",
                    title="Dev",
                    bullets=[
                        EnhancedBullet(
                            id="0_0",
                            original_text="Coded",
                            enhanced_text="Coded things",
                            source_entry_id="entry-1",
                            relevance_score=0.5,
                        ),
                    ],
                ),
            ],
        ),
    ],
    skills=["Python"],
)


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestATSScorer:
    """Test the ATSScorer service."""

    def test_score_returns_ats_score(self) -> None:
        scorer = ATSScorer()
        result = scorer.score(SAMPLE_RESUME, SAMPLE_ANALYSIS)
        assert isinstance(result, ATSScore)
        assert 0 <= result.overall_score <= 100
        assert 0 <= result.keyword_score <= 100
        assert 0 <= result.skills_score <= 100
        assert 0 <= result.format_score <= 100

    def test_keyword_matching(self) -> None:
        scorer = ATSScorer()
        result = scorer.score(SAMPLE_RESUME, SAMPLE_ANALYSIS)
        # Python and API should be found
        found_kws = {m.keyword for m in result.keyword_matches if m.found}
        assert "Python" in found_kws
        assert "API" in found_kws

    def test_missing_keywords_reported(self) -> None:
        scorer = ATSScorer()
        # Use a resume that doesn't mention GraphQL
        result = scorer.score(SAMPLE_RESUME, SAMPLE_ANALYSIS)
        assert "GraphQL" in result.missing_keywords

    def test_skills_in_skills_section_matched(self) -> None:
        scorer = ATSScorer()
        result = scorer.score(SAMPLE_RESUME, SAMPLE_ANALYSIS)
        # Redis is in skills list
        redis_matches = [m for m in result.keyword_matches if m.keyword == "Redis"]
        assert len(redis_matches) == 1
        assert redis_matches[0].found
        assert "skills" in redis_matches[0].locations

    def test_format_issues_detected(self) -> None:
        scorer = ATSScorer()
        result = scorer.score(SPARSE_RESUME, SAMPLE_ANALYSIS)
        assert len(result.format_issues) > 0
        issue_text = " ".join(result.format_issues)
        assert "summary" in issue_text.lower() or "skills" in issue_text.lower()

    def test_suggestions_generated_for_missing(self) -> None:
        scorer = ATSScorer()
        result = scorer.score(SPARSE_RESUME, SAMPLE_ANALYSIS)
        assert len(result.suggestions) > 0

    def test_high_score_for_good_resume(self) -> None:
        scorer = ATSScorer()
        result = scorer.score(SAMPLE_RESUME, SAMPLE_ANALYSIS)
        # A well-matched resume should score reasonably well
        assert result.overall_score > 50

    def test_low_score_for_sparse_resume(self) -> None:
        scorer = ATSScorer()
        result = scorer.score(SPARSE_RESUME, SAMPLE_ANALYSIS)
        # A sparse resume should score lower
        assert result.overall_score < result.keyword_score or result.format_score < 100

    def test_location_tracking(self) -> None:
        scorer = ATSScorer()
        result = scorer.score(SAMPLE_RESUME, SAMPLE_ANALYSIS)
        python_match = [m for m in result.keyword_matches if m.keyword == "Python"][0]
        # Python appears in summary, bullets, and skills
        assert "summary" in python_match.locations
        assert "skills" in python_match.locations

    def test_empty_keywords_full_score(self) -> None:
        """Empty keyword list should give 100% keyword score."""
        empty_jd = JDAnalysis(
            role_title="Dev",
            seniority_level="mid",
            industry="tech",
            ats_keywords=[],
            required_skills=[],
            preferred_skills=[],
            tech_stack=[],
        )
        scorer = ATSScorer()
        result = scorer.score(SAMPLE_RESUME, empty_jd)
        assert result.keyword_score == 100.0


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestATSSchemas:
    """Test ATS schema validation."""

    def test_keyword_match_valid(self) -> None:
        km = KeywordMatch(keyword="Python", found=True, locations=["skills"])
        assert km.found
        assert km.locations == ["skills"]

    def test_ats_score_bounds(self) -> None:
        score = ATSScore(
            overall_score=75.0,
            keyword_score=80.0,
            skills_score=70.0,
            format_score=90.0,
        )
        assert score.overall_score == 75.0

    def test_ats_score_invalid_range(self) -> None:
        with pytest.raises(Exception):
            ATSScore(
                overall_score=150.0,  # Out of range
                keyword_score=80.0,
                skills_score=70.0,
                format_score=90.0,
            )


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestATSScoreEndpoint:
    """Tests for the POST /sessions/{id}/ats-score endpoint."""

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

    async def test_ats_score_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /sessions/{id}/ats-score returns scoring results."""
        with patch("src.api.sessions.get_llm_config") as mock_config:
            mock_config.return_value = MagicMock()
            session_id = await self._create_session_with_resume(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sessions/{session_id}/ats-score",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert "overall_score" in data["score"]
        assert "keyword_matches" in data["score"]
        assert "missing_keywords" in data["score"]

    async def test_ats_score_no_session(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Returns 404 for unknown session."""
        import uuid

        resp = await client.post(
            f"/api/v1/sessions/{uuid.uuid4()}/ats-score",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_ats_score_no_resume(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Returns 400 when no enhanced resume exists."""
        with patch("src.api.sessions.get_llm_config") as mock_config:
            mock_config.return_value = MagicMock()

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
            f"/api/v1/sessions/{session_id}/ats-score",
            headers=auth_headers,
        )
        assert resp.status_code == 400
