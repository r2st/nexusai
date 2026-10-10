"""Middleware for scalability, security, and observability.

Provides:
- Rate limiting middleware
- Request ID tracking
- Response time logging
- Circuit breaker pattern
- Tenant context injection
- Error tracking and observability
"""

import time
import uuid
import traceback
from typing import Callable, Any
from contextvars import ContextVar

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Context variables for request tracking
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for tracing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(request_id)

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class ResponseTimeMiddleware(BaseHTTPMiddleware):
    """Track and log response times."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        response = await call_next(request)

        process_time = (time.perf_counter() - start_time) * 1000  # ms
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        path = request.url.path
        if path not in ("/health", "/healthz", "/api/health", "/api/healthz"):
            log_data = {
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round(process_time, 2),
            }
            if process_time > 1000:
                logger.warning("Slow request detected", **log_data)
            elif process_time > 500:
                logger.info("Request completed (slow)", **log_data)
            else:
                logger.debug("Request completed", **log_data)

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis."""

    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/api/v1/health", "/health", "/healthz"]:
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)

        # Check rate limit
        try:
            from app.core.cache import api_rate_limiter

            allowed, info = await api_rate_limiter.is_allowed(client_id)

            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded",
                        "retry_after": info["reset_in"],
                    },
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": str(info["remaining"]),
                        "X-RateLimit-Reset": str(info["reset_in"]),
                        "Retry-After": str(info["reset_in"]),
                    },
                )

            response = await call_next(request)

            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset_in"])

            return response

        except Exception as e:
            logger.debug("Rate limiter unavailable, failing open", error=str(e))
            return await call_next(request)

    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier for rate limiting."""
        # Try to get user ID from auth header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Use token hash as identifier (more stable than IP)
            import hashlib
            token = auth_header[7:]
            return f"token:{hashlib.sha256(token.encode()).hexdigest()[:16]}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        return f"ip:{request.client.host if request.client else 'unknown'}"


class TenantMiddleware(BaseHTTPMiddleware):
    """Extract and validate tenant context from requests.

    This middleware extracts tenant context from multiple sources:
    1. X-Tenant-ID header (explicit)
    2. X-Organization-ID header (alias)
    3. JWT token claims (if available)

    The tenant ID is stored in a context variable for access throughout
    the request lifecycle.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract tenant ID from various sources
        tenant_id = self._extract_tenant_id(request)

        if tenant_id:
            tenant_id_var.set(tenant_id)
            structlog.contextvars.bind_contextvars(tenant_id=tenant_id)

            from app.core.multitenancy import set_current_tenant_id
            set_current_tenant_id(tenant_id)

        response = await call_next(request)

        # Add tenant ID to response headers for debugging
        if tenant_id:
            response.headers["X-Tenant-ID"] = tenant_id

        return response

    def _extract_tenant_id(self, request: Request) -> str | None:
        """Extract tenant ID from request."""
        # Priority 1: Explicit header
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id

        # Priority 2: Organization ID header (alias)
        tenant_id = request.headers.get("X-Organization-ID")
        if tenant_id:
            return tenant_id

        # Priority 3: Try to extract from JWT claims
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_token
                token = auth_header[7:]
                payload = decode_token(token)
                if payload and "tenant_id" in payload:
                    return payload["tenant_id"]
                if payload and "organization_id" in payload:
                    return payload["organization_id"]
            except Exception as e:
                logger.debug("Failed to extract tenant from JWT", error=str(e))

        return None


class TenantRateLimitMiddleware(BaseHTTPMiddleware):
    """Per-tenant rate limiting middleware.

    This provides fair usage across tenants by applying rate limits
    at the tenant level, not just per-user.
    """

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute_per_tenant: int = 1000,
        requests_per_minute_per_user: int = 100,
    ):
        super().__init__(app)
        self.tenant_limit = requests_per_minute_per_tenant
        self.user_limit = requests_per_minute_per_user

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip for health checks
        if request.url.path in ["/api/v1/health", "/health", "/healthz"]:
            return await call_next(request)

        tenant_id = tenant_id_var.get()
        if not tenant_id:
            # No tenant context, fall back to global rate limit
            return await call_next(request)

        try:
            from app.core.cache import tenant_rate_limiter

            # Check tenant-level rate limit
            allowed, info = await tenant_rate_limiter.is_allowed(
                identifier="tenant",
                tenant_id=tenant_id,
            )

            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Tenant rate limit exceeded",
                        "retry_after": info.get("reset_in", 60),
                    },
                    headers={
                        "X-RateLimit-Limit": str(info.get("limit", self.tenant_limit)),
                        "X-RateLimit-Remaining": str(info.get("remaining", 0)),
                        "Retry-After": str(info.get("reset_in", 60)),
                        "X-RateLimit-Scope": "tenant",
                    },
                )

            response = await call_next(request)
            return response

        except Exception as e:
            logger.debug("Tenant rate limiter unavailable, failing open", tenant_id=tenant_id, error=str(e))
            return await call_next(request)


class CircuitBreaker:
    """Circuit breaker pattern for external service calls.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is failing, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout

        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0

    @property
    def state(self) -> str:
        """Get current circuit state."""
        if self._state == self.OPEN:
            # Check if timeout has passed
            if time.time() - self._last_failure_time > self.timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
        return self._state

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == self.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = self.CLOSED
                self._failure_count = 0
        elif self._state == self.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == self.HALF_OPEN:
            self._state = self.OPEN
        elif self._failure_count >= self.failure_threshold:
            self._state = self.OPEN

    def is_available(self) -> bool:
        """Check if circuit allows requests."""
        return self.state != self.OPEN

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if not self.is_available():
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is open"
            )

        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Pre-configured circuit breakers for external services
circuit_breakers: dict[str, CircuitBreaker] = {
    "devlake": CircuitBreaker("devlake", failure_threshold=5, timeout=60),
    "openbao": CircuitBreaker("openbao", failure_threshold=3, timeout=30),
    "openfga": CircuitBreaker("openfga", failure_threshold=3, timeout=30),
    "clickhouse": CircuitBreaker("clickhouse", failure_threshold=5, timeout=60),
    "openai": CircuitBreaker("openai", failure_threshold=3, timeout=120),
    "anthropic": CircuitBreaker("anthropic", failure_threshold=3, timeout=120),
}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in circuit_breakers:
        circuit_breakers[name] = CircuitBreaker(name)
    return circuit_breakers[name]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


class CompressionMiddleware(BaseHTTPMiddleware):
    """Handle response compression for large payloads."""

    MIN_SIZE = 1000  # Minimum size to compress (bytes)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Check if client accepts gzip
        accept_encoding = request.headers.get("Accept-Encoding", "")

        if "gzip" in accept_encoding.lower():
            response.headers["Vary"] = "Accept-Encoding"

        return response


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """Track and log errors with observability integration.

    Captures unhandled exceptions and logs them with:
    - Request context (method, path, user, tenant)
    - Error details (type, message, stacktrace)
    - Correlation IDs for tracing

    Integrates with Langfuse for LLM-related error tracking.
    """

    _SKIP_PATHS = frozenset(("/", "/health", "/healthz", "/favicon.ico"))

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)

        request_id = request_id_var.get() or str(uuid.uuid4())
        tenant_id = tenant_id_var.get()

        user_id = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_token
                token = auth_header[7:]
                payload = decode_token(token)
                if payload:
                    user_id = payload.get("sub")
            except Exception as e:
                logger.debug("Failed to extract user from JWT for audit", error=str(e))

        try:
            response = await call_next(request)

            # Log 4xx/5xx responses for monitoring
            if response.status_code >= 400:
                log_data = {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                }

                if response.status_code >= 500:
                    logger.error("Server error response", **log_data)
                else:
                    logger.warning("Client error response", **log_data)

            return response

        except HTTPException:
            # Let FastAPI handle HTTP exceptions normally
            raise

        except Exception as e:
            # Log unhandled exceptions with full context
            error_id = str(uuid.uuid4())[:8]  # Short ID for user reference

            logger.error(
                "Unhandled exception in request",
                error_id=error_id,
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                query_params=str(request.query_params),
                user_id=user_id,
                tenant_id=tenant_id,
                error_type=type(e).__name__,
                error_message=str(e),
                traceback=traceback.format_exc(),
            )

            try:
                from app.services.observability.service import _observability_service
                if _observability_service:
                    _observability_service.metrics.record_http_request(
                        method=request.method,
                        endpoint=request.url.path,
                        status=500,
                        duration_ms=0,
                    )
            except Exception as obs_err:
                logger.debug("Failed to record error in observability service", error=str(obs_err))

            # Return a generic error response
            error_response = {
                "detail": "An internal error occurred",
                "error_id": error_id,
            }

            # Include more details in development mode
            if settings.is_development:
                error_response["error_type"] = type(e).__name__
                error_response["error_message"] = str(e)

            return JSONResponse(
                status_code=500,
                content=error_response,
                headers={
                    "X-Request-ID": request_id,
                    "X-Error-ID": error_id,
                },
            )
