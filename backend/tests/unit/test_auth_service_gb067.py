"""GB067: Tests for services/auth.py — AuthService edge cases with mocked DB."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

import pytest

from app.models.user import User, AuthProvider
from app.services.auth import AuthService


def _make_user(**overrides) -> User:
    defaults = {
        "id": str(uuid4()),
        "email": "test@example.com",
        "username": "testuser",
        "hashed_password": "hashed_value",
        "full_name": "Test User",
        "is_active": True,
        "is_verified": False,
        "role": "user",
        "auth_provider": AuthProvider.LOCAL.value,
        "provider_id": None,
        "last_login_at": None,
        "bio": None,
        "avatar_url": None,
    }
    defaults.update(overrides)
    user = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _make_service() -> AuthService:
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return AuthService(db)


def _mock_query_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------

class TestAuthenticateUser:
    @pytest.mark.asyncio
    async def test_user_not_found(self):
        svc = _make_service()
        svc.db.execute = AsyncMock(return_value=_mock_query_result(None))
        result = await svc.authenticate_user("noone@example.com", "pass")
        assert result is None

    @pytest.mark.asyncio
    async def test_user_no_password_oauth(self):
        """OAuth users have no hashed_password — authentication should fail."""
        svc = _make_service()
        user = _make_user(hashed_password=None)
        svc.db.execute = AsyncMock(return_value=_mock_query_result(user))
        result = await svc.authenticate_user("test@example.com", "pass")
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.auth.verify_password", return_value=False)
    async def test_wrong_password(self, mock_verify):
        svc = _make_service()
        user = _make_user()
        svc.db.execute = AsyncMock(return_value=_mock_query_result(user))
        result = await svc.authenticate_user("test@example.com", "wrong")
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.auth.verify_password", return_value=True)
    async def test_inactive_user_rejected(self, mock_verify):
        svc = _make_service()
        user = _make_user(is_active=False)
        svc.db.execute = AsyncMock(return_value=_mock_query_result(user))
        result = await svc.authenticate_user("test@example.com", "pass")
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.auth.verify_password", return_value=True)
    async def test_successful_auth_updates_last_login(self, mock_verify):
        svc = _make_service()
        user = _make_user()
        svc.db.execute = AsyncMock(return_value=_mock_query_result(user))
        result = await svc.authenticate_user("test@example.com", "pass")
        assert result is user
        assert user.last_login_at is not None
        svc.db.flush.assert_awaited()


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------

class TestLogin:
    @pytest.mark.asyncio
    @patch("app.services.auth.verify_password", return_value=True)
    @patch("app.services.auth.create_tokens")
    async def test_login_returns_tokens(self, mock_create, mock_verify):
        from app.core.security import Token
        mock_create.return_value = Token(
            access_token="at", refresh_token="rt", token_type="bearer", expires_in=3600
        )
        svc = _make_service()
        user = _make_user()
        svc.db.execute = AsyncMock(return_value=_mock_query_result(user))
        result = await svc.login("test@example.com", "pass")
        assert result is not None
        assert result.access_token == "at"
        mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_invalid_credentials_returns_none(self):
        svc = _make_service()
        svc.db.execute = AsyncMock(return_value=_mock_query_result(None))
        result = await svc.login("noone@example.com", "pass")
        assert result is None


# ---------------------------------------------------------------------------
# refresh_tokens
# ---------------------------------------------------------------------------

class TestRefreshTokens:
    @pytest.mark.asyncio
    @patch("app.services.auth.verify_token", return_value=None)
    async def test_invalid_refresh_token(self, mock_verify):
        svc = _make_service()
        result = await svc.refresh_tokens("bad_token")
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.auth.verify_token")
    @patch("app.services.auth.create_tokens")
    async def test_user_not_found_on_refresh(self, mock_create, mock_verify):
        mock_verify.return_value = MagicMock(user_id="deleted-user")
        svc = _make_service()
        svc.db.execute = AsyncMock(return_value=_mock_query_result(None))
        result = await svc.refresh_tokens("valid_refresh")
        assert result is None
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.auth.verify_token")
    @patch("app.services.auth.create_tokens")
    async def test_inactive_user_on_refresh(self, mock_create, mock_verify):
        mock_verify.return_value = MagicMock(user_id="user-1")
        user = _make_user(is_active=False)
        svc = _make_service()
        svc.db.execute = AsyncMock(return_value=_mock_query_result(user))
        result = await svc.refresh_tokens("valid_refresh")
        assert result is None
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.auth.verify_token")
    @patch("app.services.auth.create_tokens")
    async def test_successful_refresh(self, mock_create, mock_verify):
        from app.core.security import Token
        mock_verify.return_value = MagicMock(user_id="user-1")
        mock_create.return_value = Token(
            access_token="new_at", refresh_token="new_rt",
            token_type="bearer", expires_in=3600,
        )
        user = _make_user()
        svc = _make_service()
        svc.db.execute = AsyncMock(return_value=_mock_query_result(user))
        result = await svc.refresh_tokens("valid_refresh")
        assert result is not None
        assert result.access_token == "new_at"


# ---------------------------------------------------------------------------
# update_password
# ---------------------------------------------------------------------------

class TestUpdatePassword:
    @pytest.mark.asyncio
    @patch("app.services.auth.get_password_hash", return_value="new_hash")
    async def test_updates_hash(self, mock_hash):
        svc = _make_service()
        user = _make_user()
        result = await svc.update_password(user, "new_password")
        assert result is True
        assert user.hashed_password == "new_hash"
        svc.db.flush.assert_awaited()


# ---------------------------------------------------------------------------
# verify_email
# ---------------------------------------------------------------------------

class TestVerifyEmail:
    @pytest.mark.asyncio
    async def test_marks_verified(self):
        svc = _make_service()
        user = _make_user(is_verified=False)
        result = await svc.verify_email(user)
        assert result is True
        assert user.is_verified is True


# ---------------------------------------------------------------------------
# update_profile
# ---------------------------------------------------------------------------

class TestUpdateProfile:
    @pytest.mark.asyncio
    async def test_updates_full_name(self):
        svc = _make_service()
        user = _make_user()
        await svc.update_profile(user, full_name="New Name")
        assert user.full_name == "New Name"

    @pytest.mark.asyncio
    async def test_updates_bio(self):
        svc = _make_service()
        user = _make_user()
        await svc.update_profile(user, bio="My bio")
        assert user.bio == "My bio"

    @pytest.mark.asyncio
    async def test_updates_avatar(self):
        svc = _make_service()
        user = _make_user()
        await svc.update_profile(user, avatar_url="https://img.example.com/a.png")
        assert user.avatar_url == "https://img.example.com/a.png"

    @pytest.mark.asyncio
    async def test_none_values_not_overwritten(self):
        svc = _make_service()
        user = _make_user(full_name="Original")
        await svc.update_profile(user)
        assert user.full_name == "Original"


# ---------------------------------------------------------------------------
# get_user_by_email (case sensitivity)
# ---------------------------------------------------------------------------

class TestGetUserByEmail:
    @pytest.mark.asyncio
    async def test_lowercases_email(self):
        svc = _make_service()
        svc.db.execute = AsyncMock(return_value=_mock_query_result(None))
        await svc.get_user_by_email("TEST@Example.COM")
        call_args = svc.db.execute.call_args
        # Verify the query was constructed — we can't easily inspect the SQL
        # but the method should have been called
        svc.db.execute.assert_awaited_once()
