"""Tests for WebSocket streaming infrastructure."""

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.main import app
from src.schemas.ws_events import WSEvent
from src.services.stream_manager import StreamManager, stream_manager

# ---------------------------------------------------------------------------
# Unit tests for StreamManager (no real WebSocket needed)
# ---------------------------------------------------------------------------


class TestStreamManager:
    """Tests for the StreamManager class in isolation."""

    def test_initial_state(self) -> None:
        mgr = StreamManager()
        assert mgr.active_connections("any-session") == 0


# ---------------------------------------------------------------------------
# WSEvent schema tests
# ---------------------------------------------------------------------------


class TestWSEventSchema:
    def test_minimal_event(self) -> None:
        event = WSEvent(type="thinking")
        data = event.model_dump()
        assert data["type"] == "thinking"
        assert data["agent"] is None

    def test_full_event(self) -> None:
        event = WSEvent(
            type="stream_token",
            agent="resume_writer",
            token="Hello",
            section="summary",
        )
        assert event.type == "stream_token"
        assert event.token == "Hello"

    def test_json_round_trip(self) -> None:
        event = WSEvent(
            type="progress",
            current=5,
            total=20,
            label="writing bullets",
        )
        json_str = event.model_dump_json()
        restored = WSEvent.model_validate_json(json_str)
        assert restored == event

    def test_error_event(self) -> None:
        event = WSEvent(
            type="error",
            message="LLM rate limited",
            recoverable=True,
        )
        assert event.recoverable is True

    def test_approval_gate_event(self) -> None:
        event = WSEvent(
            type="approval_gate",
            gate="calibration",
            data={"bullet_count": 3},
        )
        assert event.gate == "calibration"
        assert event.data == {"bullet_count": 3}


# ---------------------------------------------------------------------------
# Integration tests using Starlette's TestClient (synchronous WS helper)
#
# Important: each test must register the user AND use the WS within the
# same TestClient context so they share the same anyio event loop.
# This avoids "attached to a different loop" errors.
# ---------------------------------------------------------------------------


def _register(c: TestClient, suffix: str = "") -> str:
    """Register a user and return an access token using an existing client."""
    resp = c.post(
        "/api/v1/auth/register",
        json={
            "name": "WS User",
            "email": f"ws-{id(c)}{suffix}@example.com",
            "password": "password123",
        },
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


def test_ws_connect_and_receive() -> None:
    """Client connects via WS, server emits an event, client receives it."""
    session_id = "test-session-1"

    with TestClient(app) as c:  # noqa: SIM117
        token = _register(c)
        with c.websocket_connect(
            f"/api/v1/sessions/{session_id}/stream?token={token}"
        ) as ws:
            event = WSEvent(type="progress", current=3, total=10, label="parsing")

            async def _emit() -> None:
                await stream_manager.emit(session_id, event)

            ws.portal.call(_emit)

            data = ws.receive_json()
            assert data["type"] == "progress"
            assert data["current"] == 3
            assert data["total"] == 10
            assert data["label"] == "parsing"


def test_ws_stream_token_assembly() -> None:
    """Multiple stream_token events are received in order."""
    session_id = "test-session-2"
    tokens_to_send = ["Hello", " ", "world", "!"]

    with TestClient(app) as c:  # noqa: SIM117
        token = _register(c)
        with c.websocket_connect(
            f"/api/v1/sessions/{session_id}/stream?token={token}"
        ) as ws:
            async def _emit_tokens() -> None:
                await stream_manager.emit(
                    session_id,
                    WSEvent(type="stream_start", section="summary"),
                )
                for t in tokens_to_send:
                    await stream_manager.emit(
                        session_id,
                        WSEvent(type="stream_token", token=t),
                    )
                await stream_manager.emit(
                    session_id,
                    WSEvent(type="stream_end"),
                )

            ws.portal.call(_emit_tokens)

            received: list[dict] = []
            for _ in range(len(tokens_to_send) + 2):
                received.append(ws.receive_json())

            assert received[0]["type"] == "stream_start"
            assembled = "".join(
                e["token"] for e in received if e["type"] == "stream_token"
            )
            assert assembled == "Hello world!"
            assert received[-1]["type"] == "stream_end"


def test_ws_rejects_invalid_token() -> None:
    """Connection with a bad token is rejected (close code 1008)."""
    with TestClient(app) as c:
        with pytest.raises(WebSocketDisconnect) as exc_info:  # noqa: SIM117
            with c.websocket_connect(
                "/api/v1/sessions/any/stream?token=invalid-jwt"
            ):
                pass  # pragma: no cover
        assert exc_info.value.code == 1008
