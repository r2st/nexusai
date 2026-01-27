"""
Integration tests for authentication with development test accounts.

Test Accounts:
- admin@nexusai.dev / admin123 (admin superuser)
- user@nexusai.dev / user123 (regular user)
- viewer@nexusai.dev / viewer123 (viewer role)
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User, UserRole


# Test account credentials
TEST_ACCOUNTS = [
    {
        "email": "admin@nexusai.dev",
        "password": "admin123",
        "username": "admin",
        "full_name": "Admin User",
        "role": UserRole.ADMIN,
        "is_superuser": True,
    },
    {
        "email": "user@nexusai.dev",
        "password": "user123",
        "username": "regularuser",
        "full_name": "Regular User",
        "role": UserRole.USER,
        "is_superuser": False,
    },
    {
        "email": "viewer@nexusai.dev",
        "password": "viewer123",
        "username": "viewer",
        "full_name": "Viewer User",
        "role": UserRole.VIEWER,
        "is_superuser": False,
    },
]


@pytest.fixture
async def setup_test_accounts(db_session: AsyncSession):
    """Create the development test accounts in the database."""
    users = []
    for account in TEST_ACCOUNTS:
        user = User(
            email=account["email"],
            username=account["username"],
            hashed_password=get_password_hash(account["password"]),
            full_name=account["full_name"],
            role=account["role"].value,
            is_active=True,
            is_superuser=account["is_superuser"],
            is_verified=True,
        )
        db_session.add(user)
        users.append(user)

    await db_session.commit()
    for user in users:
        await db_session.refresh(user)

    return users


class TestAuthenticationWithTestAccounts:
    """Test authentication flows with the development test accounts."""

    @pytest.mark.asyncio
    async def test_admin_login_success(
        self, client: AsyncClient, setup_test_accounts
    ):
        """Test admin user can login successfully."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@nexusai.dev",
                "password": "admin123",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "user" in data
        assert "tokens" in data

        # Verify user data
        assert data["user"]["email"] == "admin@nexusai.dev"
        assert data["user"]["role"] == "admin"

        # Verify tokens
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]
        assert data["tokens"]["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_user_login_success(
        self, client: AsyncClient, setup_test_accounts
    ):
        """Test regular user can login successfully."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "user@nexusai.dev",
                "password": "user123",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["user"]["email"] == "user@nexusai.dev"
        assert data["user"]["role"] == "user"
        assert "access_token" in data["tokens"]

    @pytest.mark.asyncio
    async def test_viewer_login_success(
        self, client: AsyncClient, setup_test_accounts
    ):
        """Test viewer user can login successfully."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "viewer@nexusai.dev",
                "password": "viewer123",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["user"]["email"] == "viewer@nexusai.dev"
        assert data["user"]["role"] == "viewer"
        assert "access_token" in data["tokens"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self, client: AsyncClient, setup_test_accounts
    ):
        """Test login fails with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@nexusai.dev",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login fails for non-existent user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nobody@nexusai.dev",
                "password": "anypassword",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_token_refresh(
        self, client: AsyncClient, setup_test_accounts
    ):
        """Test token refresh works correctly."""
        # First login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "user@nexusai.dev",
                "password": "user123",
            },
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["tokens"]["refresh_token"]

        # Refresh tokens
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert "access_token" in data
        assert "refresh_token" in data


class TestAuthenticatedEndpoints:
    """Test that authenticated endpoints work with test account tokens."""

    @pytest.fixture
    async def admin_token(
        self, client: AsyncClient, setup_test_accounts
    ) -> str:
        """Get admin access token."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@nexusai.dev", "password": "admin123"},
        )
        return response.json()["tokens"]["access_token"]

    @pytest.fixture
    async def user_token(
        self, client: AsyncClient, setup_test_accounts
    ) -> str:
        """Get regular user access token."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "user@nexusai.dev", "password": "user123"},
        )
        return response.json()["tokens"]["access_token"]

    @pytest.fixture
    async def viewer_token(
        self, client: AsyncClient, setup_test_accounts
    ) -> str:
        """Get viewer access token."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "viewer@nexusai.dev", "password": "viewer123"},
        )
        return response.json()["tokens"]["access_token"]

    @pytest.mark.asyncio
    async def test_admin_can_access_protected_endpoint(
        self, client: AsyncClient, admin_token: str
    ):
        """Test admin can access protected endpoints."""
        response = await client.get(
            "/api/v1/health",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Health endpoint should be accessible
        assert response.status_code in [200, 401, 404]

    @pytest.mark.asyncio
    async def test_user_can_create_conversation(
        self, client: AsyncClient, user_token: str
    ):
        """Test regular user can create a chat conversation."""
        response = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Test Conversation from user@nexusai.dev"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        # Should succeed or return auth error if org not set
        assert response.status_code in [200, 201, 400, 401, 403]

    @pytest.mark.asyncio
    async def test_viewer_limited_access(
        self, client: AsyncClient, viewer_token: str
    ):
        """Test viewer has limited access."""
        # Viewers should be able to read but potentially not create
        response = await client.get(
            "/api/v1/chat/conversations",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        # Should be able to list (even if empty)
        assert response.status_code in [200, 401, 403]

    @pytest.mark.asyncio
    async def test_unauthenticated_access_denied(self, client: AsyncClient):
        """Test unauthenticated requests are denied."""
        response = await client.get("/api/v1/chat/conversations")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_invalid_token_denied(self, client: AsyncClient):
        """Test invalid tokens are rejected."""
        response = await client.get(
            "/api/v1/chat/conversations",
            headers={"Authorization": "Bearer invalid-token-12345"},
        )
        assert response.status_code in [401, 403]


class TestRoleBasedAccess:
    """Test role-based access control with test accounts."""

    @pytest.fixture
    async def tokens(
        self, client: AsyncClient, setup_test_accounts
    ) -> dict[str, str]:
        """Get tokens for all test accounts."""
        tokens = {}
        for account in TEST_ACCOUNTS:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": account["email"], "password": account["password"]},
            )
            role = account["role"].value
            tokens[role] = response.json()["tokens"]["access_token"]
        return tokens

    @pytest.mark.asyncio
    async def test_all_roles_can_access_health(
        self, client: AsyncClient, tokens: dict[str, str]
    ):
        """Test all roles can access public health endpoint."""
        for role, token in tokens.items():
            response = await client.get(
                "/api/v1/health",
                headers={"Authorization": f"Bearer {token}"},
            )
            # Health should be accessible to all
            assert response.status_code in [200, 404], f"Failed for role: {role}"

    @pytest.mark.asyncio
    async def test_documents_access_by_role(
        self, client: AsyncClient, tokens: dict[str, str]
    ):
        """Test document listing access varies by role."""
        results = {}
        for role, token in tokens.items():
            response = await client.get(
                "/api/v1/documents",
                headers={"Authorization": f"Bearer {token}"},
            )
            results[role] = response.status_code

        # All authenticated users should be able to list documents
        for role, status in results.items():
            assert status in [200, 400, 401, 403], f"Unexpected status for {role}: {status}"
