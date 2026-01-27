"""WebSocket integration tests."""

import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.main import app
from app.models.user import User


@asynccontextmanager
async def _fake_db_context():
    yield AsyncMock()

@asynccontextmanager
async def _noop_lifespan(_app):
    yield


async def _fake_get_user_from_token(token: str, db) -> User:
    return User(
        id="ws-test-user",
        email="ws-test@example.com",
        username="ws-test",
        hashed_password="not-used",
        is_active=True,
        is_superuser=False,
    )


def _patch_websocket_dependencies(monkeypatch):
    import app.api.websocket as websocket_api

    monkeypatch.setattr(websocket_api, "get_db_context", _fake_db_context)
    monkeypatch.setattr(websocket_api, "get_user_from_token", _fake_get_user_from_token)
    monkeypatch.setattr(app.router, "lifespan_context", _noop_lifespan)
    return websocket_api


def test_websocket_ping_pong(monkeypatch):
    _patch_websocket_dependencies(monkeypatch)

    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/ws/chat?token=test") as ws:
            connected = ws.receive_json()
            assert connected["type"] == "connected"
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong["type"] == "pong"


def test_websocket_rate_limit(monkeypatch):
    websocket_api = _patch_websocket_dependencies(monkeypatch)
    monkeypatch.setattr(websocket_api, "RATE_LIMIT_WINDOW_SECONDS", 1)
    monkeypatch.setattr(websocket_api, "MAX_MESSAGES_PER_WINDOW", 1)

    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/ws/chat?token=test") as ws:
            connected = ws.receive_json()
            assert connected["type"] == "connected"
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong["type"] == "pong"
            ws.send_json({"type": "ping"})
            error = ws.receive_json()
            assert error["type"] == "error"
            assert error["error"] == "Rate limit exceeded"


def test_websocket_idle_timeout(monkeypatch):
    websocket_api = _patch_websocket_dependencies(monkeypatch)
    monkeypatch.setattr(websocket_api, "IDLE_TIMEOUT_SECONDS", 0.1)

    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/ws/chat?token=test") as ws:
            connected = ws.receive_json()
            assert connected["type"] == "connected"
            time.sleep(0.2)
            with pytest.raises(WebSocketDisconnect):
                ws.receive_json()


@pytest.mark.asyncio
async def test_websocket_error_payload_logging(monkeypatch):
    import app.api.websocket as websocket_api

    class DummyWebSocket:
        application_state = WebSocketState.CONNECTED

        async def send_json(self, _message):
            return None

    warning_mock = Mock()
    monkeypatch.setattr(websocket_api.logger, "warning", warning_mock)

    await websocket_api.manager.send_message(
        DummyWebSocket(),
        {"type": "error", "error": {}},
    )

    assert warning_mock.called
    args, kwargs = warning_mock.call_args
    assert args[0] == "WebSocket error payload is empty or non-string"
    assert "error_payload" in kwargs
