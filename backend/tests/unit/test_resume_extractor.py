"""Tests for resume upload and text extraction (Phase 2.1)."""

from __future__ import annotations

from io import BytesIO

import pymupdf
import pytest
from docx import Document
from httpx import AsyncClient

from src.services.resume_extractor import (
    ExtractionError,
    FileTooLargeError,
    ResumeExtractor,
    UnsupportedFileTypeError,
)

# ---------------------------------------------------------------------------
# Helpers — generate sample files in memory
# ---------------------------------------------------------------------------

SAMPLE_TEXT = (
    "John Doe\n"
    "Software Engineer\n\n"
    "Experience\n"
    "- Built scalable APIs at Acme Corp (2020-2023)\n"
    "- Led migration to microservices architecture\n\n"
    "Education\n"
    "- B.S. Computer Science, MIT, 2019"
)


def _make_pdf(text: str = SAMPLE_TEXT) -> bytes:
    """Create a minimal PDF with the given text."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _make_docx(text: str = SAMPLE_TEXT) -> bytes:
    """Create a minimal DOCX with the given text."""
    doc = Document()
    for line in text.split("\n"):
        if line.strip():
            doc.add_paragraph(line)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Unit tests — ResumeExtractor
# ---------------------------------------------------------------------------


class TestResumeExtractorPDF:
    def test_extract_pdf_basic(self) -> None:
        extractor = ResumeExtractor()
        pdf_bytes = _make_pdf()
        result = extractor.extract(pdf_bytes, "application/pdf")
        assert "John Doe" in result
        assert "Software Engineer" in result
        assert "microservices" in result

    def test_extract_pdf_preserves_structure(self) -> None:
        extractor = ResumeExtractor()
        pdf_bytes = _make_pdf()
        result = extractor.extract(pdf_bytes, "application/pdf")
        # Bullet points should be preserved
        assert "Built scalable APIs" in result
        assert "Led migration" in result

    def test_extract_pdf_sort_enabled(self) -> None:
        """The extractor uses sort=True for better column handling."""
        extractor = ResumeExtractor()
        pdf_bytes = _make_pdf("Column A\nColumn B")
        result = extractor.extract(pdf_bytes, "application/pdf")
        assert "Column A" in result
        assert "Column B" in result

    def test_extract_pdf_corrupt_data(self) -> None:
        extractor = ResumeExtractor()
        with pytest.raises(ExtractionError, match="Failed to parse PDF"):
            extractor.extract(b"not a pdf", "application/pdf")


class TestResumeExtractorDOCX:
    def test_extract_docx_basic(self) -> None:
        extractor = ResumeExtractor()
        docx_bytes = _make_docx()
        result = extractor.extract(docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        assert "John Doe" in result
        assert "Software Engineer" in result
        assert "microservices" in result

    def test_extract_docx_preserves_paragraphs(self) -> None:
        extractor = ResumeExtractor()
        docx_bytes = _make_docx()
        result = extractor.extract(docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        assert "Built scalable APIs" in result
        assert "B.S. Computer Science" in result

    def test_extract_docx_corrupt_data(self) -> None:
        extractor = ResumeExtractor()
        with pytest.raises(ExtractionError, match="Failed to parse DOCX"):
            extractor.extract(b"not a docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


class TestResumeExtractorTXT:
    def test_extract_txt_utf8(self) -> None:
        extractor = ResumeExtractor()
        result = extractor.extract(SAMPLE_TEXT.encode("utf-8"), "text/plain")
        assert result == SAMPLE_TEXT

    def test_extract_txt_latin1(self) -> None:
        extractor = ResumeExtractor()
        # Latin-1 string with accented chars that aren't valid UTF-8 sequences
        text = "R\xe9sum\xe9 - Jos\xe9 Garc\xeda"
        raw = text.encode("latin-1")
        # This should fail UTF-8 and fall back to latin-1
        result = extractor.extract(raw, "text/plain")
        assert "sum" in result

    def test_extract_txt_empty(self) -> None:
        extractor = ResumeExtractor()
        with pytest.raises(ExtractionError, match="Text file is empty"):
            extractor.extract(b"   \n  ", "text/plain")


class TestResumeExtractorValidation:
    def test_unsupported_content_type(self) -> None:
        extractor = ResumeExtractor()
        with pytest.raises(UnsupportedFileTypeError, match="Unsupported file type"):
            extractor.extract(b"data", "image/png")

    def test_file_too_large(self) -> None:
        extractor = ResumeExtractor()
        large_bytes = b"x" * (11 * 1024 * 1024)  # 11 MB
        with pytest.raises(FileTooLargeError, match="exceeds maximum size"):
            extractor.extract(large_bytes, "text/plain")


# ---------------------------------------------------------------------------
# Integration tests — API endpoint
# ---------------------------------------------------------------------------


class TestImportEndpoint:
    @pytest.mark.asyncio
    async def test_upload_pdf(self, client: AsyncClient, auth_headers: dict[str, str]) -> None:
        pdf_bytes = _make_pdf()
        resp = await client.post(
            "/api/v1/career/import",
            headers=auth_headers,
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "resume.pdf"
        assert data["content_type"] == "application/pdf"
        assert "John Doe" in data["text"]
        assert data["char_count"] > 0

    @pytest.mark.asyncio
    async def test_upload_docx(self, client: AsyncClient, auth_headers: dict[str, str]) -> None:
        docx_bytes = _make_docx()
        resp = await client.post(
            "/api/v1/career/import",
            headers=auth_headers,
            files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "resume.docx"
        assert "John Doe" in data["text"]

    @pytest.mark.asyncio
    async def test_upload_txt(self, client: AsyncClient, auth_headers: dict[str, str]) -> None:
        resp = await client.post(
            "/api/v1/career/import",
            headers=auth_headers,
            files={"file": ("resume.txt", SAMPLE_TEXT.encode(), "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "resume.txt"
        assert data["text"] == SAMPLE_TEXT

    @pytest.mark.asyncio
    async def test_upload_unsupported_type(self, client: AsyncClient, auth_headers: dict[str, str]) -> None:
        resp = await client.post(
            "/api/v1/career/import",
            headers=auth_headers,
            files={"file": ("photo.png", b"fake-image", "image/png")},
        )
        assert resp.status_code == 400
        assert "Unsupported file type" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_requires_auth(self, client: AsyncClient) -> None:
        pdf_bytes = _make_pdf()
        resp = await client.post(
            "/api/v1/career/import",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 403
