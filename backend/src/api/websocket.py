"""WebSocket endpoint for real-time session streaming."""

from __future__ import annotations

import contextlib
import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketException, status
from sqlalchemy import select

from src.core.database import get_db
from src.models.user import User
from src.services.auth import decode_access_token
from src.services.stream_manager import stream_manager

logger = logging.getLogger(__name__)

router = APIRouter()


def _resolve_get_db():  # type: ignore[no-untyped-def]
    """Return the active get_db callable, respecting dependency overrides."""
    from src.main import app  # deferred to avoid circular import

    return app.dependency_overrides.get(get_db, get_db)


async def _authenticate_ws(token: str) -> User:
    """Validate a JWT token and return the User, or raise."""
    user_id: uuid.UUID | None = decode_access_token(token)
    if user_id is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    db_factory = _resolve_get_db()
    db_gen = db_factory()
    db = await db_gen.__anext__()
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    finally:
        with contextlib.suppress(StopAsyncIteration):
            await db_gen.__anext__()

    if user is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    return user


@router.websocket("/sessions/{session_id}/stream")
async def session_stream(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
) -> None:
    """Stream real-time events for *session_id* over WebSocket.

    Authentication is performed via the ``token`` query parameter
    because browser WebSocket API does not support custom headers.
    """
    user = await _authenticate_ws(token)
    logger.info("WS auth OK: user=%s session=%s", user.id, session_id)

    await stream_manager.connect(session_id, websocket)
    try:
        # Keep the connection alive — listen for client messages
        # (e.g. approval responses or pings).  The primary data flow
        # is server → client via stream_manager.emit().
        while True:
            data = await websocket.receive_text()
            logger.debug("WS recv: session=%s data=%s", session_id, data[:200])
    except Exception:  # noqa: BLE001
        pass
    finally:
        await stream_manager.disconnect(session_id, websocket)
