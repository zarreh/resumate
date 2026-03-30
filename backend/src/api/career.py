"""Career history endpoints — upload, parse, and CRUD for career entries."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.dependencies import get_current_user
from src.models.user import User
from src.schemas.career import (
    CareerEntryCreate,
    CareerEntryResponse,
    CareerEntryUpdate,
    ImportResponse,
    ParsedResumeResponse,
)
from src.services.career import CareerService
from src.services.llm_config import get_llm_config
from src.services.resume_extractor import (
    ExtractionError,
    FileTooLargeError,
    UnsupportedFileTypeError,
    resume_extractor,
)
from src.services.resume_parser import ResumeParser

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry_to_response(entry: object) -> CareerEntryResponse:
    """Convert a CareerHistoryEntry ORM object to a response schema."""
    return CareerEntryResponse(
        id=str(entry.id),  # type: ignore[attr-defined]
        entry_type=entry.entry_type,  # type: ignore[attr-defined]
        title=entry.title,  # type: ignore[attr-defined]
        organization=entry.organization,  # type: ignore[attr-defined]
        start_date=entry.start_date.isoformat() if entry.start_date else None,  # type: ignore[attr-defined]
        end_date=entry.end_date.isoformat() if entry.end_date else None,  # type: ignore[attr-defined]
        bullet_points=entry.bullet_points,  # type: ignore[attr-defined]
        tags=entry.tags,  # type: ignore[attr-defined]
        source=entry.source,  # type: ignore[attr-defined]
        raw_text=entry.raw_text,  # type: ignore[attr-defined]
    )


# ---------------------------------------------------------------------------
# Import & Parse
# ---------------------------------------------------------------------------


@router.post("/import", response_model=ImportResponse, status_code=status.HTTP_200_OK)
async def import_resume(
    file: UploadFile,
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> ImportResponse:
    """Upload a resume file (PDF, DOCX, or TXT) and extract its text content."""
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


# ---------------------------------------------------------------------------
# CRUD Endpoints
# ---------------------------------------------------------------------------


@router.get("/entries", response_model=list[CareerEntryResponse])
async def list_entries(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CareerEntryResponse]:
    """List all career entries for the current user."""
    svc = CareerService(db)
    entries = await svc.list_entries(current_user.id)
    return [_entry_to_response(e) for e in entries]


@router.post("/entries", response_model=CareerEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    data: CareerEntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CareerEntryResponse:
    """Create a new career entry."""
    svc = CareerService(db)
    entry = await svc.create_entry(current_user.id, data)
    return _entry_to_response(entry)


@router.get("/entries/{entry_id}", response_model=CareerEntryResponse)
async def get_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CareerEntryResponse:
    """Get a single career entry by ID."""
    svc = CareerService(db)
    entry = await svc.get_entry(current_user.id, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    return _entry_to_response(entry)


@router.put("/entries/{entry_id}", response_model=CareerEntryResponse)
async def update_entry(
    entry_id: uuid.UUID,
    data: CareerEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CareerEntryResponse:
    """Update a career entry."""
    svc = CareerService(db)
    entry = await svc.update_entry(current_user.id, entry_id, data)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    return _entry_to_response(entry)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a career entry."""
    svc = CareerService(db)
    deleted = await svc.delete_entry(current_user.id, entry_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/entries/confirm-all")
async def confirm_all_entries(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Mark all parsed_resume entries as user_confirmed."""
    svc = CareerService(db)
    count = await svc.confirm_all(current_user.id)
    return {"confirmed": count}
