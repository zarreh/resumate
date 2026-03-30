"""WebSocket event protocol schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

WSEventType = Literal[
    "agent_start",
    "agent_end",
    "thinking",
    "stream_start",
    "stream_token",
    "stream_end",
    "progress",
    "approval_gate",
    "error",
]


class WSEvent(BaseModel):
    """A single WebSocket event sent from server to client."""

    type: WSEventType
    agent: str | None = None
    message: str | None = None
    section: str | None = None
    token: str | None = None
    current: int | None = None
    total: int | None = None
    label: str | None = None
    gate: str | None = None
    data: dict[str, Any] | None = None
    recoverable: bool | None = None
