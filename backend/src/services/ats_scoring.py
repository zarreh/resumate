"""ATS (Applicant Tracking System) scoring service.

Primarily deterministic keyword matching with an optional light LLM call
for improvement suggestions.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from src.schemas.job import JDAnalysis
from src.schemas.resume import EnhancedResume


class KeywordMatch(BaseModel):
    """Result of matching a single keyword against the resume."""

    keyword: str
    found: bool
    locations: list[str] = Field(
        default_factory=list,
        description="Where the keyword was found: 'summary', 'bullets', 'skills'",
    )


class ATSScore(BaseModel):
    """Complete ATS scoring result."""

    overall_score: float = Field(ge=0.0, le=100.0, description="Overall ATS score 0-100")
    keyword_score: float = Field(ge=0.0, le=100.0, description="ATS keyword coverage score")
    skills_score: float = Field(ge=0.0, le=100.0, description="Required + preferred skills coverage")
    format_score: float = Field(ge=0.0, le=100.0, description="Format/structure score")
    keyword_matches: list[KeywordMatch] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    format_issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ATSScorer:
    """Deterministic ATS scoring engine."""

    def score(
        self,
        resume: EnhancedResume,
        jd_analysis: JDAnalysis,
    ) -> ATSScore:
        """Score a resume against a JD analysis for ATS compatibility."""
        # Build searchable text corpus from the resume
        corpus = self._build_corpus(resume)

        # Match ATS keywords
        keyword_matches = self._match_keywords(
            jd_analysis.ats_keywords, corpus
        )

        # Match required + preferred skills
        all_skills = list(dict.fromkeys(
            jd_analysis.required_skills
            + jd_analysis.preferred_skills
            + jd_analysis.tech_stack
        ))
        skill_matches = self._match_keywords(all_skills, corpus)

        # Calculate scores
        keyword_score = self._calc_match_score(keyword_matches)
        skills_score = self._calc_weighted_skills_score(
            jd_analysis, corpus
        )
        format_issues = self._check_format(resume)
        format_score = max(0.0, 100.0 - len(format_issues) * 15.0)

        overall_score = (
            keyword_score * 0.40
            + skills_score * 0.45
            + format_score * 0.15
        )

        all_matches = keyword_matches + [
            m for m in skill_matches
            if m.keyword not in {km.keyword for km in keyword_matches}
        ]
        missing = [m.keyword for m in all_matches if not m.found]

        suggestions = self._generate_suggestions(
            missing, format_issues, keyword_score, skills_score
        )

        return ATSScore(
            overall_score=round(overall_score, 1),
            keyword_score=round(keyword_score, 1),
            skills_score=round(skills_score, 1),
            format_score=round(format_score, 1),
            keyword_matches=all_matches,
            missing_keywords=missing,
            format_issues=format_issues,
            suggestions=suggestions,
        )

    def _build_corpus(self, resume: EnhancedResume) -> dict[str, str]:
        """Build searchable text from the resume, keyed by location."""
        bullets_text = []
        for section in resume.sections:
            for entry in section.entries:
                for bullet in entry.bullets:
                    bullets_text.append(bullet.enhanced_text)

        return {
            "summary": resume.summary.lower(),
            "bullets": " ".join(bullets_text).lower(),
            "skills": " ".join(resume.skills).lower(),
        }

    def _match_keywords(
        self, keywords: list[str], corpus: dict[str, str]
    ) -> list[KeywordMatch]:
        """Match keywords against the resume corpus."""
        results = []
        for kw in keywords:
            pattern = re.compile(re.escape(kw.lower()), re.IGNORECASE)
            locations = []
            for loc_name, text in corpus.items():
                if pattern.search(text):
                    locations.append(loc_name)
            results.append(
                KeywordMatch(
                    keyword=kw,
                    found=len(locations) > 0,
                    locations=locations,
                )
            )
        return results

    def _calc_match_score(self, matches: list[KeywordMatch]) -> float:
        """Calculate a simple coverage percentage."""
        if not matches:
            return 100.0
        found = sum(1 for m in matches if m.found)
        return (found / len(matches)) * 100.0

    def _calc_weighted_skills_score(
        self, jd: JDAnalysis, corpus: dict[str, str]
    ) -> float:
        """Calculate weighted skills score (required 60%, preferred 25%, tech 15%)."""
        full_text = " ".join(corpus.values())

        def coverage(skills: list[str]) -> float:
            if not skills:
                return 100.0
            found = sum(
                1 for s in skills if s.lower() in full_text
            )
            return (found / len(skills)) * 100.0

        req = coverage(jd.required_skills)
        pref = coverage(jd.preferred_skills)
        tech = coverage(jd.tech_stack)

        return req * 0.60 + pref * 0.25 + tech * 0.15

    def _check_format(self, resume: EnhancedResume) -> list[str]:
        """Check for common ATS format issues."""
        issues = []

        # Check summary length
        if len(resume.summary.split()) < 20:
            issues.append("Professional summary is too short (< 20 words)")
        if len(resume.summary.split()) > 80:
            issues.append("Professional summary is too long (> 80 words)")

        # Check bullet count
        total_bullets = sum(
            len(bullet.enhanced_text.split())
            for s in resume.sections
            for e in s.entries
            for bullet in e.bullets
        )
        bullet_count = sum(
            len(e.bullets)
            for s in resume.sections
            for e in s.entries
        )
        if bullet_count > 0:
            avg_words = total_bullets / bullet_count
            if avg_words < 8:
                issues.append("Average bullet length is very short (< 8 words)")
            if avg_words > 30:
                issues.append("Average bullet length is very long (> 30 words)")

        # Check skills section
        if len(resume.skills) < 5:
            issues.append("Skills section has fewer than 5 skills")

        # Check for empty sections
        for section in resume.sections:
            if not section.entries:
                issues.append(f"Section '{section.title}' has no entries")

        return issues

    def _generate_suggestions(
        self,
        missing_keywords: list[str],
        format_issues: list[str],
        keyword_score: float,
        skills_score: float,
    ) -> list[str]:
        """Generate actionable suggestions based on scoring results."""
        suggestions = []

        if missing_keywords:
            top_missing = missing_keywords[:5]
            suggestions.append(
                f"Add missing keywords to your resume: {', '.join(top_missing)}"
            )

        if keyword_score < 60:
            suggestions.append(
                "Keyword coverage is low — consider mirroring more language from the job description"
            )

        if skills_score < 60:
            suggestions.append(
                "Skills match is below average — ensure all relevant skills are listed explicitly"
            )

        for issue in format_issues:
            suggestions.append(f"Format: {issue}")

        return suggestions
