"""GB067: Tests for api/deps.py — dependency injection, tenant scoping, role hierarchy."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.deps import (
    RateLimitExceeded,
    TenantScoped,
    get_current_admin_user,
    get_current_user,
    get_current_user_optional,
    get_tenant_id_from_request,
)
from app.models.user import User


def _make_user(**overrides) -> User:
    defaults = {
        "id": str(uuid4()),
        "email": "test@example.com",
        "username": "testuser",
        "is_active": True,
        "is_admin": False,
        "role": "user",
        "default_organization_id": None,
    }
    defaults.update(overrides)
    user = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _make_request(headers=None):
    req = MagicMock()
    req.headers = headers or {}
    return req


# ---------------------------------------------------------------------------
# get_tenant_id_from_request
# ---------------------------------------------------------------------------

class TestGetTenantIdFromRequest:
    @pytest.mark.asyncio
    async def test_x_tenant_id_header(self):
        req = _make_request(headers={"X-Tenant-ID": "t1"})
        assert await get_tenant_id_from_request(req) == "t1"

    @pytest.mark.asyncio
    async def test_x_organization_id_header(self):
        req = _make_request(headers={"X-Organization-ID": "o1"})
        assert await get_tenant_id_from_request(req) == "o1"

    @pytest.mark.asyncio
    async def test_tenant_id_priority_over_org_id(self):
        req = _make_request(
            headers={"X-Tenant-ID": "t1", "X-Organization-ID": "o1"}
        )
        assert await get_tenant_id_from_request(req) == "t1"

    @pytest.mark.asyncio
    async def test_no_headers_returns_context_var(self):
        req = _make_request()
        with patch("app.api.deps.get_current_tenant_id", return_value="ctx-t1"):
            result = await get_tenant_id_from_request(req)
        assert result == "ctx-t1"

    @pytest.mark.asyncio
    async def test_no_headers_no_context_returns_none(self):
        req = _make_request()
        with patch("app.api.deps.get_current_tenant_id", return_value=None):
            result = await get_tenant_id_from_request(req)
        assert result is None


# ---------------------------------------------------------------------------
# get_current_admin_user
# ---------------------------------------------------------------------------

class TestGetCurrentAdminUser:
    @pytest.mark.asyncio
    async def test_admin_passes(self):
        user = _make_user(is_admin=True)
        result = await get_current_admin_user(user)
        assert result is user

    @pytest.mark.asyncio
    async def test_non_admin_raises_403(self):
        user = _make_user(is_admin=False)
        with pytest.raises(HTTPException) as exc:
            await get_current_admin_user(user)
        assert exc.value.status_code == 403
        assert "admin" in exc.value.detail.lower()


# ---------------------------------------------------------------------------
# get_current_user_optional
# ---------------------------------------------------------------------------

class TestGetCurrentUserOptional:
    @pytest.mark.asyncio
    async def test_no_credentials_returns_none(self):
        db = AsyncMock()
        result = await get_current_user_optional(credentials=None, db=db)
        assert result is None

    @pytest.mark.asyncio
    @patch("app.api.deps.verify_token", return_value=None)
    async def test_invalid_token_returns_none(self, mock_verify):
        db = AsyncMock()
        creds = MagicMock()
        creds.credentials = "bad_token"
        result = await get_current_user_optional(credentials=creds, db=db)
        assert result is None

    @pytest.mark.asyncio
    @patch("app.api.deps.verify_token")
    @patch("app.api.deps.AuthService")
    async def test_inactive_user_returns_none(self, MockAuth, mock_verify):
        mock_verify.return_value = MagicMock(user_id="u1")
        user = _make_user(is_active=False)
        instance = MockAuth.return_value
        instance.get_user_by_id = AsyncMock(return_value=user)
        db = AsyncMock()
        creds = MagicMock()
        creds.credentials = "valid_token"
        result = await get_current_user_optional(credentials=creds, db=db)
        assert result is None

    @pytest.mark.asyncio
    @patch("app.api.deps.verify_token")
    @patch("app.api.deps.AuthService")
    async def test_user_not_found_returns_none(self, MockAuth, mock_verify):
        mock_verify.return_value = MagicMock(user_id="u1")
        instance = MockAuth.return_value
        instance.get_user_by_id = AsyncMock(return_value=None)
        db = AsyncMock()
        creds = MagicMock()
        creds.credentials = "valid_token"
        result = await get_current_user_optional(credentials=creds, db=db)
        assert result is None


# ---------------------------------------------------------------------------
# TenantScoped role hierarchy
# ---------------------------------------------------------------------------

class TestTenantScopedRoleHierarchy:
    def test_role_level_member(self):
        ts = TenantScoped(min_role="member")
        assert ts._role_level("member") == 0
        assert ts._role_level("admin") == 1
        assert ts._role_level("owner") == 2

    def test_role_level_unknown_returns_minus_one(self):
        ts = TenantScoped()
        assert ts._role_level("viewer") == -1
        assert ts._role_level("superadmin") == -1

    def test_member_satisfies_member(self):
        ts = TenantScoped(min_role="member")
        assert ts._role_level("member") >= ts._role_level("member")

    def test_member_does_not_satisfy_admin(self):
        ts = TenantScoped(min_role="admin")
        assert ts._role_level("member") < ts._role_level("admin")

    def test_owner_satisfies_all(self):
        ts = TenantScoped(min_role="owner")
        assert ts._role_level("owner") >= ts._role_level("owner")

    def test_admin_satisfies_member(self):
        ts = TenantScoped(min_role="member")
        assert ts._role_level("admin") >= ts._role_level("member")


# ---------------------------------------------------------------------------
# RateLimitExceeded
# ---------------------------------------------------------------------------

class TestRateLimitExceeded:
    def test_default_retry_after(self):
        exc = RateLimitExceeded()
        assert exc.status_code == 429
        assert exc.headers["Retry-After"] == "60"

    def test_custom_retry_after(self):
        exc = RateLimitExceeded(retry_after=120)
        assert exc.headers["Retry-After"] == "120"

    def test_detail_message(self):
        exc = RateLimitExceeded()
        assert "rate limit" in exc.detail.lower()
