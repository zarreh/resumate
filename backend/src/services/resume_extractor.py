"""Resume text extraction from PDF, DOCX, and plain text files."""

from __future__ import annotations

from io import BytesIO

import pymupdf
from docx import Document

SUPPORTED_CONTENT_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


class UnsupportedFileTypeError(Exception):
    """Raised when the uploaded file type is not supported."""


class FileTooLargeError(Exception):
    """Raised when the uploaded file exceeds the size limit."""


class ExtractionError(Exception):
    """Raised when text extraction fails."""


class ResumeExtractor:
    """Extracts raw text from resume files."""

    def extract(self, file_bytes: bytes, content_type: str) -> str:
        """Extract text from file bytes based on content type.

        Returns the extracted text with paragraph structure preserved.
        """
        fmt = SUPPORTED_CONTENT_TYPES.get(content_type)
        if fmt is None:
            msg = (
                f"Unsupported file type: {content_type}. "
                f"Supported types: {', '.join(SUPPORTED_CONTENT_TYPES)}"
            )
            raise UnsupportedFileTypeError(msg)

        if len(file_bytes) > MAX_UPLOAD_BYTES:
            msg = f"File exceeds maximum size of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB"
            raise FileTooLargeError(msg)

        if fmt == "pdf":
            return self._extract_pdf(file_bytes)
        if fmt == "docx":
            return self._extract_docx(file_bytes)
        return self._extract_txt(file_bytes)

    def _extract_pdf(self, file_bytes: bytes) -> str:
        try:
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        except Exception as exc:
            msg = f"Failed to parse PDF: {exc}"
            raise ExtractionError(msg) from exc
        pages = []
        for page in doc:
            text = page.get_text(sort=True)
            if text.strip():
                pages.append(text.strip())
        doc.close()
        result = "\n\n".join(pages)
        if not result.strip():
            msg = "PDF contains no extractable text (may be scanned/image-based)"
            raise ExtractionError(msg)
        return result

    def _extract_docx(self, file_bytes: bytes) -> str:
        try:
            doc = Document(BytesIO(file_bytes))
        except Exception as exc:
            msg = f"Failed to parse DOCX: {exc}"
            raise ExtractionError(msg) from exc
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        result = "\n".join(paragraphs)
        if not result.strip():
            msg = "DOCX contains no extractable text"
            raise ExtractionError(msg)
        return result

    @staticmethod
    def _extract_txt(file_bytes: bytes) -> str:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1")
            except Exception as exc:
                msg = f"Failed to decode text file: {exc}"
                raise ExtractionError(msg) from exc
        if not text.strip():
            msg = "Text file is empty"
            raise ExtractionError(msg)
        return text


resume_extractor = ResumeExtractor()
