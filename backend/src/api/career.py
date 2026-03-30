"""Career history endpoints — resume upload, text extraction, and parsing."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, status

from src.core.dependencies import get_current_user
from src.models.user import User
from src.schemas.career import ImportResponse, ParsedResumeResponse
from src.services.llm_config import get_llm_config
from src.services.resume_extractor import (
    ExtractionError,
    FileTooLargeError,
    UnsupportedFileTypeError,
    resume_extractor,
)
from src.services.resume_parser import ResumeParser

router = APIRouter()


@router.post("/import", response_model=ImportResponse, status_code=status.HTTP_200_OK)
async def import_resume(
    file: UploadFile,
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> ImportResponse:
    """Upload a resume file (PDF, DOCX, or TXT) and extract its text content.

    The extracted text is returned directly. Use ``POST /parse`` to structure
    the text into career entries.
    """
    content_type = file.content_type or ""
    file_bytes = await file.read()

    try:
        text = resume_extractor.extract(file_bytes, content_type)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except ExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return ImportResponse(
        filename=file.filename or "unknown",
        content_type=content_type,
        text=text,
        char_count=len(text),
    )


@router.post("/parse", response_model=ParsedResumeResponse, status_code=status.HTTP_200_OK)
async def parse_resume_text(
    text: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> ParsedResumeResponse:
    """Parse raw resume text into structured career entries using the LLM."""
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume text is empty",
        )

    parser = ResumeParser(get_llm_config())
    try:
        entries = await parser.parse(text)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse resume: {exc}",
        ) from exc

    return ParsedResumeResponse(entries=entries, entry_count=len(entries))
