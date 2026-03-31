"""Match scoring service — calculates how well career entries match a JD."""

from __future__ import annotations

from src.schemas.job import JDAnalysis
from src.schemas.matching import GapAnalysis, MatchResult, RankedEntry, SkillMatch


def _normalize(s: str) -> str:
    """Normalize a string for case-insensitive comparison."""
    return s.lower().strip()


def _skill_matches(
    skills: list[str], entry_tags: set[str]
) -> tuple[list[SkillMatch], int]:
    """Check which skills are matched by any entry tag."""
    matches: list[SkillMatch] = []
    matched_count = 0

    for skill in skills:
        norm_skill = _normalize(skill)
        matched_by = [t for t in entry_tags if _normalize(t) == norm_skill]

        # Also check partial matches (e.g., "React" matches "React.js")
        if not matched_by:
            matched_by = [
                t
                for t in entry_tags
                if norm_skill in _normalize(t) or _normalize(t) in norm_skill
            ]

        is_matched = len(matched_by) > 0
        if is_matched:
            matched_count += 1

        matches.append(
            SkillMatch(skill=skill, matched=is_matched, matched_by=matched_by)
        )

    return matches, matched_count


def _pct(matched: int, total: int) -> float:
    """Calculate percentage, return 100 if total is 0."""
    if total == 0:
        return 100.0
    return round(matched / total * 100, 1)


class MatchScorer:
    """Scores how well a set of career entries match a job description analysis."""

    def score(
        self,
        jd_analysis: JDAnalysis,
        entries: list[RankedEntry],
    ) -> MatchResult:
        """Compute match scores and gap analysis."""
        # Collect all tags from all entries
        all_tags: set[str] = set()
        for entry in entries:
            all_tags.update(entry.tags)

        # Also include bullet text keywords (entry titles, orgs)
        all_text_lower: set[str] = set()
        for entry in entries:
            all_text_lower.add(_normalize(entry.title))
            if entry.organization:
                all_text_lower.add(_normalize(entry.organization))
            for bp in entry.bullet_points:
                all_text_lower.add(_normalize(bp))

        # Score required skills
        required_matches, required_count = _skill_matches(
            jd_analysis.required_skills, all_tags
        )

        # Score preferred skills
        preferred_matches, preferred_count = _skill_matches(
            jd_analysis.preferred_skills, all_tags
        )

        # Score tech stack
        tech_matches, tech_count = _skill_matches(
            jd_analysis.tech_stack, all_tags
        )

        # Calculate percentages
        req_score = _pct(required_count, len(jd_analysis.required_skills))
        pref_score = _pct(preferred_count, len(jd_analysis.preferred_skills))
        tech_score = _pct(tech_count, len(jd_analysis.tech_stack))

        # Overall: weighted average (required 50%, tech 30%, preferred 20%)
        overall = round(req_score * 0.5 + tech_score * 0.3 + pref_score * 0.2, 1)

        # Gap analysis
        gap = GapAnalysis(
            unmatched_required=[m.skill for m in required_matches if not m.matched],
            unmatched_preferred=[m.skill for m in preferred_matches if not m.matched],
            missing_tech=[m.skill for m in tech_matches if not m.matched],
        )

        # Recommended section order based on JD emphasis
        section_order = self._recommend_section_order(jd_analysis, entries)

        return MatchResult(
            overall_score=overall,
            required_skills_score=req_score,
            preferred_skills_score=pref_score,
            tech_stack_score=tech_score,
            required_matches=required_matches,
            preferred_matches=preferred_matches,
            tech_matches=tech_matches,
            gap_analysis=gap,
            recommended_section_order=section_order,
        )

    def _recommend_section_order(
        self,
        jd_analysis: JDAnalysis,
        entries: list[RankedEntry],
    ) -> list[str]:
        """Recommend resume section ordering based on JD and available entries."""
        # Count entries by type
        type_counts: dict[str, int] = {}
        for entry in entries:
            type_counts[entry.entry_type] = type_counts.get(entry.entry_type, 0) + 1

        # Default ordering
        sections = ["summary"]

        # If JD emphasizes technical skills and we have work experience, lead with experience
        has_work = type_counts.get("work_experience", 0) > 0
        has_projects = type_counts.get("project", 0) > 0
        has_education = type_counts.get("education", 0) > 0

        # For senior/lead/principal roles, experience first
        senior_levels = {"senior", "staff", "lead", "principal", "director", "vp", "c-level"}
        is_senior = _normalize(jd_analysis.seniority_level) in senior_levels

        if is_senior and has_work:
            sections.append("experience")
            sections.append("skills")
            if has_projects:
                sections.append("projects")
            if has_education:
                sections.append("education")
        elif has_education and not has_work:
            # Fresh grad: education first
            sections.append("education")
            if has_projects:
                sections.append("projects")
            sections.append("skills")
        else:
            # Default: experience, skills, projects, education
            if has_work:
                sections.append("experience")
            sections.append("skills")
            if has_projects:
                sections.append("projects")
            if has_education:
                sections.append("education")

        return sections
