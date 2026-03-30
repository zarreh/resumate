"""Career import request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class ImportResponse(BaseModel):
    """Response returned after extracting text from an uploaded resume."""

    filename: str
    content_type: str
    text: str
    char_count: int
