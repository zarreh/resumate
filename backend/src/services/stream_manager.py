"""Manages active WebSocket connections per session."""

from __future__ import annotations

import contextlib
import logging

from fastapi import WebSocket

from src.schemas.ws_events import WSEvent

logger = logging.getLogger(__name__)


class StreamManager:
    """Registry of WebSocket connections keyed by session ID.

    Provides connect/disconnect lifecycle and fan-out emit to all
    clients watching a given session.
    """

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, ws: WebSocket) -> None:
        """Accept and register a WebSocket for *session_id*."""
        await ws.accept()
        self._connections.setdefault(session_id, []).append(ws)
        logger.info("WS connected: session=%s (total=%d)", session_id, len(self._connections[session_id]))

    async def disconnect(self, session_id: str, ws: WebSocket) -> None:
        """Remove a WebSocket from the registry."""
        conns = self._connections.get(session_id)
        if conns is None:
            return
        with contextlib.suppress(ValueError):
            conns.remove(ws)
        if not conns:
            del self._connections[session_id]
        logger.info("WS disconnected: session=%s", session_id)

    async def emit(self, session_id: str, event: WSEvent) -> None:
        """Send *event* to every client connected to *session_id*."""
        conns = self._connections.get(session_id)
        if not conns:
            return
        dead: list[WebSocket] = []
        payload = event.model_dump_json()
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            await self.disconnect(session_id, ws)

    def active_connections(self, session_id: str) -> int:
        """Return the number of active connections for *session_id*."""
        return len(self._connections.get(session_id, []))


# Module-level singleton used by the rest of the application.
stream_manager = StreamManager()
