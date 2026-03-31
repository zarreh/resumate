"""Schemas for the Chat agent."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the chat conversation."""

    role: Literal["user", "assistant", "system", "tool"] = Field(
        description="Who sent this message"
    )
    content: str = Field(description="Message text content")
    tool_calls: list[dict[str, Any]] | None = Field(
        default=None, description="Tool calls made by the assistant"
    )
    tool_call_id: str | None = Field(
        default=None, description="ID of the tool call this message responds to"
    )


class ChatResponse(BaseModel):
    """Response from the Chat agent."""

    message: str = Field(description="The assistant's reply")
    tool_calls_made: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Summary of tool calls made during this turn",
    )
