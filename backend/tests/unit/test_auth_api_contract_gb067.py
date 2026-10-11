"""GB067: API contract tests for auth endpoints — request validation and response schema.

Tests Pydantic model validation for RegisterRequest, LoginRequest, RefreshRequest,
and the auth rate limiter dependency, all without requiring a database.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.api.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    UserResponse,
    AuthResponse,
)


# ---------------------------------------------------------------------------
# RegisterRequest validation
# ---------------------------------------------------------------------------

class TestRegisterRequestValidation:
    def test_valid_request(self):
        req = RegisterRequest(
            email="user@example.com",
            username="testuser",
            password="SecureP@ss1",
            full_name="Test User",
        )
        assert req.email == "user@example.com"

    def test_email_required(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="user", password="SecureP@ss1")

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="not-an-email",
                username="user",
                password="SecureP@ss1",
            )

    def test_username_min_length(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="u@e.com", username="ab", password="SecureP@ss1"
            )

    def test_username_max_length(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="u@e.com", username="x" * 51, password="SecureP@ss1"
            )

    def test_username_valid_characters(self):
        req = RegisterRequest(
            email="u@e.com", username="user-name_1", password="SecureP@ss1"
        )
        assert req.username == "user-name_1"

    def test_username_rejects_special_chars(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="u@e.com", username="user@name", password="SecureP@ss1"
            )

    def test_username_rejects_spaces(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="u@e.com", username="user name", password="SecureP@ss1"
            )

    def test_password_min_length(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="u@e.com", username="user", password="short"
            )

    def test_password_max_length(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="u@e.com", username="user", password="x" * 129
            )

    def test_full_name_optional(self):
        req = RegisterRequest(
            email="u@e.com", username="user", password="SecureP@ss1"
        )
        assert req.full_name is None

    def test_full_name_max_length(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="u@e.com",
                username="user",
                password="SecureP@ss1",
                full_name="x" * 201,
            )


# ---------------------------------------------------------------------------
# LoginRequest validation
# ---------------------------------------------------------------------------

class TestLoginRequestValidation:
    def test_valid_request(self):
        req = LoginRequest(email="u@e.com", password="pass")
        assert req.email == "u@e.com"

    def test_email_required(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="pass")

    def test_password_required(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="u@e.com")

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="bad", password="pass")


# ---------------------------------------------------------------------------
# RefreshRequest validation
# ---------------------------------------------------------------------------

class TestRefreshRequestValidation:
    def test_valid_request(self):
        req = RefreshRequest(refresh_token="some-token")
        assert req.refresh_token == "some-token"

    def test_refresh_token_required(self):
        with pytest.raises(ValidationError):
            RefreshRequest()


# ---------------------------------------------------------------------------
# UserResponse schema
# ---------------------------------------------------------------------------

class TestUserResponseSchema:
    def test_all_fields_present(self):
        resp = UserResponse(
            id="u1",
            email="u@e.com",
            username="user1",
            full_name="User One",
            role="user",
            is_verified=True,
            organization_id=None,
        )
        assert resp.id == "u1"
        assert resp.organization_id is None

    def test_organization_id_optional(self):
        resp = UserResponse(
            id="u1",
            email="u@e.com",
            username="user1",
            full_name=None,
            role="admin",
            is_verified=False,
        )
        assert resp.organization_id is None

    def test_from_attributes_enabled(self):
        assert UserResponse.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# Auth rate limiter dependency
# ---------------------------------------------------------------------------

class TestAuthRateLimit:
    @pytest.mark.asyncio
    async def test_allowed_passes(self):
        from app.api.auth import _check_auth_rate_limit

        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        with patch("app.core.cache.auth_rate_limiter") as mock_rl:
            mock_rl.is_allowed = AsyncMock(return_value=(True, {"remaining": 5}))
            await _check_auth_rate_limit(request)

    @pytest.mark.asyncio
    async def test_blocked_raises_429(self):
        from fastapi import HTTPException
        from app.api.auth import _check_auth_rate_limit

        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        with patch("app.core.cache.auth_rate_limiter") as mock_rl:
            mock_rl.is_allowed = AsyncMock(
                return_value=(False, {"reset_in": 30})
            )
            with pytest.raises(HTTPException) as exc:
                await _check_auth_rate_limit(request)
            assert exc.value.status_code == 429
            assert exc.value.headers["Retry-After"] == "30"

    @pytest.mark.asyncio
    async def test_uses_x_forwarded_for(self):
        from app.api.auth import _check_auth_rate_limit

        request = MagicMock()
        request.headers = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        with patch("app.core.cache.auth_rate_limiter") as mock_rl:
            mock_rl.is_allowed = AsyncMock(return_value=(True, {}))
            await _check_auth_rate_limit(request)
            call_args = mock_rl.is_allowed.call_args
            assert "10.0.0.1" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_no_client_uses_unknown(self):
        from app.api.auth import _check_auth_rate_limit

        request = MagicMock()
        request.headers = {}
        request.client = None

        with patch("app.core.cache.auth_rate_limiter") as mock_rl:
            mock_rl.is_allowed = AsyncMock(return_value=(True, {}))
            await _check_auth_rate_limit(request)
            call_args = mock_rl.is_allowed.call_args
            assert "unknown" in call_args[0][0]
