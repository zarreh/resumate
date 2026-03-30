"""Career history endpoints — resume upload and text extraction."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from src.core.dependencies import get_current_user
from src.models.user import User
from src.schemas.career import ImportResponse
from src.services.resume_extractor import (
    ExtractionError,
    FileTooLargeError,
    UnsupportedFileTypeError,
    resume_extractor,
)

router = APIRouter()


@router.post("/import", response_model=ImportResponse, status_code=status.HTTP_200_OK)
async def import_resume(
    file: UploadFile,
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> ImportResponse:
    """Upload a resume file (PDF, DOCX, or TXT) and extract its text content.

    The extracted text is returned directly. Parsing into structured career
    entries happens in a later phase (2.2b).
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
