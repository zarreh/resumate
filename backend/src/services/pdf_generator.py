"""PDF generator — Jinja2 + LaTeX + tectonic pipeline."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

import jinja2

from src.schemas.resume import EnhancedResume
from src.services.latex_sanitizer import sanitize_for_latex

logger = logging.getLogger(__name__)

# Templates live in backend/templates/latex/
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "latex"

# Jinja2 environment with custom delimiters for LaTeX compatibility
_jinja_env = jinja2.Environment(
    block_start_string=r"\BLOCK{",
    block_end_string="}",
    variable_start_string=r"\VAR{",
    variable_end_string="}",
    comment_start_string=r"\#{",
    comment_end_string="}",
    loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=False,
)

# Register the sanitizer as a Jinja2 filter
_jinja_env.filters["latex_escape"] = sanitize_for_latex


def render_latex(resume: EnhancedResume, template_name: str = "professional") -> str:
    """Render an EnhancedResume to a LaTeX source string.

    Args:
        resume: The enhanced resume data.
        template_name: Name of the template (without extension).

    Returns:
        LaTeX source string ready for compilation.
    """
    template = _jinja_env.get_template(f"{template_name}.tex.j2")
    return template.render(resume=resume, sanitize=sanitize_for_latex)


def compile_pdf(latex_source: str) -> bytes:
    """Compile LaTeX source to PDF using tectonic.

    Args:
        latex_source: Complete LaTeX document source.

    Returns:
        PDF file bytes.

    Raises:
        RuntimeError: If tectonic compilation fails.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = Path(tmpdir) / "resume.tex"
        tex_path.write_text(latex_source, encoding="utf-8")

        result = subprocess.run(
            ["tectonic", str(tex_path), "--untrusted"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            logger.error("Tectonic compilation failed:\n%s", result.stderr)
            msg = f"LaTeX compilation failed: {result.stderr[:500]}"
            raise RuntimeError(msg)

        pdf_path = Path(tmpdir) / "resume.pdf"
        if not pdf_path.exists():
            msg = "PDF output not found after compilation"
            raise RuntimeError(msg)

        return pdf_path.read_bytes()


def generate_pdf(
    resume: EnhancedResume, template_name: str = "professional"
) -> bytes:
    """Full pipeline: render LaTeX from template, compile to PDF.

    Args:
        resume: The enhanced resume data.
        template_name: Name of the template (without extension).

    Returns:
        PDF file bytes.
    """
    latex_source = render_latex(resume, template_name)
    return compile_pdf(latex_source)
