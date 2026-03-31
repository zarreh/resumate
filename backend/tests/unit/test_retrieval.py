"""Tests for retrieval service and match scoring."""

from __future__ import annotations

import pytest

from src.schemas.job import JDAnalysis
from src.schemas.matching import RankedEntry
from src.services.match_scoring import MatchScorer

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_ANALYSIS = JDAnalysis(
    role_title="Senior Backend Engineer",
    company_name="Acme Corp",
    seniority_level="senior",
    industry="marketplace",
    required_skills=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker"],
    preferred_skills=["Kubernetes", "GraphQL", "AWS"],
    ats_keywords=["Backend Engineer", "Python", "microservices"],
    tech_stack=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Kubernetes"],
    responsibilities=["Design APIs", "Optimize databases"],
    qualifications=["5+ years experience"],
    domain_expectations=[],
)


def _make_entry(
    entry_id: str = "entry-1",
    entry_type: str = "work_experience",
    title: str = "Software Engineer",
    organization: str | None = "TechCo",
    tags: list[str] | None = None,
    bullet_points: list[str] | None = None,
) -> RankedEntry:
    return RankedEntry(
        entry_id=entry_id,
        entry_type=entry_type,
        title=title,
        organization=organization,
        start_date="2020-01-01",
        end_date=None,
        bullet_points=bullet_points or ["Built APIs", "Managed databases"],
        tags=tags or ["Python", "FastAPI", "PostgreSQL"],
        source="user_provided",
        similarity_score=0.85,
    )


# ---------------------------------------------------------------------------
# MatchScorer tests
# ---------------------------------------------------------------------------


class TestMatchScorer:
    """Tests for the MatchScorer service."""

    def test_full_match(self) -> None:
        """All skills matched gives high score."""
        entries = [
            _make_entry(
                tags=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Kubernetes", "GraphQL", "AWS"]
            ),
        ]
        scorer = MatchScorer()
        result = scorer.score(SAMPLE_ANALYSIS, entries)

        assert result.required_skills_score == 100.0
        assert result.preferred_skills_score == 100.0
        assert result.tech_stack_score == 100.0
        assert result.overall_score == 100.0
        assert len(result.gap_analysis.unmatched_required) == 0

    def test_partial_match(self) -> None:
        """Some skills matched gives partial score."""
        entries = [_make_entry(tags=["Python", "FastAPI", "PostgreSQL"])]
        scorer = MatchScorer()
        result = scorer.score(SAMPLE_ANALYSIS, entries)

        assert 0 < result.required_skills_score < 100
        assert result.overall_score < 100
        assert len(result.gap_analysis.unmatched_required) > 0
        assert "Redis" in result.gap_analysis.unmatched_required
        assert "Docker" in result.gap_analysis.unmatched_required

    def test_no_match(self) -> None:
        """No skills matched gives low score."""
        entries = [_make_entry(tags=["Java", "Spring", "MySQL"])]
        scorer = MatchScorer()
        result = scorer.score(SAMPLE_ANALYSIS, entries)

        assert result.required_skills_score == 0.0
        assert result.overall_score == 0.0
        assert len(result.gap_analysis.unmatched_required) == 5

    def test_empty_entries(self) -> None:
        """No entries gives zero scores."""
        scorer = MatchScorer()
        result = scorer.score(SAMPLE_ANALYSIS, [])

        assert result.required_skills_score == 0.0
        assert result.overall_score == 0.0

    def test_empty_jd_skills(self) -> None:
        """JD with no skills gives 100% (nothing to match)."""
        empty_analysis = JDAnalysis(
            role_title="Generic Role",
            seniority_level="mid",
            industry="tech",
        )
        entries = [_make_entry()]
        scorer = MatchScorer()
        result = scorer.score(empty_analysis, entries)

        assert result.required_skills_score == 100.0
        assert result.overall_score == 100.0

    def test_case_insensitive_matching(self) -> None:
        """Skills are matched case-insensitively."""
        entries = [_make_entry(tags=["python", "fastapi", "postgresql", "redis", "docker"])]
        scorer = MatchScorer()
        result = scorer.score(SAMPLE_ANALYSIS, entries)

        assert result.required_skills_score == 100.0

    def test_partial_string_matching(self) -> None:
        """Partial matches work (e.g., 'React' matches 'React.js')."""
        jd = JDAnalysis(
            role_title="Frontend Engineer",
            seniority_level="mid",
            industry="tech",
            required_skills=["React"],
            tech_stack=["React"],
        )
        entries = [_make_entry(tags=["React.js", "TypeScript"])]
        scorer = MatchScorer()
        result = scorer.score(jd, entries)

        assert result.required_skills_score == 100.0

    def test_multiple_entries_combine_tags(self) -> None:
        """Tags from multiple entries are combined for matching."""
        entries = [
            _make_entry(entry_id="1", tags=["Python", "FastAPI"]),
            _make_entry(entry_id="2", tags=["PostgreSQL", "Redis", "Docker"]),
        ]
        scorer = MatchScorer()
        result = scorer.score(SAMPLE_ANALYSIS, entries)

        assert result.required_skills_score == 100.0

    def test_gap_analysis_structure(self) -> None:
        """Gap analysis contains correct unmatched items."""
        entries = [_make_entry(tags=["Python", "Django"])]
        scorer = MatchScorer()
        result = scorer.score(SAMPLE_ANALYSIS, entries)

        gap = result.gap_analysis
        assert "FastAPI" in gap.unmatched_required
        assert "PostgreSQL" in gap.unmatched_required
        assert isinstance(gap.missing_tech, list)

    def test_skill_match_details(self) -> None:
        """SkillMatch objects contain correct match details."""
        entries = [_make_entry(tags=["Python", "FastAPI"])]
        scorer = MatchScorer()
        result = scorer.score(SAMPLE_ANALYSIS, entries)

        python_match = next(m for m in result.required_matches if m.skill == "Python")
        assert python_match.matched is True
        assert "Python" in python_match.matched_by

        redis_match = next(m for m in result.required_matches if m.skill == "Redis")
        assert redis_match.matched is False


class TestSectionOrder:
    """Tests for section order recommendation."""

    def test_senior_role_experience_first(self) -> None:
        """Senior roles recommend experience before skills."""
        entries = [
            _make_entry(entry_type="work_experience"),
            _make_entry(entry_id="2", entry_type="education"),
        ]
        scorer = MatchScorer()
        result = scorer.score(SAMPLE_ANALYSIS, entries)

        order = result.recommended_section_order
        assert "summary" in order
        assert order.index("experience") < order.index("education")

    def test_fresh_grad_education_first(self) -> None:
        """Without work experience, education comes first."""
        jd = JDAnalysis(
            role_title="Junior Developer",
            seniority_level="junior",
            industry="tech",
        )
        entries = [
            _make_entry(entry_id="1", entry_type="education"),
            _make_entry(entry_id="2", entry_type="project"),
        ]
        scorer = MatchScorer()
        result = scorer.score(jd, entries)

        order = result.recommended_section_order
        assert order.index("education") < order.index("projects")

    def test_with_projects(self) -> None:
        """Projects appear in recommended order when present."""
        entries = [
            _make_entry(entry_type="work_experience"),
            _make_entry(entry_id="2", entry_type="project"),
        ]
        scorer = MatchScorer()
        result = scorer.score(SAMPLE_ANALYSIS, entries)

        assert "projects" in result.recommended_section_order


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestMatchSchemas:
    """Tests for matching schemas."""

    def test_ranked_entry_serialization(self) -> None:
        entry = _make_entry()
        data = entry.model_dump()
        restored = RankedEntry.model_validate(data)
        assert restored.entry_id == "entry-1"
        assert restored.similarity_score == pytest.approx(0.85)

    def test_match_result_serialization(self) -> None:
        """MatchResult serializes and deserializes correctly."""
        scorer = MatchScorer()
        result = scorer.score(SAMPLE_ANALYSIS, [_make_entry()])

        data = result.model_dump()
        from src.schemas.matching import MatchResult

        restored = MatchResult.model_validate(data)
        assert restored.overall_score == result.overall_score
        assert len(restored.required_matches) == len(result.required_matches)
