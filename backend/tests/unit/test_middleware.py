"""
Unit tests for middleware components.
"""

import asyncio
import hashlib
import time
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers

from app.core.middleware import (
    RequestIDMiddleware,
    ResponseTimeMiddleware,
    RateLimitMiddleware,
    TenantMiddleware,
    TenantRateLimitMiddleware,
    SecurityHeadersMiddleware,
    CompressionMiddleware,
    ErrorTrackingMiddleware,
    CircuitBreaker,
    CircuitBreakerOpenError,
    get_circuit_breaker,
    circuit_breakers,
    request_id_var,
    tenant_id_var,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_request():
    """Create a mock request."""
    request = MagicMock(spec=Request)
    request.headers = Headers({})
    request.url.path = "/api/v1/test"
    request.method = "GET"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def mock_response():
    """Create a mock response."""
    response = MagicMock(spec=Response)
    response.headers = {}
    response.status_code = 200
    return response


@pytest.fixture
def mock_call_next(mock_response):
    """Create a mock call_next function."""
    async def call_next(request):
        return mock_response
    return call_next


@pytest.fixture
def mock_app():
    """Create a mock ASGI app."""
    return MagicMock()


# =============================================================================
# RequestIDMiddleware Tests
# =============================================================================


class TestRequestIDMiddleware:
    """Tests for RequestIDMiddleware."""

    @pytest.mark.asyncio
    async def test_generates_request_id(self, mock_request, mock_call_next):
        """Test that middleware generates request ID."""
        middleware = RequestIDMiddleware(MagicMock())

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    @pytest.mark.asyncio
    async def test_uses_provided_request_id(self, mock_call_next):
        """Test that middleware uses provided X-Request-ID."""
        request = MagicMock(spec=Request)
        request.headers = Headers({"X-Request-ID": "custom-id-123"})
        request.url.path = "/test"

        middleware = RequestIDMiddleware(MagicMock())

        response = await middleware.dispatch(request, mock_call_next)

        assert response.headers["X-Request-ID"] == "custom-id-123"

    @pytest.mark.asyncio
    async def test_sets_context_var(self, mock_request, mock_call_next):
        """Test that middleware sets context variable."""
        middleware = RequestIDMiddleware(MagicMock())

        captured_id = None

        async def capture_call_next(request):
            nonlocal captured_id
            captured_id = request_id_var.get()
            return MagicMock(headers={})

        await middleware.dispatch(mock_request, capture_call_next)

        assert captured_id is not None
        assert len(captured_id) > 0


# =============================================================================
# ResponseTimeMiddleware Tests
# =============================================================================


class TestResponseTimeMiddleware:
    """Tests for ResponseTimeMiddleware."""

    @pytest.mark.asyncio
    async def test_adds_process_time_header(self, mock_request, mock_call_next):
        """Test that middleware adds X-Process-Time header."""
        middleware = ResponseTimeMiddleware(MagicMock())

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert "X-Process-Time" in response.headers
        assert "ms" in response.headers["X-Process-Time"]

    @pytest.mark.asyncio
    async def test_measures_actual_time(self, mock_request):
        """Test that middleware measures actual processing time."""
        middleware = ResponseTimeMiddleware(MagicMock())

        async def slow_call_next(request):
            await asyncio.sleep(0.1)  # 100ms
            response = MagicMock()
            response.headers = {}
            return response

        response = await middleware.dispatch(mock_request, slow_call_next)

        # Extract time value
        time_str = response.headers["X-Process-Time"]
        time_ms = float(time_str.replace("ms", ""))

        assert time_ms >= 100  # At least 100ms

    @pytest.mark.asyncio
    async def test_logs_slow_requests(self, mock_request):
        """Test that slow requests are logged as warnings."""
        middleware = ResponseTimeMiddleware(MagicMock())

        async def very_slow_call_next(request):
            await asyncio.sleep(1.1)  # > 1 second
            response = MagicMock()
            response.headers = {}
            response.status_code = 200
            return response

        with patch("app.core.middleware.logger") as mock_logger:
            await middleware.dispatch(mock_request, very_slow_call_next)
            mock_logger.warning.assert_called()
            call_args = mock_logger.warning.call_args
            assert "Slow request" in call_args[0][0]


# =============================================================================
# RateLimitMiddleware Tests
# =============================================================================


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    @pytest.mark.asyncio
    async def test_skips_health_check_endpoints(self, mock_call_next):
        """Test that health check endpoints skip rate limiting."""
        middleware = RateLimitMiddleware(MagicMock())

        for path in ["/api/v1/health", "/health", "/healthz"]:
            request = MagicMock(spec=Request)
            request.url.path = path
            request.headers = Headers({})

            response = await middleware.dispatch(request, mock_call_next)

            assert response is not None

    @pytest.mark.asyncio
    async def test_extracts_client_id_from_bearer_token(self, mock_call_next):
        """Test client ID extraction from bearer token."""
        middleware = RateLimitMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/test"
        request.headers = Headers({"Authorization": "Bearer test-token-123"})
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        client_id = middleware._get_client_id(request)

        assert client_id.startswith("token:")
        # Should be a hash
        assert len(client_id.split(":")[1]) == 16

    @pytest.mark.asyncio
    async def test_extracts_client_id_from_forwarded_ip(self, mock_call_next):
        """Test client ID extraction from X-Forwarded-For."""
        middleware = RateLimitMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/test"
        request.headers = Headers({"X-Forwarded-For": "10.0.0.1, 192.168.1.1"})
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        client_id = middleware._get_client_id(request)

        assert client_id == "ip:10.0.0.1"

    @pytest.mark.asyncio
    async def test_extracts_client_id_from_client_host(self, mock_call_next):
        """Test client ID extraction from client host."""
        middleware = RateLimitMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/test"
        request.headers = Headers({})
        request.client = MagicMock()
        request.client.host = "192.168.1.100"

        client_id = middleware._get_client_id(request)

        assert client_id == "ip:192.168.1.100"

    @pytest.mark.asyncio
    async def test_handles_missing_client(self, mock_call_next):
        """Test handling of missing client."""
        middleware = RateLimitMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/test"
        request.headers = Headers({})
        request.client = None

        client_id = middleware._get_client_id(request)

        assert client_id == "ip:unknown"

    @pytest.mark.asyncio
    async def test_rate_limit_headers_on_allowed(self, mock_request, mock_call_next):
        """Test rate limit headers are added when allowed."""
        middleware = RateLimitMiddleware(MagicMock())

        with patch("app.core.cache.api_rate_limiter") as mock_limiter:
            mock_limiter.is_allowed = AsyncMock(return_value=(True, {
                "limit": 60,
                "remaining": 59,
                "reset_in": 60,
            }))

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.headers.get("X-RateLimit-Limit") == "60"
            assert response.headers.get("X-RateLimit-Remaining") == "59"

    @pytest.mark.asyncio
    async def test_rate_limit_returns_429_when_exceeded(self, mock_request, mock_call_next):
        """Test rate limit returns 429 when exceeded."""
        middleware = RateLimitMiddleware(MagicMock())

        with patch("app.core.cache.api_rate_limiter") as mock_limiter:
            mock_limiter.is_allowed = AsyncMock(return_value=(False, {
                "limit": 60,
                "remaining": 0,
                "reset_in": 30,
            }))

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert isinstance(response, JSONResponse)
            assert response.status_code == 429


# =============================================================================
# TenantMiddleware Tests
# =============================================================================


class TestTenantMiddleware:
    """Tests for TenantMiddleware."""

    @pytest.mark.asyncio
    async def test_extracts_tenant_from_header(self, mock_call_next):
        """Test tenant extraction from X-Tenant-ID header."""
        middleware = TenantMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.headers = Headers({"X-Tenant-ID": "tenant-123"})
        request.url.path = "/api/v1/test"

        tenant_id = middleware._extract_tenant_id(request)

        assert tenant_id == "tenant-123"

    @pytest.mark.asyncio
    async def test_extracts_tenant_from_organization_header(self, mock_call_next):
        """Test tenant extraction from X-Organization-ID header."""
        middleware = TenantMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.headers = Headers({"X-Organization-ID": "org-456"})
        request.url.path = "/api/v1/test"

        tenant_id = middleware._extract_tenant_id(request)

        assert tenant_id == "org-456"

    @pytest.mark.asyncio
    async def test_tenant_header_priority(self, mock_call_next):
        """Test X-Tenant-ID takes priority over X-Organization-ID."""
        middleware = TenantMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.headers = Headers({
            "X-Tenant-ID": "tenant-123",
            "X-Organization-ID": "org-456",
        })
        request.url.path = "/api/v1/test"

        tenant_id = middleware._extract_tenant_id(request)

        assert tenant_id == "tenant-123"

    @pytest.mark.asyncio
    async def test_sets_tenant_context(self, mock_call_next):
        """Test that tenant context is set during request."""
        middleware = TenantMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.headers = Headers({"X-Tenant-ID": "tenant-123"})
        request.url.path = "/api/v1/test"

        captured_tenant = None

        async def capture_call_next(request):
            nonlocal captured_tenant
            captured_tenant = tenant_id_var.get()
            response = MagicMock()
            response.headers = {}
            return response

        with patch("app.core.multitenancy.set_current_tenant_id"):
            await middleware.dispatch(request, capture_call_next)

        assert captured_tenant == "tenant-123"

    @pytest.mark.asyncio
    async def test_adds_tenant_to_response_header(self, mock_call_next):
        """Test that tenant ID is added to response header."""
        middleware = TenantMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.headers = Headers({"X-Tenant-ID": "tenant-123"})
        request.url.path = "/api/v1/test"

        with patch("app.core.multitenancy.set_current_tenant_id"):
            response = await middleware.dispatch(request, mock_call_next)

        assert response.headers.get("X-Tenant-ID") == "tenant-123"


# =============================================================================
# TenantRateLimitMiddleware Tests
# =============================================================================


class TestTenantRateLimitMiddleware:
    """Tests for TenantRateLimitMiddleware."""

    @pytest.mark.asyncio
    async def test_skips_health_endpoints(self, mock_call_next):
        """Test that health endpoints skip tenant rate limiting."""
        middleware = TenantRateLimitMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/health"
        request.headers = Headers({})

        response = await middleware.dispatch(request, mock_call_next)

        assert response is not None

    @pytest.mark.asyncio
    async def test_skips_without_tenant_context(self, mock_request, mock_call_next):
        """Test that requests without tenant context are passed through."""
        middleware = TenantRateLimitMiddleware(MagicMock())

        # Clear tenant context
        tenant_id_var.set("")

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response is not None


# =============================================================================
# SecurityHeadersMiddleware Tests
# =============================================================================


class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware."""

    @pytest.mark.asyncio
    async def test_adds_security_headers(self, mock_request, mock_call_next):
        """Test that security headers are added."""
        middleware = SecurityHeadersMiddleware(MagicMock())

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "strict-origin" in response.headers["Referrer-Policy"]

    @pytest.mark.asyncio
    async def test_adds_hsts_in_production(self, mock_request, mock_call_next):
        """Test that HSTS is added in production."""
        middleware = SecurityHeadersMiddleware(MagicMock())

        with patch("app.core.middleware.settings") as mock_settings:
            mock_settings.is_production = True

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert "Strict-Transport-Security" in response.headers


# =============================================================================
# CompressionMiddleware Tests
# =============================================================================


class TestCompressionMiddleware:
    """Tests for CompressionMiddleware."""

    @pytest.mark.asyncio
    async def test_sets_vary_header_for_gzip(self, mock_call_next):
        """Test Vary header is set when client accepts gzip."""
        middleware = CompressionMiddleware(MagicMock())

        request = MagicMock(spec=Request)
        request.headers = Headers({"Accept-Encoding": "gzip, deflate"})
        request.url.path = "/api/v1/test"

        response = await middleware.dispatch(request, mock_call_next)

        assert response.headers.get("Vary") == "Accept-Encoding"


# =============================================================================
# CircuitBreaker Tests
# =============================================================================


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_initial_state_is_closed(self):
        """Test circuit breaker starts in closed state."""
        cb = CircuitBreaker("test")
        assert cb.state == CircuitBreaker.CLOSED

    def test_opens_after_threshold_failures(self):
        """Test circuit opens after failure threshold."""
        cb = CircuitBreaker("test", failure_threshold=3)

        for _ in range(3):
            cb.record_failure()

        assert cb.state == CircuitBreaker.OPEN

    def test_success_resets_failure_count(self):
        """Test success resets failure count in closed state."""
        cb = CircuitBreaker("test", failure_threshold=3)

        cb.record_failure()
        cb.record_failure()
        cb.record_success()

        assert cb._failure_count == 0
        assert cb.state == CircuitBreaker.CLOSED

    def test_half_open_after_timeout(self):
        """Test circuit becomes half-open after timeout."""
        cb = CircuitBreaker("test", failure_threshold=1, timeout=0)

        cb.record_failure()
        assert cb._state == CircuitBreaker.OPEN

        # After timeout, accessing .state triggers transition
        time.sleep(0.01)
        assert cb.state == CircuitBreaker.HALF_OPEN

    def test_success_in_half_open_closes_circuit(self):
        """Test success in half-open state closes circuit."""
        cb = CircuitBreaker("test", failure_threshold=1, success_threshold=1, timeout=0)

        cb.record_failure()
        time.sleep(0.01)
        # Access state to trigger OPEN -> HALF_OPEN transition
        _ = cb.state

        cb.record_success()

        assert cb.state == CircuitBreaker.CLOSED

    def test_failure_in_half_open_opens_circuit(self):
        """Test failure in half-open state opens circuit."""
        # Use a longer timeout so it doesn't immediately transition back to half-open
        cb = CircuitBreaker("test", failure_threshold=1, timeout=60)

        cb.record_failure()
        # Manually set to half-open state for testing
        cb._state = CircuitBreaker.HALF_OPEN

        cb.record_failure()

        # Internal state should be OPEN
        assert cb._state == CircuitBreaker.OPEN

    def test_is_available(self):
        """Test is_available method."""
        cb = CircuitBreaker("test", failure_threshold=1)

        assert cb.is_available() is True

        cb.record_failure()

        assert cb.is_available() is False

    @pytest.mark.asyncio
    async def test_call_executes_function_when_closed(self):
        """Test call executes function when circuit is closed."""
        cb = CircuitBreaker("test")

        async def test_func():
            return "success"

        result = await cb.call(test_func)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_call_raises_when_open(self):
        """Test call raises when circuit is open."""
        cb = CircuitBreaker("test", failure_threshold=1)
        cb.record_failure()

        async def test_func():
            return "success"

        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(test_func)

    @pytest.mark.asyncio
    async def test_call_records_success_on_success(self):
        """Test call records success when function succeeds."""
        cb = CircuitBreaker("test", failure_threshold=3)
        cb._failure_count = 2

        async def test_func():
            return "success"

        await cb.call(test_func)

        assert cb._failure_count == 0

    @pytest.mark.asyncio
    async def test_call_records_failure_on_exception(self):
        """Test call records failure when function raises."""
        cb = CircuitBreaker("test", failure_threshold=3)

        async def failing_func():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await cb.call(failing_func)

        assert cb._failure_count == 1


# =============================================================================
# Circuit Breaker Registry Tests
# =============================================================================


class TestCircuitBreakerRegistry:
    """Tests for circuit breaker registry."""

    def test_preconfigured_breakers_exist(self):
        """Test preconfigured circuit breakers exist."""
        assert "devlake" in circuit_breakers
        assert "openbao" in circuit_breakers
        assert "openfga" in circuit_breakers
        assert "openai" in circuit_breakers
        assert "anthropic" in circuit_breakers

    def test_get_circuit_breaker_existing(self):
        """Test getting existing circuit breaker."""
        cb = get_circuit_breaker("devlake")

        assert cb is not None
        assert cb.name == "devlake"

    def test_get_circuit_breaker_creates_new(self):
        """Test getting non-existing circuit breaker creates new one."""
        name = f"test-breaker-{uuid.uuid4()}"
        cb = get_circuit_breaker(name)

        assert cb is not None
        assert cb.name == name
        assert name in circuit_breakers


# =============================================================================
# Context Variable Tests
# =============================================================================


class TestContextVariables:
    """Tests for context variables."""

    def test_request_id_var_default(self):
        """Test request_id_var default value."""
        assert request_id_var.get() == ""

    def test_tenant_id_var_default(self):
        """Test tenant_id_var default value."""
        assert tenant_id_var.get() == ""

    def test_request_id_var_set_and_get(self):
        """Test setting and getting request_id_var."""
        token = request_id_var.set("test-request-id")

        assert request_id_var.get() == "test-request-id"

        request_id_var.reset(token)

    def test_tenant_id_var_set_and_get(self):
        """Test setting and getting tenant_id_var."""
        token = tenant_id_var.set("test-tenant-id")

        assert tenant_id_var.get() == "test-tenant-id"

        tenant_id_var.reset(token)


# =============================================================================
# ErrorTrackingMiddleware Tests
# =============================================================================


class TestErrorTrackingMiddleware:
    """Tests for ErrorTrackingMiddleware."""

    @pytest.mark.asyncio
    async def test_passes_through_successful_request(self, mock_request, mock_call_next):
        """Test that successful requests pass through unchanged."""
        middleware = ErrorTrackingMiddleware(MagicMock())

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}

        async def success_call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, success_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_logs_4xx_errors_as_warning(self, mock_request):
        """Test that 4xx errors are logged as warnings."""
        middleware = ErrorTrackingMiddleware(MagicMock())

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.headers = {}

        async def not_found_call_next(request):
            return mock_response

        with patch("app.core.middleware.logger") as mock_logger:
            response = await middleware.dispatch(mock_request, not_found_call_next)

            assert response.status_code == 404
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_logs_5xx_errors_as_error(self, mock_request):
        """Test that 5xx errors are logged as errors."""
        middleware = ErrorTrackingMiddleware(MagicMock())

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {}

        async def server_error_call_next(request):
            return mock_response

        with patch("app.core.middleware.logger") as mock_logger:
            response = await middleware.dispatch(mock_request, server_error_call_next)

            assert response.status_code == 500
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_catches_unhandled_exception(self, mock_request):
        """Test that unhandled exceptions are caught and logged."""
        middleware = ErrorTrackingMiddleware(MagicMock())

        async def exception_call_next(request):
            raise ValueError("Test error")

        with patch("app.core.middleware.logger") as mock_logger:
            response = await middleware.dispatch(mock_request, exception_call_next)

            # Should return a 500 response
            assert response.status_code == 500

            # Should log the error
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_exception_response_includes_error_id(self, mock_request):
        """Test that exception response includes an error ID for tracking."""
        middleware = ErrorTrackingMiddleware(MagicMock())

        async def exception_call_next(request):
            raise RuntimeError("Something went wrong")

        response = await middleware.dispatch(mock_request, exception_call_next)

        assert response.status_code == 500
        # Check that X-Error-ID header is present
        assert "X-Error-ID" in response.headers

    @pytest.mark.asyncio
    async def test_exception_response_includes_request_id(self, mock_request):
        """Test that exception response includes request ID for correlation."""
        middleware = ErrorTrackingMiddleware(MagicMock())

        # Set a request ID
        token = request_id_var.set("test-request-123")

        async def exception_call_next(request):
            raise RuntimeError("Something went wrong")

        try:
            response = await middleware.dispatch(mock_request, exception_call_next)

            assert response.status_code == 500
            assert "X-Request-ID" in response.headers
            assert response.headers["X-Request-ID"] == "test-request-123"
        finally:
            request_id_var.reset(token)

    @pytest.mark.asyncio
    async def test_http_exception_is_reraised(self, mock_request):
        """Test that HTTPException is re-raised, not caught."""
        from fastapi import HTTPException

        middleware = ErrorTrackingMiddleware(MagicMock())

        async def http_exception_call_next(request):
            raise HTTPException(status_code=403, detail="Forbidden")

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, http_exception_call_next)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_extracts_user_id_from_jwt(self, mock_request):
        """Test that user ID is extracted from JWT for logging."""
        middleware = ErrorTrackingMiddleware(MagicMock())

        # Add auth header
        mock_request.headers = Headers({"Authorization": "Bearer test-token"})

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {}

        async def server_error_call_next(request):
            return mock_response

        with patch("app.core.security.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": "user-123"}

            with patch("app.core.middleware.logger") as mock_logger:
                await middleware.dispatch(mock_request, server_error_call_next)

                # Check that logger was called with user_id
                call_kwargs = mock_logger.error.call_args[1]
                assert call_kwargs.get("user_id") == "user-123"

    @pytest.mark.asyncio
    async def test_handles_decode_token_failure(self, mock_request):
        """Test that middleware handles JWT decode failures gracefully."""
        middleware = ErrorTrackingMiddleware(MagicMock())

        # Add invalid auth header
        mock_request.headers = Headers({"Authorization": "Bearer invalid-token"})

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {}

        async def server_error_call_next(request):
            return mock_response

        with patch("app.core.security.decode_token") as mock_decode:
            mock_decode.side_effect = Exception("Invalid token")

            # Should not raise, just proceed without user_id
            response = await middleware.dispatch(mock_request, server_error_call_next)

            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_development_mode_includes_error_details(self, mock_request):
        """Test that development mode includes error details in response."""
        middleware = ErrorTrackingMiddleware(MagicMock())

        async def exception_call_next(request):
            raise ValueError("Detailed error message")

        with patch("app.core.middleware.settings") as mock_settings:
            mock_settings.is_development = True

            response = await middleware.dispatch(mock_request, exception_call_next)

            assert response.status_code == 500
            # In dev mode, response body should include error details
            # Response is JSONResponse, so body is accessible
            import json
            body = json.loads(response.body.decode())
            assert body.get("error_type") == "ValueError"
            assert "error_message" in body

    @pytest.mark.asyncio
    async def test_production_mode_hides_error_details(self, mock_request):
        """Test that production mode hides error details in response."""
        middleware = ErrorTrackingMiddleware(MagicMock())

        async def exception_call_next(request):
            raise ValueError("Sensitive error message")

        with patch("app.core.middleware.settings") as mock_settings:
            mock_settings.is_development = False

            response = await middleware.dispatch(mock_request, exception_call_next)

            assert response.status_code == 500
            import json
            body = json.loads(response.body.decode())
            # Should not include sensitive details
            assert "error_type" not in body
            assert "error_message" not in body
            # Should include generic message and error_id
            assert "detail" in body
            assert "error_id" in body
