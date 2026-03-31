"""Chat API endpoints — REST and WebSocket for conversational interaction."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.chat import ChatAgent
from src.core.database import get_db
from src.core.dependencies import get_current_user
from src.models.user import User
from src.services.llm_config import get_llm_config

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ChatMessageRequest(BaseModel):
    """Request body for sending a chat message."""

    message: str = Field(min_length=1, description="The user's message text")
    session_id: str | None = Field(
        default=None, description="Optional active session ID for context"
    )
    history: list[dict[str, str]] = Field(
        default_factory=list,
        description="Prior conversation messages as [{'role': 'user'|'assistant', 'content': '...'}]",
    )


class ChatMessageResponse(BaseModel):
    """Response from the chat endpoint."""

    message: str = Field(description="The assistant's reply")
    tool_calls_made: list[dict] = Field(  # type: ignore[type-arg]
        default_factory=list, description="Tools invoked during this turn"
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    body: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    """Send a chat message and get an AI response.

    Optionally provide a ``session_id`` so the agent can access
    session-specific data (JD analysis, resume draft, etc.).
    """
    llm_config = get_llm_config()

    session_uuid: uuid.UUID | None = None
    if body.session_id:
        try:
            session_uuid = uuid.UUID(body.session_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session_id format",
            ) from exc

    context = ChatAgent.create_context(
        db=db,
        user_id=current_user.id,
        llm_config=llm_config,
        session_id=session_uuid,
    )

    try:
        agent = ChatAgent(llm_config, context)
        response = await agent.chat(
            user_message=body.message,
            history=body.history if body.history else None,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Chat agent error: {exc}",
        ) from exc

    return ChatMessageResponse(
        message=response.message,
        tool_calls_made=response.tool_calls_made,
    )
