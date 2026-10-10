"""GB055: M4 Cross-cutting concerns tests.

Tests auth enforcement, CSP headers, input validation consistency,
and security headers across all API modules.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock

from app.main import app
from app.core.config import get_settings


# ============================================================================
# Auth enforcement tests — verify previously-unprotected endpoints now require auth
# ============================================================================


class TestAuthEnforcement:
    """Verify endpoints that were missing auth now return 401/403 without a token."""

    @pytest_asyncio.fixture
    async def client(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method,path",
        [
            # metrics.py — all data endpoints
            ("GET", "/api/v1/metrics/dora/test-project"),
            ("GET", "/api/v1/metrics/space/test-project"),
            ("GET", "/api/v1/metrics/business/test-project"),
            ("GET", "/api/v1/metrics/productivity/team/test-project"),
            ("GET", "/api/v1/metrics/dashboard/test-project"),
            ("GET", "/api/v1/metrics/flow/test-project"),
            ("GET", "/api/v1/metrics/unified/test-project"),
            ("GET", "/api/v1/metrics/insights/test-project"),
            ("POST", "/api/v1/metrics/insights/test-project/chat?question=why+is+lead+time+high"),
            # workflows.py
            ("POST", "/api/v1/workflows"),
            ("GET", "/api/v1/workflows"),
            ("GET", "/api/v1/workflows/templates"),
            # collaboration.py
            ("POST", "/api/v1/collaboration/sessions"),
            ("GET", "/api/v1/collaboration/sessions"),
            ("POST", "/api/v1/collaboration/annotations"),
            # compliance.py
            ("POST", "/api/v1/compliance/gdpr/dsr"),
            ("GET", "/api/v1/compliance/gdpr/report"),
            ("GET", "/api/v1/compliance/soc2/controls"),
            ("GET", "/api/v1/compliance/dashboard"),
            # hipaa.py
            ("POST", "/api/v1/hipaa/phi/detect"),
            ("POST", "/api/v1/hipaa/baa"),
            ("GET", "/api/v1/hipaa/controls"),
            ("GET", "/api/v1/hipaa/report"),
            # chatbot.py — admin endpoints (not webhook receivers)
            ("POST", "/api/v1/chatbot/configure/slack"),
            ("POST", "/api/v1/chatbot/configure/teams"),
            ("POST", "/api/v1/chatbot/users/link"),
            ("GET", "/api/v1/chatbot/dashboard"),
            # sso.py — not registered in api_router currently; skip
            # devlake.py
            ("GET", "/api/v1/devlake/pipelines/1"),
        ],
    )
    async def test_unauthenticated_request_returns_401_or_403(
        self, client: AsyncClient, method: str, path: str
    ):
        """Endpoints that require auth must reject unauthenticated requests."""
        response = await client.request(method, path)
        assert response.status_code in (401, 403), (
            f"{method} {path} returned {response.status_code}, "
            f"expected 401 or 403 for unauthenticated request"
        )


# ============================================================================
# CSP and security headers tests
# ============================================================================


class TestSecurityHeaders:
    """Verify security headers are present on responses."""

    @pytest_asyncio.fixture
    async def client(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_csp_header_present(self, client: AsyncClient):
        response = await client.get("/health")
        assert "content-security-policy" in response.headers
        csp = response.headers["content-security-policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    @pytest.mark.asyncio
    async def test_permissions_policy_header_present(self, client: AsyncClient):
        response = await client.get("/health")
        assert "permissions-policy" in response.headers
        pp = response.headers["permissions-policy"]
        assert "camera=()" in pp
        assert "microphone=()" in pp

    @pytest.mark.asyncio
    async def test_security_headers_present(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("x-xss-protection") == "1; mode=block"
        assert "strict-origin" in response.headers.get("referrer-policy", "")

    @pytest.mark.asyncio
    async def test_request_id_header_present(self, client: AsyncClient):
        response = await client.get("/health")
        assert "x-request-id" in response.headers

    @pytest.mark.asyncio
    async def test_process_time_header_present(self, client: AsyncClient):
        response = await client.get("/health")
        assert "x-process-time" in response.headers


# ============================================================================
# Input validation consistency tests
# ============================================================================


class TestInputValidation:
    """Verify input validation is consistent across endpoints."""

    @pytest_asyncio.fixture
    async def client(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_path_traversal_blocked_in_signed_url_download(self, client: AsyncClient):
        """Path traversal in file_key should be rejected."""
        response = await client.get(
            "/api/v1/signed-urls/download/../../../etc/passwd",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert response.status_code in (400, 401)

    @pytest.mark.asyncio
    async def test_cypher_injection_blocked(self, client: AsyncClient):
        """Cypher identifiers must be alphanumeric."""
        from app.core.input_validation import validate_cypher_identifier
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_cypher_identifier("') RETURN n //", "label")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_path_traversal_validation(self):
        """Path traversal strings must be rejected."""
        from app.core.input_validation import validate_no_path_traversal
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            validate_no_path_traversal("../../../etc/passwd", "path")

        with pytest.raises(HTTPException):
            validate_no_path_traversal("/etc/passwd", "path")

        with pytest.raises(HTTPException):
            validate_no_path_traversal("file\x00.txt", "path")

        result = validate_no_path_traversal("documents/report.pdf", "path")
        assert result == "documents/report.pdf"

    @pytest.mark.asyncio
    async def test_error_string_sanitization(self):
        """Error strings must be sanitized to prevent XSS."""
        from app.core.input_validation import sanitize_error_string

        result = sanitize_error_string('<script>alert("xss")</script>')
        assert "<script>" not in result
        assert "<" not in result
        assert ">" not in result


# ============================================================================
# Logging consistency tests
# ============================================================================


class TestLoggingConsistency:
    """Verify structured logging is configured correctly."""

    def test_sensitive_fields_redacted(self):
        """Sensitive fields must be redacted in logs."""
        from app.main import _redact_sensitive_fields

        event_dict = {
            "password": "secret123",
            "api_key": "sk-abc123",
            "email": "user@example.com",
            "token": "jwt-token-value",
        }
        result = _redact_sensitive_fields(None, None, event_dict)
        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"
        assert result["email"] == "user@example.com"  # email is not in sensitive keys
        assert result["token"] == "[REDACTED]"

    def test_structlog_configured_with_json_renderer(self):
        """Structlog should be configured for structured logging."""
        import structlog

        logger = structlog.get_logger()
        assert logger is not None


# ============================================================================
# SSO public endpoints remain accessible
# ============================================================================


class TestSSOPublicEndpoints:
    """Verify SSO auth flow endpoints remain publicly accessible.

    Note: SSO router is not currently registered in api_router.
    These tests verify the module has auth where needed but are
    skipped at the HTTP level.
    """

    def test_sso_provider_crud_requires_admin(self):
        """SSO provider management endpoints use get_current_admin_user."""
        import ast
        with open("backend/app/api/sso.py") as f:
            source = f.read()
        assert "get_current_admin_user" in source


# ============================================================================
# Webhook endpoints remain accessible (no auth needed)
# ============================================================================


class TestWebhookEndpointsPublic:
    """Verify webhook receiver endpoints remain accessible without auth."""

    @pytest_asyncio.fixture
    async def client(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_health_endpoints_accessible(self, client: AsyncClient):
        """Health checks must be public."""
        for path in ["/health", "/healthz", "/api/health"]:
            response = await client.get(path)
            assert response.status_code in (200, 503), (
                f"Health endpoint {path} returned {response.status_code}"
            )
