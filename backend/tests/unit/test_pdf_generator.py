"""Tests for LaTeX sanitizer, PDF generator, and resume PDF endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from src.schemas.job import JDAnalysis
from src.schemas.matching import GapAnalysis, MatchResult, SkillMatch
from src.schemas.resume import (
    EnhancedBullet,
    EnhancedResume,
    ResumeSection,
    ResumeSectionEntry,
)
from src.services.latex_sanitizer import sanitize_for_latex

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_ANALYSIS = JDAnalysis(
    role_title="Backend Engineer",
    company_name="TestCo",
    seniority_level="mid",
    industry="tech",
    required_skills=["Python"],
    preferred_skills=[],
    ats_keywords=["Python"],
    tech_stack=["Python"],
    responsibilities=["Build APIs"],
    qualifications=["3+ years"],
    domain_expectations=[],
)

SAMPLE_RESUME = EnhancedResume(
    summary="Experienced backend engineer with Python expertise.",
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
                            original_text="Built APIs",
                            enhanced_text="Designed and implemented RESTful APIs using Python & FastAPI",
                            source_entry_id="entry-1",
                            relevance_score=0.95,
                        ),
                    ],
                )
            ],
        ),
    ],
    skills=["Python", "FastAPI", "PostgreSQL"],
    metadata={"total_bullets": 1},
)


# ---------------------------------------------------------------------------
# LaTeX sanitizer tests
# ---------------------------------------------------------------------------


class TestLatexSanitizer:
    """Tests for the sanitize_for_latex function."""

    def test_ampersand(self) -> None:
        assert sanitize_for_latex("AT&T") == r"AT\&T"

    def test_percent(self) -> None:
        assert sanitize_for_latex("100%") == r"100\%"

    def test_dollar(self) -> None:
        assert sanitize_for_latex("$50") == r"\$50"

    def test_hash(self) -> None:
        assert sanitize_for_latex("#1") == r"\#1"

    def test_underscore(self) -> None:
        assert sanitize_for_latex("my_var") == r"my\_var"

    def test_curly_braces(self) -> None:
        assert sanitize_for_latex("{test}") == r"\{test\}"

    def test_tilde(self) -> None:
        assert sanitize_for_latex("~") == r"\textasciitilde{}"

    def test_caret(self) -> None:
        assert sanitize_for_latex("^") == r"\textasciicircum{}"

    def test_backslash_first(self) -> None:
        # Backslash must be escaped before other chars to avoid double-escaping
        result = sanitize_for_latex("\\")
        assert result == r"\textbackslash{}"

    def test_mixed_special_chars(self) -> None:
        result = sanitize_for_latex("C++ & Python at $company")
        assert r"\&" in result
        assert r"\$" in result

    def test_no_special_chars(self) -> None:
        text = "Plain text without special characters"
        assert sanitize_for_latex(text) == text

    def test_unicode_passthrough(self) -> None:
        # Unicode should pass through unchanged
        assert sanitize_for_latex("résumé") == "résumé"


# ---------------------------------------------------------------------------
# LaTeX rendering tests
# ---------------------------------------------------------------------------


class TestRenderLatex:
    """Tests for the render_latex function."""

    def test_render_produces_latex(self) -> None:
        from src.services.pdf_generator import render_latex

        result = render_latex(SAMPLE_RESUME, "professional")
        assert r"\documentclass" in result
        assert r"\begin{document}" in result
        assert r"\end{document}" in result

    def test_render_includes_summary(self) -> None:
        from src.services.pdf_generator import render_latex

        result = render_latex(SAMPLE_RESUME, "professional")
        assert "Experienced backend engineer" in result

    def test_render_includes_section(self) -> None:
        from src.services.pdf_generator import render_latex

        result = render_latex(SAMPLE_RESUME, "professional")
        assert "Professional Experience" in result
        assert "Backend Developer" in result
        assert "TechCo" in result

    def test_render_includes_skills(self) -> None:
        from src.services.pdf_generator import render_latex

        result = render_latex(SAMPLE_RESUME, "professional")
        assert "Python" in result
        assert "FastAPI" in result

    def test_render_escapes_special_chars(self) -> None:
        from src.services.pdf_generator import render_latex

        resume = SAMPLE_RESUME.model_copy(deep=True)
        resume.sections[0].entries[0].bullets[0].enhanced_text = (
            "Used C++ & Python at $10M company"
        )
        result = render_latex(resume, "professional")
        assert r"\&" in result
        assert r"\$" in result

    def test_render_empty_resume(self) -> None:
        from src.services.pdf_generator import render_latex

        empty = EnhancedResume(
            summary="", sections=[], skills=[], metadata={}
        )
        result = render_latex(empty, "professional")
        assert r"\begin{document}" in result
        assert r"\end{document}" in result

    def test_render_invalid_template(self) -> None:
        from src.services.pdf_generator import render_latex

        with pytest.raises(Exception):
            render_latex(SAMPLE_RESUME, "nonexistent")


# ---------------------------------------------------------------------------
# PDF compilation tests (mocked)
# ---------------------------------------------------------------------------


class TestCompilePdf:
    """Tests for the compile_pdf function (tectonic mocked)."""

    @patch("src.services.pdf_generator.subprocess.run")
    def test_compile_success(self, mock_run: MagicMock, tmp_path: object) -> None:
        from src.services.pdf_generator import compile_pdf

        # Mock successful tectonic run
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        # We need to mock the PDF file existing after compilation
        with patch("src.services.pdf_generator.Path") as mock_path_cls:
            # Make tempfile work normally, but mock the PDF path check
            import tempfile
            from pathlib import Path as RealPath

            # Use a real temp dir but mock the PDF read
            with tempfile.TemporaryDirectory() as tmpdir:
                mock_path_cls.side_effect = lambda *args: RealPath(*args)

                # Create a fake PDF file where tectonic would
                fake_pdf = RealPath(tmpdir) / "resume.pdf"
                fake_pdf.write_bytes(b"%PDF-1.4 fake content")

                # Patch to use our tmpdir
                with patch("tempfile.TemporaryDirectory") as mock_tempdir:
                    mock_tempdir.return_value.__enter__ = MagicMock(
                        return_value=tmpdir
                    )
                    mock_tempdir.return_value.__exit__ = MagicMock(
                        return_value=False
                    )

                    result = compile_pdf(r"\documentclass{article}\begin{document}Hello\end{document}")
                    assert result == b"%PDF-1.4 fake content"

    @patch("src.services.pdf_generator.subprocess.run")
    def test_compile_failure(self, mock_run: MagicMock) -> None:
        from src.services.pdf_generator import compile_pdf

        mock_run.return_value = MagicMock(
            returncode=1, stderr="! Undefined control sequence."
        )

        with pytest.raises(RuntimeError, match="LaTeX compilation failed"):
            compile_pdf(r"\documentclass{article}\begin{document}\invalid\end{document}")


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestResumeEndpoints:
    """Tests for the resumes API endpoints."""

    async def _create_session_with_resume(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> str:
        """Helper: create a session and store a resume on it."""
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
                mock_ret = MagicMock()
                mock_ret.embed_job_description = AsyncMock()
                mock_ret.embed_all_entries = AsyncMock()
                mock_ret.find_relevant_entries = AsyncMock(return_value=[])
                mock_ret_cls.return_value = mock_ret
                mock_sc = MagicMock()
                mock_sc.score.return_value = MatchResult(
                    overall_score=0,
                    required_skills_score=0,
                    preferred_skills_score=0,
                    tech_stack_score=0,
                    required_matches=[],
                    preferred_matches=[],
                    tech_matches=[],
                    gap_analysis=GapAnalysis(
                        unmatched_required=[],
                        unmatched_preferred=[],
                        missing_tech=[],
                    ),
                    recommended_section_order=[],
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

    async def test_render_latex(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /resumes/{id}/render returns LaTeX source."""
        session_id = await self._create_session_with_resume(client, auth_headers)

        resp = await client.post(
            f"/api/v1/resumes/{session_id}/render",
            json={"template_name": "professional"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert r"\documentclass" in data["latex_source"]
        assert "Backend Developer" in data["latex_source"]

    @patch("src.api.resumes.generate_pdf")
    async def test_download_pdf(
        self,
        mock_gen: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /resumes/{id}/pdf returns PDF bytes."""
        mock_gen.return_value = b"%PDF-1.4 test content"

        session_id = await self._create_session_with_resume(client, auth_headers)

        resp = await client.get(
            f"/api/v1/resumes/{session_id}/pdf",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content == b"%PDF-1.4 test content"

    async def test_render_no_resume(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /resumes/{id}/render returns 400 when no resume exists."""
        # Create session without generating resume
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
            f"/api/v1/resumes/{session_id}/render",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    async def test_render_session_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /resumes/{id}/render returns 404 for unknown session."""
        import uuid

        resp = await client.post(
            f"/api/v1/resumes/{uuid.uuid4()}/render",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 404
