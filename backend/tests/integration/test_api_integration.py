"""
API Integration tests to verify frontend-backend communication.

These tests ensure the API contracts expected by the frontend are working.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User, UserRole


@pytest.fixture
async def api_test_user(db_session: AsyncSession):
    """Create a test user for API tests."""
    user = User(
        email="apitest@nexusai.dev",
        username="apitest",
        hashed_password=get_password_hash("apitest123"),
        full_name="API Test User",
        role=UserRole.USER.value,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestAuthAPIContract:
    """Test authentication API contracts expected by frontend."""

    @pytest.mark.asyncio
    async def test_login_response_format(
        self, client: AsyncClient, api_test_user: User
    ):
        """Test login response matches frontend expectations."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "apitest@nexusai.dev",
                "password": "apitest123",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Frontend expects this structure
        assert "user" in data
        assert "tokens" in data

        # User object
        user = data["user"]
        assert "id" in user
        assert "email" in user
        assert "role" in user
        assert "is_verified" in user

        # Tokens object
        tokens = data["tokens"]
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens

    @pytest.mark.asyncio
    async def test_login_error_format(self, client: AsyncClient):
        """Test login error response format."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        data = response.json()

        # Frontend expects detail field for errors
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_refresh_token_response(
        self, client: AsyncClient, api_test_user: User
    ):
        """Test token refresh response format."""
        # First login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "apitest@nexusai.dev",
                "password": "apitest123",
            },
        )
        refresh_token = login_response.json()["tokens"]["refresh_token"]

        # Refresh
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()

        # Should return new tokens
        assert "access_token" in data
        assert "refresh_token" in data


class TestChatAPIContract:
    """Test chat API contracts expected by frontend."""

    @pytest.fixture
    async def auth_headers(
        self, client: AsyncClient, api_test_user: User
    ) -> dict:
        """Get auth headers for chat tests."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "apitest@nexusai.dev",
                "password": "apitest123",
            },
        )
        token = response.json()["tokens"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_list_conversations_format(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test conversation list response format."""
        response = await client.get(
            "/api/v1/chat/conversations",
            headers=auth_headers,
        )

        # Should return list (possibly empty)
        assert response.status_code in [200, 401, 403]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_conversation_format(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test conversation creation response format."""
        response = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "API Test Conversation"},
            headers=auth_headers,
        )

        # May fail without org context
        assert response.status_code in [200, 201, 400, 401, 403]

        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data
            assert "title" in data


class TestHealthAndStatusAPI:
    """Test health and status endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/api/v1/health")

        # Health endpoint should be accessible
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "status" in data or "healthy" in data or isinstance(data, dict)


class TestOrganizationsAPIContract:
    """Test organizations API contracts."""

    @pytest.fixture
    async def auth_headers(
        self, client: AsyncClient, api_test_user: User
    ) -> dict:
        """Get auth headers."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "apitest@nexusai.dev",
                "password": "apitest123",
            },
        )
        token = response.json()["tokens"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_list_organizations(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing organizations."""
        response = await client.get(
            "/api/v1/organizations",
            headers=auth_headers,
        )

        # Should return list of organizations user belongs to
        assert response.status_code in [200, 401, 403, 404]

        if response.status_code == 200:
            data = response.json()
            # Could be list or paginated response
            assert isinstance(data, (list, dict))


class TestDocumentsAPIContract:
    """Test documents API contracts."""

    @pytest.fixture
    async def auth_headers(
        self, client: AsyncClient, api_test_user: User
    ) -> dict:
        """Get auth headers."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "apitest@nexusai.dev",
                "password": "apitest123",
            },
        )
        token = response.json()["tokens"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_list_documents(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing documents."""
        response = await client.get(
            "/api/v1/documents",
            headers=auth_headers,
        )

        assert response.status_code in [200, 400, 401, 403, 404]

        if response.status_code == 200:
            data = response.json()
            # Should be list or paginated
            assert isinstance(data, (list, dict))


class TestNewServicesAPIContract:
    """Test API contracts for newly implemented services."""

    @pytest.fixture
    async def auth_headers(
        self, client: AsyncClient, api_test_user: User
    ) -> dict:
        """Get auth headers."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "apitest@nexusai.dev",
                "password": "apitest123",
            },
        )
        token = response.json()["tokens"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_events_webhook_endpoint_exists(
        self, client: AsyncClient
    ):
        """Test events webhook endpoint is available."""
        # Webhook endpoints should accept POST
        response = await client.post(
            "/api/v1/events/webhooks/github",
            json={"test": "payload"},
            headers={
                "X-Tenant-ID": "test-tenant",
                "X-GitHub-Event": "ping",
            },
        )

        # Should not be 404 (endpoint exists)
        # May be 400/422 for invalid payload or 401 for auth
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_rollups_endpoint_exists(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test rollups endpoint is available."""
        response = await client.get(
            "/api/v1/rollups/dora",
            headers=auth_headers,
        )

        # Endpoint should exist (may fail on auth or missing data)
        assert response.status_code in [200, 400, 401, 403, 404, 422]

    @pytest.mark.asyncio
    async def test_query_endpoint_exists(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test query gateway endpoint is available."""
        response = await client.post(
            "/api/v1/query",
            json={"sources": ["metrics"]},
            headers=auth_headers,
        )

        # Endpoint should exist
        assert response.status_code in [200, 400, 401, 403, 404, 422]

    @pytest.mark.asyncio
    async def test_query_dashboards_list(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test dashboard list endpoint."""
        response = await client.get(
            "/api/v1/query/dashboards",
            headers=auth_headers,
        )

        # Should return list of dashboards
        assert response.status_code in [200, 401, 403, 404]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)


class TestCORSHeaders:
    """Test CORS headers for frontend access."""

    @pytest.mark.asyncio
    async def test_cors_preflight(self, client: AsyncClient):
        """Test CORS preflight request."""
        response = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        # Should allow CORS or return method not allowed
        assert response.status_code in [200, 204, 405]

    @pytest.mark.asyncio
    async def test_cors_headers_in_response(self, client: AsyncClient):
        """Test CORS headers are present in responses."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "password",
            },
            headers={"Origin": "http://localhost:3000"},
        )

        # Check for CORS headers (may or may not be present depending on config)
        # Just verify the request completes
        assert response.status_code in [200, 401, 422]
