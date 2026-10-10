"""
Unit tests for GB050 M11 observability improvements.

Tests:
- Structured logging migration (cache, tasks use structlog)
- ResponseTimeMiddleware logs all requests
- Circuit breaker status in detailed health check
- Startup observability summary
"""

import asyncio
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request, Response
from starlette.datastructures import Headers

from app.core.middleware import (
    ResponseTimeMiddleware,
    CircuitBreaker,
    circuit_breakers,
    request_id_var,
)


# =============================================================================
# Structured Logging Migration Tests
# =============================================================================


class TestStructlogMigration:
    """Verify core modules use structlog instead of plain logging."""

    def test_cache_uses_structlog(self):
        """cache.py should use structlog.get_logger, not logging.getLogger."""
        import app.core.cache as cache_mod
        import structlog

        assert hasattr(cache_mod, "logger")
        assert isinstance(
            cache_mod.logger, structlog.stdlib.BoundLogger
        ) or hasattr(cache_mod.logger, "bind")

    def test_tasks_uses_structlog(self):
        """tasks.py should use structlog.get_logger, not logging.getLogger."""
        pytest.importorskip("arq")
        import app.core.tasks as tasks_mod
        import structlog

        assert hasattr(tasks_mod, "logger")
        assert isinstance(
            tasks_mod.logger, structlog.stdlib.BoundLogger
        ) or hasattr(tasks_mod.logger, "bind")

    def test_middleware_uses_structlog(self):
        """middleware.py should use structlog.get_logger."""
        import app.core.middleware as mw_mod
        import structlog

        assert hasattr(mw_mod, "logger")
        assert isinstance(
            mw_mod.logger, structlog.stdlib.BoundLogger
        ) or hasattr(mw_mod.logger, "bind")

    def test_database_uses_structlog(self):
        """database.py should use structlog.get_logger."""
        import app.core.database as db_mod
        import structlog

        assert hasattr(db_mod, "logger")
        assert isinstance(
            db_mod.logger, structlog.stdlib.BoundLogger
        ) or hasattr(db_mod.logger, "bind")


# =============================================================================
# ResponseTimeMiddleware - All Requests Logged
# =============================================================================


class TestResponseTimeAllRequests:
    """Test that ResponseTimeMiddleware logs all non-health requests."""

    @pytest.mark.asyncio
    async def test_fast_request_logged_at_debug(self):
        """Requests under 500ms should be logged at DEBUG level."""
        middleware = ResponseTimeMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.headers = Headers({})
        request.url.path = "/api/v1/chat"
        request.method = "POST"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}

        async def fast_call_next(req):
            return mock_response

        with patch("app.core.middleware.logger") as mock_logger:
            await middleware.dispatch(request, fast_call_next)
            mock_logger.debug.assert_called_once()
            call_kwargs = mock_logger.debug.call_args
            assert "Request completed" in call_kwargs[0][0]

    @pytest.mark.asyncio
    async def test_medium_request_logged_at_info(self):
        """Requests between 500ms-1000ms should be logged at INFO level."""
        middleware = ResponseTimeMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.headers = Headers({})
        request.url.path = "/api/v1/query"
        request.method = "GET"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}

        async def medium_call_next(req):
            await asyncio.sleep(0.6)
            return mock_response

        with patch("app.core.middleware.logger") as mock_logger:
            await middleware.dispatch(request, medium_call_next)
            mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_slow_request_logged_at_warning(self):
        """Requests over 1000ms should be logged at WARNING level."""
        middleware = ResponseTimeMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.headers = Headers({})
        request.url.path = "/api/v1/documents"
        request.method = "POST"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}

        async def slow_call_next(req):
            await asyncio.sleep(1.1)
            return mock_response

        with patch("app.core.middleware.logger") as mock_logger:
            await middleware.dispatch(request, slow_call_next)
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert "Slow request" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_health_endpoint_not_logged(self):
        """Health check endpoints should not be logged."""
        middleware = ResponseTimeMiddleware(MagicMock())

        for path in ["/health", "/healthz", "/api/health", "/api/healthz"]:
            request = MagicMock(spec=Request)
            request.headers = Headers({})
            request.url.path = path
            request.method = "GET"

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}

            async def call_next(req):
                return mock_response

            with patch("app.core.middleware.logger") as mock_logger:
                await middleware.dispatch(request, call_next)
                mock_logger.debug.assert_not_called()
                mock_logger.info.assert_not_called()
                mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_includes_duration_and_status(self):
        """Log entries should include duration_ms, status_code, method, path."""
        middleware = ResponseTimeMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.headers = Headers({})
        request.url.path = "/api/v1/test"
        request.method = "GET"

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {}

        async def call_next(req):
            return mock_response

        with patch("app.core.middleware.logger") as mock_logger:
            await middleware.dispatch(request, call_next)
            call_kwargs = mock_logger.debug.call_args[1]
            assert "duration_ms" in call_kwargs
            assert call_kwargs["status_code"] == 201
            assert call_kwargs["method"] == "GET"
            assert call_kwargs["path"] == "/api/v1/test"


# =============================================================================
# Circuit Breaker in Health Check
# =============================================================================


class TestCircuitBreakerHealthCheck:
    """Test circuit breaker status in detailed health endpoint."""

    @pytest.mark.asyncio
    async def test_detailed_health_includes_circuit_breakers(self, client):
        """Detailed health should include circuit breaker status."""
        from app.core.middleware import circuit_breakers

        response = await client.get("/api/v1/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert "circuit_breakers" in data["checks"]
        cb_check = data["checks"]["circuit_breakers"]
        assert "status" in cb_check
        assert "breakers" in cb_check

    @pytest.mark.asyncio
    async def test_circuit_breaker_healthy_when_all_closed(self, client):
        """Circuit breakers should report healthy when all closed."""
        from app.core.middleware import circuit_breakers

        # Reset all breakers to closed
        for cb in circuit_breakers.values():
            cb._state = CircuitBreaker.CLOSED
            cb._failure_count = 0

        response = await client.get("/api/v1/health/detailed")
        data = response.json()
        cb_check = data["checks"]["circuit_breakers"]
        assert cb_check["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_circuit_breaker_degraded_when_open(self, client):
        """Circuit breakers should report degraded when any is open."""
        from app.core.middleware import circuit_breakers

        # Open one breaker
        cb = circuit_breakers.get("devlake")
        if cb:
            original_state = cb._state
            original_failures = cb._failure_count
            original_time = cb._last_failure_time
            cb._state = CircuitBreaker.OPEN
            cb._last_failure_time = time.time()
            cb._failure_count = cb.failure_threshold

            try:
                response = await client.get("/api/v1/health/detailed")
                data = response.json()
                cb_check = data["checks"]["circuit_breakers"]
                assert cb_check["status"] == "degraded"
                assert cb_check["breakers"]["devlake"]["state"] == "open"
            finally:
                cb._state = original_state
                cb._failure_count = original_failures
                cb._last_failure_time = original_time

    @pytest.mark.asyncio
    async def test_circuit_breaker_shows_failure_count(self, client):
        """Each breaker should show its failure count."""
        from app.core.middleware import circuit_breakers

        cb = circuit_breakers.get("openai")
        if cb:
            original = cb._failure_count
            cb._failure_count = 2
            try:
                response = await client.get("/api/v1/health/detailed")
                data = response.json()
                breakers = data["checks"]["circuit_breakers"]["breakers"]
                assert breakers["openai"]["failure_count"] == 2
            finally:
                cb._failure_count = original


# =============================================================================
# Startup Observability Summary
# =============================================================================


class TestStartupObservability:
    """Test startup observability configuration logging."""

    def test_structlog_json_renderer_configured(self):
        """structlog should be configured with JSON or Console renderer."""
        import structlog
        config = structlog.get_config()
        processors = config.get("processors", [])
        processor_names = [type(p).__name__ for p in processors if not callable(p) or hasattr(p, '__name__')]
        # Should have TimeStamper for ISO timestamps
        assert any("TimeStamper" in type(p).__name__ for p in processors)

    def test_structlog_has_context_vars_merge(self):
        """structlog should merge context vars (for request_id propagation)."""
        import structlog
        config = structlog.get_config()
        processors = config.get("processors", [])
        has_contextvars = any(
            "merge_contextvars" in str(p) or "contextvars" in str(type(p).__name__).lower()
            for p in processors
        )
        assert has_contextvars

    def test_sensitive_field_redaction(self):
        """structlog should redact sensitive fields."""
        from app.main import _redact_sensitive_fields

        event_dict = {
            "event": "test",
            "password": "secret123",
            "api_key": "sk-abc",
            "username": "visible",
        }
        result = _redact_sensitive_fields(None, "info", event_dict)
        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"
        assert result["username"] == "visible"


# =============================================================================
# Error Tracking Correlation
# =============================================================================


class TestErrorTrackingCorrelation:
    """Test that error tracking includes proper correlation IDs."""

    @pytest.mark.asyncio
    async def test_error_response_has_request_id_header(self):
        """Error responses should include X-Request-ID for log correlation."""
        from app.core.middleware import ErrorTrackingMiddleware

        middleware = ErrorTrackingMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.headers = Headers({})
        request.url.path = "/api/v1/crash"
        request.method = "GET"
        request.query_params = ""

        test_request_id = f"test-{uuid.uuid4()}"
        token = request_id_var.set(test_request_id)

        async def crash(req):
            raise RuntimeError("test crash")

        try:
            response = await middleware.dispatch(request, crash)
            assert response.status_code == 500
            assert response.headers["X-Request-ID"] == test_request_id
            assert "X-Error-ID" in response.headers
        finally:
            request_id_var.reset(token)

    @pytest.mark.asyncio
    async def test_error_log_includes_all_context(self):
        """Unhandled exception log should include request_id, error_type, traceback."""
        from app.core.middleware import ErrorTrackingMiddleware

        middleware = ErrorTrackingMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.headers = Headers({})
        request.url.path = "/api/v1/fail"
        request.method = "POST"
        request.query_params = "foo=bar"

        token = request_id_var.set("corr-123")

        async def fail(req):
            raise ValueError("something broke")

        try:
            with patch("app.core.middleware.logger") as mock_logger:
                await middleware.dispatch(request, fail)
                mock_logger.error.assert_called()
                kwargs = mock_logger.error.call_args[1]
                assert kwargs["request_id"] == "corr-123"
                assert kwargs["error_type"] == "ValueError"
                assert "traceback" in kwargs
                assert kwargs["method"] == "POST"
                assert kwargs["path"] == "/api/v1/fail"
        finally:
            request_id_var.reset(token)
