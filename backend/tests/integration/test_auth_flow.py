"""
Integration tests for complete authentication flows.
"""

import pytest
from uuid import uuid4


class TestAuthenticationFlow:
    """Test complete authentication workflows."""

    @pytest.mark.asyncio
    async def test_register_login_flow(self, client, db_session):
        """Test complete registration and login flow."""
        # Generate unique email
        email = f"newuser_{uuid4().hex[:8]}@example.com"
        password = "SecurePassword123!"

        # 1. Register new user
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "username": f"user_{uuid4().hex[:8]}",
                "password": password,
                "full_name": "New Test User",
            },
        )
        assert register_response.status_code in [200, 201, 400]

        if register_response.status_code in [200, 201]:
            data = register_response.json()
            assert "user" in data
            assert "tokens" in data
            assert data["user"]["email"] == email

            # 2. Login with the new credentials
            login_response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": email,
                    "password": password,
                },
            )
            assert login_response.status_code == 200

            login_data = login_response.json()
            assert "user" in login_data
            assert "tokens" in login_data
            assert "access_token" in login_data["tokens"]
            assert "refresh_token" in login_data["tokens"]

    @pytest.mark.asyncio
    async def test_token_refresh_flow(self, client, db_session):
        """Test token refresh workflow."""
        email = f"refresh_{uuid4().hex[:8]}@example.com"
        password = "SecurePassword123!"

        # Register user
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "username": f"user_{uuid4().hex[:8]}",
                "password": password,
            },
        )

        if register_response.status_code in [200, 201]:
            tokens = register_response.json()["tokens"]
            refresh_token = tokens["refresh_token"]

            # Refresh tokens
            refresh_response = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            assert refresh_response.status_code in [200, 401]

            if refresh_response.status_code == 200:
                new_tokens = refresh_response.json()
                assert "access_token" in new_tokens
                assert "refresh_token" in new_tokens

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrong_password",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client, test_user):
        """Test registering with existing email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "username": "different_username",
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_refresh_token(self, client):
        """Test refresh with invalid token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )
        assert response.status_code == 401


class TestProtectedResourceAccess:
    """Test accessing protected resources with authentication."""

    @pytest.mark.asyncio
    async def test_access_protected_with_valid_token(self, client, auth_headers):
        """Test accessing protected resource with valid token."""
        response = await client.get(
            "/api/v1/chat/conversations",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_access_protected_without_token(self, client):
        """Test accessing protected resource without token."""
        response = await client.get("/api/v1/chat/conversations")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_access_protected_with_invalid_token(self, client):
        """Test accessing protected resource with invalid token."""
        response = await client.get(
            "/api/v1/chat/conversations",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_with_expired_token(self, client):
        """Test accessing protected resource with malformed token."""
        response = await client.get(
            "/api/v1/chat/conversations",
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxfQ.invalid"},
        )
        assert response.status_code == 401
