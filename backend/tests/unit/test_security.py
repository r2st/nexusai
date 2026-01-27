"""Unit tests for Security services.

Tests for:
- Rate limiting (sliding window, token bucket, fixed window)
- Tenant isolation (RLS context, data separation)
- Tool permissions (RBAC, tool-level access)
- Audit logging (security events, user actions)
"""

import asyncio
import time
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.security.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    RateLimitResult,
    RateLimitState,
    RateLimitStrategy,
    DEFAULT_RATE_LIMITS,
    rate_limiter,
)
from app.services.security.tenant_isolation import (
    TenantIsolationService,
    TenantContext,
    TenantScope,
    get_tenant_context,
    set_tenant_context,
    tenant_isolation_service,
)
from app.services.security.permissions import (
    PermissionsService,
    Permission,
    Role,
    ToolPermission,
    UserPermissions,
    ROLE_PERMISSIONS,
    DEFAULT_TOOL_PERMISSIONS,
    permissions_service,
)
from app.services.security.audit import (
    AuditLogger,
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    audit_logger,
)


# =============================================================================
# Rate Limiter Fixtures
# =============================================================================


@pytest.fixture
def rate_limiter_instance():
    """Create a fresh rate limiter instance."""
    return RateLimiter()


@pytest.fixture
def sliding_window_config():
    """Create a sliding window rate limit configuration."""
    return RateLimitConfig(
        name="test_sliding",
        max_requests=5,
        window_seconds=60,
        strategy=RateLimitStrategy.SLIDING_WINDOW,
    )


@pytest.fixture
def token_bucket_config():
    """Create a token bucket rate limit configuration."""
    return RateLimitConfig(
        name="test_bucket",
        max_requests=10,
        window_seconds=60,
        strategy=RateLimitStrategy.TOKEN_BUCKET,
        burst_limit=15,
        refill_rate=0.5,
    )


@pytest.fixture
def fixed_window_config():
    """Create a fixed window rate limit configuration."""
    return RateLimitConfig(
        name="test_fixed",
        max_requests=3,
        window_seconds=60,
        strategy=RateLimitStrategy.FIXED_WINDOW,
    )


# =============================================================================
# Tenant Isolation Fixtures
# =============================================================================


@pytest.fixture
def tenant_isolation():
    """Create a fresh tenant isolation service."""
    return TenantIsolationService(strict_mode=True)


@pytest.fixture
def tenant_isolation_non_strict():
    """Create a tenant isolation service in non-strict mode."""
    return TenantIsolationService(strict_mode=False)


@pytest.fixture
def tenant_context():
    """Create a basic tenant context."""
    return TenantContext(
        tenant_id="tenant-123",
        user_id="user-456",
        scope=TenantScope.ORGANIZATION,
    )


@pytest.fixture
def admin_tenant_context():
    """Create an admin tenant context."""
    return TenantContext(
        tenant_id="tenant-123",
        user_id="admin-789",
        scope=TenantScope.ORGANIZATION,
        is_admin=True,
    )


@pytest.fixture
def project_scoped_context():
    """Create a project-scoped tenant context."""
    return TenantContext(
        tenant_id="tenant-123",
        user_id="user-456",
        scope=TenantScope.PROJECT,
        project_id="project-001",
    )


# =============================================================================
# Permissions Fixtures
# =============================================================================


@pytest.fixture
def permissions_svc():
    """Create a fresh permissions service."""
    return PermissionsService()


@pytest.fixture
def owner_permissions(permissions_svc):
    """Create owner permissions."""
    return permissions_svc.create_user_permissions(
        user_id="owner-001",
        tenant_id="tenant-123",
        role=Role.OWNER,
    )


@pytest.fixture
def admin_permissions(permissions_svc):
    """Create admin permissions."""
    return permissions_svc.create_user_permissions(
        user_id="admin-001",
        tenant_id="tenant-123",
        role=Role.ADMIN,
    )


@pytest.fixture
def member_permissions(permissions_svc):
    """Create member permissions."""
    return permissions_svc.create_user_permissions(
        user_id="member-001",
        tenant_id="tenant-123",
        role=Role.MEMBER,
    )


@pytest.fixture
def viewer_permissions(permissions_svc):
    """Create viewer permissions."""
    return permissions_svc.create_user_permissions(
        user_id="viewer-001",
        tenant_id="tenant-123",
        role=Role.VIEWER,
    )


@pytest.fixture
def guest_permissions(permissions_svc):
    """Create guest permissions."""
    return permissions_svc.create_user_permissions(
        user_id="guest-001",
        tenant_id="tenant-123",
        role=Role.GUEST,
    )


# =============================================================================
# Audit Logger Fixtures
# =============================================================================


@pytest.fixture
def audit_logger_instance():
    """Create a fresh audit logger instance."""
    return AuditLogger(log_to_db=False, log_to_file=False)


@pytest.fixture
def audit_logger_debug():
    """Create an audit logger that logs debug events."""
    return AuditLogger(
        log_to_db=False,
        log_to_file=False,
        min_severity=AuditSeverity.DEBUG,
    )


# =============================================================================
# Rate Limiter Tests - Sliding Window
# =============================================================================


class TestRateLimiterSlidingWindow:
    """Tests for sliding window rate limiting."""

    @pytest.mark.asyncio
    async def test_sliding_window_allows_under_limit(self, rate_limiter_instance, sliding_window_config):
        """Test that requests under limit are allowed."""
        rate_limiter_instance.register_limit(sliding_window_config)

        for i in range(5):
            result = await rate_limiter_instance.check(
                "test_sliding", f"user-{i % 2}", cost=1
            )
            assert result.allowed is True

    @pytest.mark.asyncio
    async def test_sliding_window_blocks_over_limit(self, rate_limiter_instance, sliding_window_config):
        """Test that requests over limit are blocked."""
        rate_limiter_instance.register_limit(sliding_window_config)

        # Exhaust the limit
        for _ in range(5):
            await rate_limiter_instance.check("test_sliding", "user-001")

        # Next request should be blocked
        result = await rate_limiter_instance.check("test_sliding", "user-001")
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after_seconds is not None
        assert result.retry_after_seconds > 0

    @pytest.mark.asyncio
    async def test_sliding_window_remaining_count(self, rate_limiter_instance, sliding_window_config):
        """Test that remaining count is accurate."""
        rate_limiter_instance.register_limit(sliding_window_config)

        result = await rate_limiter_instance.check("test_sliding", "user-001")
        assert result.remaining == 4  # 5 - 1 = 4

        result = await rate_limiter_instance.check("test_sliding", "user-001")
        assert result.remaining == 3  # 5 - 2 = 3

    @pytest.mark.asyncio
    async def test_sliding_window_tenant_isolation(self, rate_limiter_instance, sliding_window_config):
        """Test that rate limits are isolated by tenant."""
        rate_limiter_instance.register_limit(sliding_window_config)

        # Exhaust limit for tenant-1
        for _ in range(5):
            await rate_limiter_instance.check(
                "test_sliding", "user-001", tenant_id="tenant-1"
            )

        # Tenant-1 should be blocked
        result = await rate_limiter_instance.check(
            "test_sliding", "user-001", tenant_id="tenant-1"
        )
        assert result.allowed is False

        # Tenant-2 should still have quota
        result = await rate_limiter_instance.check(
            "test_sliding", "user-001", tenant_id="tenant-2"
        )
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_sliding_window_cost_parameter(self, rate_limiter_instance, sliding_window_config):
        """Test that cost parameter consumes multiple requests."""
        rate_limiter_instance.register_limit(sliding_window_config)

        # Use cost of 3 (should leave 2 remaining)
        result = await rate_limiter_instance.check("test_sliding", "user-001", cost=3)
        assert result.allowed is True
        assert result.remaining == 2

        # Use cost of 3 (should fail, only 2 remaining)
        result = await rate_limiter_instance.check("test_sliding", "user-001", cost=3)
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_sliding_window_headers(self, rate_limiter_instance, sliding_window_config):
        """Test that rate limit headers are generated correctly."""
        rate_limiter_instance.register_limit(sliding_window_config)

        result = await rate_limiter_instance.check("test_sliding", "user-001")
        headers = result.to_headers()

        assert "X-RateLimit-Limit" in headers
        assert headers["X-RateLimit-Limit"] == "5"
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers


# =============================================================================
# Rate Limiter Tests - Token Bucket
# =============================================================================


class TestRateLimiterTokenBucket:
    """Tests for token bucket rate limiting."""

    @pytest.mark.asyncio
    async def test_token_bucket_allows_burst(self, rate_limiter_instance, token_bucket_config):
        """Test that token bucket allows burst requests."""
        rate_limiter_instance.register_limit(token_bucket_config)

        # Should allow burst up to burst_limit (15)
        for i in range(15):
            result = await rate_limiter_instance.check("test_bucket", "user-001")
            assert result.allowed is True, f"Request {i+1} should be allowed"

    @pytest.mark.asyncio
    async def test_token_bucket_blocks_after_burst(self, rate_limiter_instance, token_bucket_config):
        """Test that token bucket blocks after burst is exhausted."""
        rate_limiter_instance.register_limit(token_bucket_config)

        # Exhaust burst
        for _ in range(15):
            await rate_limiter_instance.check("test_bucket", "user-001")

        # Next request should be blocked
        result = await rate_limiter_instance.check("test_bucket", "user-001")
        assert result.allowed is False
        assert result.retry_after_seconds is not None

    @pytest.mark.asyncio
    async def test_token_bucket_refills_over_time(self, rate_limiter_instance):
        """Test that token bucket refills tokens over time."""
        config = RateLimitConfig(
            name="test_refill",
            max_requests=10,
            window_seconds=10,
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            burst_limit=5,
            refill_rate=5.0,  # 5 tokens per second
        )
        rate_limiter_instance.register_limit(config)

        # Exhaust tokens
        for _ in range(5):
            await rate_limiter_instance.check("test_refill", "user-001")

        # Should be blocked
        result = await rate_limiter_instance.check("test_refill", "user-001")
        assert result.allowed is False

        # Wait for refill (simulate time passing)
        await asyncio.sleep(0.3)  # Should get ~1.5 tokens

        # Should be allowed again
        result = await rate_limiter_instance.check("test_refill", "user-001")
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_token_bucket_default_refill_rate(self, rate_limiter_instance):
        """Test token bucket default refill rate calculation."""
        config = RateLimitConfig(
            name="test_default_refill",
            max_requests=60,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET,
        )
        rate_limiter_instance.register_limit(config)

        # Default refill rate should be max_requests / window_seconds = 1 per second
        assert config.refill_rate == 1.0
        assert config.burst_limit == 60


# =============================================================================
# Rate Limiter Tests - Fixed Window
# =============================================================================


class TestRateLimiterFixedWindow:
    """Tests for fixed window rate limiting."""

    @pytest.mark.asyncio
    async def test_fixed_window_allows_under_limit(self, rate_limiter_instance, fixed_window_config):
        """Test that requests under limit are allowed."""
        rate_limiter_instance.register_limit(fixed_window_config)

        for _ in range(3):
            result = await rate_limiter_instance.check("test_fixed", "user-001")
            assert result.allowed is True

    @pytest.mark.asyncio
    async def test_fixed_window_blocks_over_limit(self, rate_limiter_instance, fixed_window_config):
        """Test that requests over limit are blocked."""
        rate_limiter_instance.register_limit(fixed_window_config)

        # Exhaust limit
        for _ in range(3):
            await rate_limiter_instance.check("test_fixed", "user-001")

        # Next should be blocked
        result = await rate_limiter_instance.check("test_fixed", "user-001")
        assert result.allowed is False
        assert result.remaining == 0

    @pytest.mark.asyncio
    async def test_fixed_window_resets_on_new_window(self, rate_limiter_instance):
        """Test that fixed window resets when window changes."""
        config = RateLimitConfig(
            name="test_fixed_reset",
            max_requests=2,
            window_seconds=1,  # 1 second window for testing
            strategy=RateLimitStrategy.FIXED_WINDOW,
        )
        rate_limiter_instance.register_limit(config)

        # Exhaust limit
        await rate_limiter_instance.check("test_fixed_reset", "user-001")
        await rate_limiter_instance.check("test_fixed_reset", "user-001")

        result = await rate_limiter_instance.check("test_fixed_reset", "user-001")
        assert result.allowed is False

        # Wait for new window
        await asyncio.sleep(1.1)

        # Should be allowed in new window
        result = await rate_limiter_instance.check("test_fixed_reset", "user-001")
        assert result.allowed is True


# =============================================================================
# Rate Limiter Tests - General
# =============================================================================


class TestRateLimiterGeneral:
    """General tests for rate limiter."""

    @pytest.mark.asyncio
    async def test_unknown_limit_allows_request(self, rate_limiter_instance):
        """Test that unknown rate limits allow requests."""
        result = await rate_limiter_instance.check("unknown_limit", "user-001")
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_reset_clears_state(self, rate_limiter_instance, sliding_window_config):
        """Test that reset clears rate limit state."""
        rate_limiter_instance.register_limit(sliding_window_config)

        # Exhaust limit
        for _ in range(5):
            await rate_limiter_instance.check("test_sliding", "user-001")

        result = await rate_limiter_instance.check("test_sliding", "user-001")
        assert result.allowed is False

        # Reset
        await rate_limiter_instance.reset("test_sliding", "user-001")

        # Should be allowed again
        result = await rate_limiter_instance.check("test_sliding", "user-001")
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_get_status_without_consuming(self, rate_limiter_instance, sliding_window_config):
        """Test that get_status doesn't consume quota."""
        rate_limiter_instance.register_limit(sliding_window_config)

        # Check status multiple times
        for _ in range(10):
            status = await rate_limiter_instance.get_status("test_sliding", "user-001")

        # Should still have full quota
        result = await rate_limiter_instance.check("test_sliding", "user-001")
        assert result.remaining == 4  # Only 1 consumed by check

    def test_cleanup_expired_states(self, rate_limiter_instance):
        """Test cleanup of expired rate limit states."""
        config = RateLimitConfig(
            name="test_cleanup",
            max_requests=10,
            window_seconds=1,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )
        rate_limiter_instance.register_limit(config)

        # Create some states
        old_time = time.time() - 10  # 10 seconds ago
        state = RateLimitState(key="test_key", config=config)
        state.request_times = [old_time]
        rate_limiter_instance._states["test_key"] = state

        # Cleanup should remove old states
        cleaned = rate_limiter_instance.cleanup_expired()
        assert cleaned >= 0

    def test_default_rate_limits_exist(self):
        """Test that default rate limits are configured."""
        assert "llm_request" in DEFAULT_RATE_LIMITS
        assert "api_request" in DEFAULT_RATE_LIMITS
        assert "login_attempt" in DEFAULT_RATE_LIMITS
        assert "agent_execute" in DEFAULT_RATE_LIMITS
        assert "document_upload" in DEFAULT_RATE_LIMITS

    def test_key_generation(self, rate_limiter_instance):
        """Test rate limit key generation."""
        key = rate_limiter_instance._get_key("test_limit", "user-001")
        assert "test_limit" in key
        assert "user-001" in key

        key_with_tenant = rate_limiter_instance._get_key(
            "test_limit", "user-001", tenant_id="tenant-123"
        )
        assert "tenant:tenant-123" in key_with_tenant

    def test_rate_limit_result_headers_with_retry(self):
        """Test rate limit result headers include retry-after when blocked."""
        result = RateLimitResult(
            allowed=False,
            remaining=0,
            reset_after_seconds=60,
            retry_after_seconds=30,
            limit=100,
        )
        headers = result.to_headers()

        assert headers["Retry-After"] == "30"
        assert headers["X-RateLimit-Remaining"] == "0"


# =============================================================================
# Tenant Isolation Tests - Context Management
# =============================================================================


class TestTenantContextManagement:
    """Tests for tenant context management."""

    def test_set_and_get_context(self, tenant_context):
        """Test setting and getting tenant context."""
        set_tenant_context(tenant_context)
        retrieved = get_tenant_context()

        assert retrieved is not None
        assert retrieved.tenant_id == "tenant-123"
        assert retrieved.user_id == "user-456"

        # Clean up
        set_tenant_context(None)

    def test_context_clears_properly(self, tenant_context):
        """Test that context clears properly."""
        set_tenant_context(tenant_context)
        set_tenant_context(None)

        assert get_tenant_context() is None

    def test_tenant_context_project_access_organization_scope(self, tenant_context):
        """Test organization scope can access any project."""
        assert tenant_context.can_access_project("project-001") is True
        assert tenant_context.can_access_project("project-002") is True

    def test_tenant_context_project_access_project_scope(self, project_scoped_context):
        """Test project scope can only access specific project."""
        assert project_scoped_context.can_access_project("project-001") is True
        assert project_scoped_context.can_access_project("project-002") is False

    def test_tenant_context_admin_can_access_any_project(self, admin_tenant_context):
        """Test admin can access any project."""
        assert admin_tenant_context.can_access_project("any-project") is True

    def test_tenant_context_resource_access_same_tenant(self, tenant_context):
        """Test resource access within same tenant."""
        assert tenant_context.can_access_resource("tenant-123") is True

    def test_tenant_context_resource_access_different_tenant(self, tenant_context):
        """Test resource access denied for different tenant."""
        assert tenant_context.can_access_resource("tenant-456") is False

    def test_tenant_context_admin_cross_tenant_access(self, admin_tenant_context):
        """Test admin can access resources from other tenants."""
        assert admin_tenant_context.can_access_resource("tenant-999") is True


# =============================================================================
# Tenant Isolation Tests - Validation
# =============================================================================


class TestTenantIsolationValidation:
    """Tests for tenant isolation validation."""

    def test_validate_tenant_access_same_tenant(self, tenant_isolation, tenant_context):
        """Test validation passes for same tenant."""
        result = tenant_isolation.validate_tenant_access(
            "tenant-123", context=tenant_context
        )
        assert result is True

    def test_validate_tenant_access_different_tenant_raises(self, tenant_isolation, tenant_context):
        """Test validation raises for different tenant."""
        with pytest.raises(PermissionError) as exc_info:
            tenant_isolation.validate_tenant_access(
                "tenant-456", context=tenant_context
            )
        assert "Access denied" in str(exc_info.value)

    def test_validate_tenant_access_no_context_strict_mode(self, tenant_isolation):
        """Test validation raises when no context in strict mode."""
        with pytest.raises(PermissionError) as exc_info:
            tenant_isolation.validate_tenant_access("tenant-123")
        assert "No tenant context" in str(exc_info.value)

    def test_validate_tenant_access_no_context_non_strict(self, tenant_isolation_non_strict):
        """Test validation passes without context in non-strict mode."""
        result = tenant_isolation_non_strict.validate_tenant_access("tenant-123")
        assert result is True

    def test_validate_project_access_allowed(self, tenant_isolation, tenant_context):
        """Test project access validation passes for valid access."""
        result = tenant_isolation.validate_project_access(
            "any-project", context=tenant_context
        )
        assert result is True

    def test_validate_project_access_denied(self, tenant_isolation, project_scoped_context):
        """Test project access validation fails for unauthorized project."""
        with pytest.raises(PermissionError) as exc_info:
            tenant_isolation.validate_project_access(
                "other-project", context=project_scoped_context
            )
        assert "Access denied to project" in str(exc_info.value)

    def test_create_tenant_context(self, tenant_isolation):
        """Test tenant context creation."""
        context = tenant_isolation.create_tenant_context(
            tenant_id="tenant-new",
            user_id="user-new",
            scope=TenantScope.TEAM,
            project_id="project-team",
            is_admin=False,
            permissions={"read", "write"},
        )

        assert context.tenant_id == "tenant-new"
        assert context.user_id == "user-new"
        assert context.scope == TenantScope.TEAM
        assert context.project_id == "project-team"
        assert context.is_admin is False
        assert "read" in context.permissions


# =============================================================================
# Tenant Isolation Tests - Context Manager
# =============================================================================


class TestTenantContextManager:
    """Tests for tenant context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_sets_context(self, tenant_isolation, tenant_context):
        """Test context manager sets context during scope."""
        async with tenant_isolation.scope(tenant_context):
            current = get_tenant_context()
            assert current is not None
            assert current.tenant_id == "tenant-123"

    @pytest.mark.asyncio
    async def test_context_manager_restores_previous(self, tenant_isolation):
        """Test context manager restores previous context."""
        original = TenantContext(
            tenant_id="original-tenant",
            user_id="original-user",
        )
        set_tenant_context(original)

        new_context = TenantContext(
            tenant_id="new-tenant",
            user_id="new-user",
        )

        async with tenant_isolation.scope(new_context):
            current = get_tenant_context()
            assert current.tenant_id == "new-tenant"

        # Should be restored
        restored = get_tenant_context()
        assert restored.tenant_id == "original-tenant"

        # Clean up
        set_tenant_context(None)

    @pytest.mark.asyncio
    async def test_context_manager_with_session(self, tenant_isolation, tenant_context):
        """Test context manager with database session."""
        mock_session = AsyncMock()

        async with tenant_isolation.scope(tenant_context, session=mock_session):
            pass

        # Should have set and cleared tenant
        mock_session.execute.assert_called()


# =============================================================================
# Tenant Isolation Tests - RLS
# =============================================================================


class TestTenantIsolationRLS:
    """Tests for RLS policy management."""

    def test_isolated_tables_list(self, tenant_isolation):
        """Test that isolated tables list is populated."""
        assert len(tenant_isolation.ISOLATED_TABLES) > 0
        assert "organizations" in tenant_isolation.ISOLATED_TABLES
        assert "projects" in tenant_isolation.ISOLATED_TABLES
        assert "conversations" in tenant_isolation.ISOLATED_TABLES

    @pytest.mark.asyncio
    async def test_set_session_tenant(self, tenant_isolation):
        """Test setting tenant context on database session."""
        mock_session = AsyncMock()

        await tenant_isolation.set_session_tenant(mock_session, "tenant-123")

        mock_session.execute.assert_called_once()
        # Check that the call included the tenant_id parameter
        call_args = mock_session.execute.call_args
        # The second positional argument should be the params dict with tenant_id
        assert call_args[0][1]["tenant_id"] == "tenant-123"

    @pytest.mark.asyncio
    async def test_clear_session_tenant(self, tenant_isolation):
        """Test clearing tenant context from database session."""
        mock_session = AsyncMock()

        await tenant_isolation.clear_session_tenant(mock_session)

        mock_session.execute.assert_called_once()


# =============================================================================
# Permissions Tests - Role Permissions
# =============================================================================


class TestRolePermissions:
    """Tests for role-based permissions."""

    def test_owner_has_all_permissions(self, permissions_svc):
        """Test that owner role has all permissions."""
        owner_perms = permissions_svc.get_role_permissions(Role.OWNER)

        assert Permission.ORG_DELETE in owner_perms
        assert Permission.PROJECT_DELETE in owner_perms
        assert Permission.API_KEY_REVOKE in owner_perms
        assert Permission.AUDIT_READ in owner_perms

    def test_admin_has_most_permissions(self, permissions_svc):
        """Test that admin role has most permissions except dangerous ones."""
        admin_perms = permissions_svc.get_role_permissions(Role.ADMIN)

        assert Permission.ORG_ADMIN in admin_perms
        assert Permission.PROJECT_ADMIN in admin_perms
        assert Permission.ORG_DELETE not in admin_perms
        assert Permission.API_KEY_REVOKE not in admin_perms

    def test_member_has_basic_permissions(self, permissions_svc):
        """Test that member role has basic permissions."""
        member_perms = permissions_svc.get_role_permissions(Role.MEMBER)

        assert Permission.PROJECT_READ in member_perms
        assert Permission.PROJECT_WRITE in member_perms
        assert Permission.AGENT_EXECUTE in member_perms
        assert Permission.PROJECT_DELETE not in member_perms
        assert Permission.ORG_ADMIN not in member_perms

    def test_viewer_has_read_only_permissions(self, permissions_svc):
        """Test that viewer role has read-only permissions."""
        viewer_perms = permissions_svc.get_role_permissions(Role.VIEWER)

        assert Permission.PROJECT_READ in viewer_perms
        assert Permission.METRICS_READ in viewer_perms
        assert Permission.PROJECT_WRITE not in viewer_perms
        assert Permission.AGENT_EXECUTE not in viewer_perms

    def test_guest_has_minimal_permissions(self, permissions_svc):
        """Test that guest role has minimal permissions."""
        guest_perms = permissions_svc.get_role_permissions(Role.GUEST)

        assert Permission.ORG_READ in guest_perms
        assert Permission.PROJECT_READ in guest_perms
        assert Permission.DOCUMENT_READ not in guest_perms
        assert Permission.AGENT_READ not in guest_perms


# =============================================================================
# Permissions Tests - User Permissions
# =============================================================================


class TestUserPermissions:
    """Tests for user permissions."""

    def test_has_permission_from_role(self, owner_permissions):
        """Test user has permission from role."""
        assert owner_permissions.has_permission(Permission.ORG_DELETE) is True

    def test_has_permission_denied(self, member_permissions):
        """Test user denied permission not in role."""
        assert member_permissions.has_permission(Permission.ORG_DELETE) is False

    def test_custom_permission_added(self, permissions_svc):
        """Test custom permissions are applied."""
        user_perms = permissions_svc.create_user_permissions(
            user_id="user-001",
            tenant_id="tenant-123",
            role=Role.MEMBER,
            custom_permissions={Permission.METRICS_EXPORT},
        )

        # Should have both role and custom permissions
        assert user_perms.has_permission(Permission.PROJECT_READ) is True
        assert user_perms.has_permission(Permission.METRICS_EXPORT) is True

    def test_denied_permission_overrides_role(self, permissions_svc):
        """Test denied permissions override role permissions."""
        user_perms = permissions_svc.create_user_permissions(
            user_id="user-001",
            tenant_id="tenant-123",
            role=Role.ADMIN,
            denied_permissions={Permission.PROJECT_DELETE},
        )

        # Should be denied despite admin role
        assert user_perms.has_permission(Permission.PROJECT_DELETE) is False
        # Other admin permissions should work
        assert user_perms.has_permission(Permission.PROJECT_ADMIN) is True

    def test_can_use_tool_owner(self, owner_permissions):
        """Test owner can use all tools."""
        assert owner_permissions.can_use_tool("delete_organization") is True
        assert owner_permissions.can_use_tool("transfer_ownership") is True

    def test_can_use_tool_member(self, member_permissions):
        """Test member can use appropriate tools."""
        assert member_permissions.can_use_tool("get_metrics") is True
        assert member_permissions.can_use_tool("create_blueprint") is True
        assert member_permissions.can_use_tool("delete_organization") is False

    def test_can_use_tool_viewer(self, viewer_permissions):
        """Test viewer has limited tool access."""
        assert viewer_permissions.can_use_tool("get_metrics") is True
        assert viewer_permissions.can_use_tool("search_documents") is True
        assert viewer_permissions.can_use_tool("create_blueprint") is False


# =============================================================================
# Permissions Tests - Permission Checking
# =============================================================================


class TestPermissionChecking:
    """Tests for permission checking service."""

    def test_check_permission_allowed(self, permissions_svc, owner_permissions):
        """Test permission check passes for valid permission."""
        result = permissions_svc.check_permission(
            owner_permissions, Permission.ORG_DELETE
        )
        assert result is True

    def test_check_permission_denied_raises(self, permissions_svc, member_permissions):
        """Test permission check raises for denied permission."""
        with pytest.raises(PermissionError) as exc_info:
            permissions_svc.check_permission(
                member_permissions, Permission.ORG_DELETE
            )
        assert "Permission denied" in str(exc_info.value)


# =============================================================================
# Permissions Tests - Tool Permissions
# =============================================================================


class TestToolPermissions:
    """Tests for tool-level permissions."""

    def test_check_tool_permission_allowed(self, permissions_svc, owner_permissions):
        """Test tool permission check passes."""
        allowed, requires_confirmation = permissions_svc.check_tool_permission(
            owner_permissions, "delete_organization"
        )
        assert allowed is True
        assert requires_confirmation is True

    def test_check_tool_permission_denied_raises(self, permissions_svc, member_permissions):
        """Test tool permission check raises for denied tool."""
        with pytest.raises(PermissionError) as exc_info:
            permissions_svc.check_tool_permission(
                member_permissions, "delete_organization"
            )
        assert "not authorized for tool" in str(exc_info.value)

    def test_check_tool_permission_blocked_parameter(self, permissions_svc, owner_permissions):
        """Test tool permission check blocks forbidden parameters."""
        # Register tool with blocked parameter
        tool_perm = ToolPermission(
            tool_name="test_tool",
            allowed_roles={Role.OWNER, Role.ADMIN, Role.MEMBER},
            blocked_parameters={"dangerous_param"},
        )
        permissions_svc.register_tool_permission(tool_perm)

        with pytest.raises(PermissionError) as exc_info:
            permissions_svc.check_tool_permission(
                owner_permissions,
                "test_tool",
                parameters={"dangerous_param": "value"},
            )
        assert "not allowed for tool" in str(exc_info.value)

    def test_check_tool_permission_allowed_parameters_only(self, permissions_svc, owner_permissions):
        """Test tool permission check with allowed parameters whitelist."""
        tool_perm = ToolPermission(
            tool_name="restricted_tool",
            allowed_roles={Role.OWNER},
            allowed_parameters={"safe_param"},
        )
        permissions_svc.register_tool_permission(tool_perm)

        # Should pass with allowed parameter
        allowed, _ = permissions_svc.check_tool_permission(
            owner_permissions,
            "restricted_tool",
            parameters={"safe_param": "value"},
        )
        assert allowed is True

        # Should fail with non-allowed parameter
        with pytest.raises(PermissionError):
            permissions_svc.check_tool_permission(
                owner_permissions,
                "restricted_tool",
                parameters={"other_param": "value"},
            )

    def test_list_available_tools(self, permissions_svc, member_permissions):
        """Test listing available tools for user."""
        available = permissions_svc.list_available_tools(member_permissions)

        tool_names = [t["name"] for t in available]
        assert "get_metrics" in tool_names
        assert "search_documents" in tool_names
        assert "delete_organization" not in tool_names

    def test_register_tool_permission(self, permissions_svc):
        """Test registering custom tool permission."""
        custom_tool = ToolPermission(
            tool_name="custom_tool",
            allowed_roles={Role.ADMIN},
            requires_confirmation=True,
            max_executions_per_hour=50,
        )
        permissions_svc.register_tool_permission(custom_tool)

        retrieved = permissions_svc.get_tool_permission("custom_tool")
        assert retrieved is not None
        assert retrieved.requires_confirmation is True
        assert retrieved.max_executions_per_hour == 50


# =============================================================================
# Permissions Tests - Resource Access
# =============================================================================


class TestResourceAccess:
    """Tests for resource access control."""

    def test_can_access_resource_project_read(self, permissions_svc, viewer_permissions):
        """Test viewer can read projects."""
        result = permissions_svc.can_access_resource(
            viewer_permissions, "project", "project-001", "read"
        )
        assert result is True

    def test_can_access_resource_project_write_denied(self, permissions_svc, viewer_permissions):
        """Test viewer cannot write to projects."""
        result = permissions_svc.can_access_resource(
            viewer_permissions, "project", "project-001", "write"
        )
        assert result is False

    def test_can_access_resource_unknown_type(self, permissions_svc, owner_permissions):
        """Test access denied for unknown resource type."""
        result = permissions_svc.can_access_resource(
            owner_permissions, "unknown_resource", "id-001", "read"
        )
        assert result is False

    def test_can_access_resource_document_delete(self, permissions_svc, admin_permissions):
        """Test admin can delete documents."""
        result = permissions_svc.can_access_resource(
            admin_permissions, "document", "doc-001", "delete"
        )
        assert result is True


# =============================================================================
# Audit Logger Tests - Event Logging
# =============================================================================


class TestAuditEventLogging:
    """Tests for audit event logging."""

    @pytest.mark.asyncio
    async def test_log_event(self, audit_logger_instance):
        """Test logging an audit event."""
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            timestamp=datetime.now(UTC),
            tenant_id="tenant-123",
            user_id="user-456",
        )

        await audit_logger_instance.log(event)

        # Event should be in buffer
        assert len(audit_logger_instance._buffer) == 1
        assert audit_logger_instance._buffer[0].event_type == AuditEventType.LOGIN_SUCCESS

    @pytest.mark.asyncio
    async def test_log_auth_event_success(self, audit_logger_instance):
        """Test logging successful auth event."""
        await audit_logger_instance.log_auth_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            user_id="user-123",
            tenant_id="tenant-456",
            success=True,
            ip_address="192.168.1.1",
        )

        events = await audit_logger_instance.query(user_id="user-123")
        assert len(events) == 1
        assert events[0].event_type == AuditEventType.LOGIN_SUCCESS
        assert events[0].severity == AuditSeverity.INFO

    @pytest.mark.asyncio
    async def test_log_auth_event_failure(self, audit_logger_instance):
        """Test logging failed auth event."""
        await audit_logger_instance.log_auth_event(
            event_type=AuditEventType.LOGIN_FAILURE,
            user_id="user-123",
            success=False,
        )

        events = await audit_logger_instance.query(user_id="user-123")
        assert len(events) == 1
        assert events[0].severity == AuditSeverity.WARNING

    @pytest.mark.asyncio
    async def test_log_data_access(self, audit_logger_instance):
        """Test logging data access event."""
        await audit_logger_instance.log_data_access(
            event_type=AuditEventType.DATA_READ,
            tenant_id="tenant-123",
            user_id="user-456",
            resource_type="document",
            resource_id="doc-789",
            action="view",
        )

        events = await audit_logger_instance.query(tenant_id="tenant-123")
        assert len(events) == 1
        assert events[0].resource_type == "document"
        assert events[0].resource_id == "doc-789"

    @pytest.mark.asyncio
    async def test_log_security_event(self, audit_logger_instance):
        """Test logging security event."""
        await audit_logger_instance.log_security_event(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            tenant_id="tenant-123",
            user_id="user-456",
            ip_address="10.0.0.1",
            details={"reason": "Multiple failed attempts"},
            severity=AuditSeverity.WARNING,
        )

        events = await audit_logger_instance.query(
            event_types=[AuditEventType.SUSPICIOUS_ACTIVITY]
        )
        assert len(events) == 1
        assert events[0].success is False


# =============================================================================
# Audit Logger Tests - Agent/Tool Execution
# =============================================================================


class TestAuditAgentToolLogging:
    """Tests for agent and tool execution logging."""

    @pytest.mark.asyncio
    async def test_log_agent_execution(self, audit_logger_instance):
        """Test logging agent execution."""
        await audit_logger_instance.log_agent_execution(
            tenant_id="tenant-123",
            user_id="user-456",
            agent_id="agent-789",
            agent_type="metrics_analyst",
            input_summary="Analyze sprint velocity",
            output_summary="Velocity increased by 15%",
            tools_used=["get_metrics", "analyze_trend"],
            success=True,
            execution_time_ms=1500.5,
        )

        events = await audit_logger_instance.query(
            event_types=[AuditEventType.AGENT_EXECUTED]
        )
        assert len(events) == 1
        assert events[0].details["agent_type"] == "metrics_analyst"
        assert "get_metrics" in events[0].details["tools_used"]

    @pytest.mark.asyncio
    async def test_log_tool_execution(self, audit_logger_instance):
        """Test logging tool execution."""
        await audit_logger_instance.log_tool_execution(
            tenant_id="tenant-123",
            user_id="user-456",
            tool_name="create_issue",
            parameters={"title": "Bug fix", "priority": "high"},
            success=True,
            required_confirmation=True,
            execution_time_ms=250.0,
        )

        events = await audit_logger_instance.query(
            event_types=[AuditEventType.TOOL_EXECUTED]
        )
        assert len(events) == 1
        assert events[0].resource_id == "create_issue"
        assert events[0].details["required_confirmation"] is True


# =============================================================================
# Audit Logger Tests - Sensitive Data Redaction
# =============================================================================


class TestAuditSensitiveDataRedaction:
    """Tests for sensitive data redaction in audit logs."""

    @pytest.mark.asyncio
    async def test_redact_password(self, audit_logger_instance):
        """Test password redaction in parameters."""
        await audit_logger_instance.log_tool_execution(
            tenant_id="tenant-123",
            user_id="user-456",
            tool_name="test_tool",
            parameters={"username": "testuser", "password": "secret123"},
            success=True,
        )

        events = await audit_logger_instance.query()
        params = events[0].details["parameters"]
        assert params["password"] == "[REDACTED]"
        assert params["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_redact_api_key(self, audit_logger_instance):
        """Test API key redaction in parameters."""
        await audit_logger_instance.log_tool_execution(
            tenant_id="tenant-123",
            user_id="user-456",
            tool_name="test_tool",
            parameters={"api_key": "sk-abc123", "name": "My Key"},
            success=True,
        )

        events = await audit_logger_instance.query()
        params = events[0].details["parameters"]
        assert params["api_key"] == "[REDACTED]"
        assert params["name"] == "My Key"

    @pytest.mark.asyncio
    async def test_redact_nested_sensitive(self, audit_logger_instance):
        """Test redaction in nested objects."""
        await audit_logger_instance.log_tool_execution(
            tenant_id="tenant-123",
            user_id="user-456",
            tool_name="test_tool",
            parameters={
                "config": {
                    "secret_token": "xyz789",
                    "url": "https://api.example.com",
                }
            },
            success=True,
        )

        events = await audit_logger_instance.query()
        nested_config = events[0].details["parameters"]["config"]
        assert nested_config["secret_token"] == "[REDACTED]"
        assert nested_config["url"] == "https://api.example.com"


# =============================================================================
# Audit Logger Tests - Querying
# =============================================================================


class TestAuditQuerying:
    """Tests for audit event querying."""

    @pytest.mark.asyncio
    async def test_query_by_tenant(self, audit_logger_instance):
        """Test querying events by tenant."""
        await audit_logger_instance.log_auth_event(
            AuditEventType.LOGIN_SUCCESS,
            "user-1",
            tenant_id="tenant-A",
            success=True,
        )
        await audit_logger_instance.log_auth_event(
            AuditEventType.LOGIN_SUCCESS,
            "user-2",
            tenant_id="tenant-B",
            success=True,
        )

        events = await audit_logger_instance.query(tenant_id="tenant-A")
        assert len(events) == 1
        assert events[0].tenant_id == "tenant-A"

    @pytest.mark.asyncio
    async def test_query_by_user(self, audit_logger_instance):
        """Test querying events by user."""
        await audit_logger_instance.log_auth_event(
            AuditEventType.LOGIN_SUCCESS,
            "user-specific",
            success=True,
        )
        await audit_logger_instance.log_auth_event(
            AuditEventType.LOGIN_SUCCESS,
            "other-user",
            success=True,
        )

        events = await audit_logger_instance.query(user_id="user-specific")
        assert all(e.user_id == "user-specific" for e in events)

    @pytest.mark.asyncio
    async def test_query_by_event_types(self, audit_logger_instance):
        """Test querying events by type."""
        await audit_logger_instance.log_auth_event(
            AuditEventType.LOGIN_SUCCESS,
            "user-1",
            success=True,
        )
        await audit_logger_instance.log_auth_event(
            AuditEventType.LOGIN_FAILURE,
            "user-1",
            success=False,
        )

        events = await audit_logger_instance.query(
            event_types=[AuditEventType.LOGIN_FAILURE]
        )
        assert all(e.event_type == AuditEventType.LOGIN_FAILURE for e in events)

    @pytest.mark.asyncio
    async def test_query_by_time_range(self, audit_logger_instance):
        """Test querying events by time range."""
        now = datetime.now(UTC)

        event = AuditEvent(
            event_type=AuditEventType.DATA_READ,
            timestamp=now,
            user_id="user-1",
        )
        await audit_logger_instance.log(event)

        # Query with time range
        start = now - timedelta(minutes=5)
        end = now + timedelta(minutes=5)
        events = await audit_logger_instance.query(start_time=start, end_time=end)
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_query_with_limit(self, audit_logger_instance):
        """Test querying events with limit."""
        for i in range(10):
            await audit_logger_instance.log_auth_event(
                AuditEventType.LOGIN_SUCCESS,
                f"user-{i}",
                success=True,
            )

        events = await audit_logger_instance.query(limit=5)
        assert len(events) == 5

    @pytest.mark.asyncio
    async def test_query_by_severity(self, audit_logger_instance):
        """Test querying events by minimum severity."""
        await audit_logger_instance.log_auth_event(
            AuditEventType.LOGIN_SUCCESS,
            "user-1",
            success=True,  # INFO severity
        )
        await audit_logger_instance.log_security_event(
            AuditEventType.SUSPICIOUS_ACTIVITY,
            user_id="user-1",
            severity=AuditSeverity.WARNING,
        )

        events = await audit_logger_instance.query(min_severity=AuditSeverity.WARNING)
        assert all(e.severity.value in ["warning", "error", "critical"] for e in events)


# =============================================================================
# Audit Logger Tests - Security Events
# =============================================================================


class TestAuditSecurityEvents:
    """Tests for security-specific audit queries."""

    @pytest.mark.asyncio
    async def test_get_recent_security_events(self, audit_logger_instance):
        """Test getting recent security events."""
        # Log various events
        await audit_logger_instance.log_auth_event(
            AuditEventType.LOGIN_SUCCESS,
            "user-1",
            success=True,
        )
        await audit_logger_instance.log_auth_event(
            AuditEventType.LOGIN_FAILURE,
            "user-1",
            success=False,
        )
        await audit_logger_instance.log_security_event(
            AuditEventType.RATE_LIMIT_EXCEEDED,
            tenant_id="tenant-123",
            user_id="user-1",
        )

        events = await audit_logger_instance.get_recent_security_events(
            "tenant-123", limit=10
        )

        # Should only include security-related events
        security_types = {
            AuditEventType.LOGIN_FAILURE,
            AuditEventType.PERMISSION_DENIED,
            AuditEventType.RATE_LIMIT_EXCEEDED,
            AuditEventType.SUSPICIOUS_ACTIVITY,
            AuditEventType.INJECTION_ATTEMPT,
            AuditEventType.CROSS_TENANT_ATTEMPT,
        }

        for event in events:
            assert event.event_type in security_types

    @pytest.mark.asyncio
    async def test_get_user_activity(self, audit_logger_instance):
        """Test getting user activity log."""
        user_id = "active-user"
        tenant_id = "tenant-123"

        await audit_logger_instance.log_auth_event(
            AuditEventType.LOGIN_SUCCESS,
            user_id,
            tenant_id=tenant_id,
            success=True,
        )
        await audit_logger_instance.log_data_access(
            AuditEventType.DATA_READ,
            tenant_id,
            user_id,
            "document",
            "doc-001",
        )

        events = await audit_logger_instance.get_user_activity(
            tenant_id, user_id, limit=50
        )

        assert len(events) >= 2
        assert all(e.user_id == user_id for e in events)


# =============================================================================
# Audit Logger Tests - Buffer and Flush
# =============================================================================


class TestAuditBufferAndFlush:
    """Tests for audit buffer management."""

    @pytest.mark.asyncio
    async def test_buffer_flushes_when_full(self, audit_logger_instance):
        """Test that buffer flushes when reaching capacity."""
        audit_logger_instance._buffer_size = 5

        for i in range(6):
            await audit_logger_instance.log_auth_event(
                AuditEventType.LOGIN_SUCCESS,
                f"user-{i}",
                success=True,
            )

        # Buffer should have been flushed and started fresh
        assert len(audit_logger_instance._buffer) < 5

    @pytest.mark.asyncio
    async def test_manual_flush(self, audit_logger_instance):
        """Test manual flush clears buffer."""
        await audit_logger_instance.log_auth_event(
            AuditEventType.LOGIN_SUCCESS,
            "user-1",
            success=True,
        )

        assert len(audit_logger_instance._buffer) > 0

        await audit_logger_instance.flush()

        assert len(audit_logger_instance._buffer) == 0

    @pytest.mark.asyncio
    async def test_flush_empty_buffer(self, audit_logger_instance):
        """Test flushing empty buffer is safe."""
        await audit_logger_instance.flush()  # Should not raise


# =============================================================================
# Audit Logger Tests - Severity Filtering
# =============================================================================


class TestAuditSeverityFiltering:
    """Tests for severity-based filtering."""

    @pytest.mark.asyncio
    async def test_debug_events_filtered_by_default(self, audit_logger_instance):
        """Test that debug events are filtered by default."""
        event = AuditEvent(
            event_type=AuditEventType.DATA_READ,
            timestamp=datetime.now(UTC),
            severity=AuditSeverity.DEBUG,
        )

        await audit_logger_instance.log(event)

        # Debug events should be filtered
        assert len(audit_logger_instance._buffer) == 0

    @pytest.mark.asyncio
    async def test_debug_events_logged_when_enabled(self, audit_logger_debug):
        """Test debug events logged when min severity is debug."""
        event = AuditEvent(
            event_type=AuditEventType.DATA_READ,
            timestamp=datetime.now(UTC),
            severity=AuditSeverity.DEBUG,
        )

        await audit_logger_debug.log(event)

        assert len(audit_logger_debug._buffer) == 1

    def test_should_log_severity_check(self, audit_logger_instance):
        """Test severity comparison logic."""
        # Default min severity is INFO
        assert audit_logger_instance._should_log(AuditSeverity.INFO) is True
        assert audit_logger_instance._should_log(AuditSeverity.WARNING) is True
        assert audit_logger_instance._should_log(AuditSeverity.CRITICAL) is True
        assert audit_logger_instance._should_log(AuditSeverity.DEBUG) is False


# =============================================================================
# Audit Event Model Tests
# =============================================================================


class TestAuditEventModel:
    """Tests for AuditEvent model."""

    def test_audit_event_to_dict(self):
        """Test AuditEvent serialization."""
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            tenant_id="tenant-123",
            user_id="user-456",
            session_id="session-789",
            resource_type="user",
            resource_id="user-456",
            action="login",
            details={"method": "password"},
            severity=AuditSeverity.INFO,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=True,
        )

        data = event.to_dict()

        assert data["event_type"] == "auth.login.success"
        assert data["tenant_id"] == "tenant-123"
        assert data["user_id"] == "user-456"
        assert data["success"] is True
        assert data["details"]["method"] == "password"
        assert "event_id" in data

    def test_audit_event_auto_generated_id(self):
        """Test that event ID is auto-generated."""
        event1 = AuditEvent(
            event_type=AuditEventType.DATA_READ,
            timestamp=datetime.now(UTC),
        )
        event2 = AuditEvent(
            event_type=AuditEventType.DATA_READ,
            timestamp=datetime.now(UTC),
        )

        assert event1.event_id != event2.event_id

    def test_audit_event_type_enum_values(self):
        """Test audit event type enum values."""
        assert AuditEventType.LOGIN_SUCCESS.value == "auth.login.success"
        assert AuditEventType.DATA_CREATED.value == "data.created"
        assert AuditEventType.AGENT_EXECUTED.value == "agent.executed"
        assert AuditEventType.RATE_LIMIT_EXCEEDED.value == "security.ratelimit.exceeded"

    def test_audit_severity_ordering(self, audit_logger_instance):
        """Test severity ordering is correct."""
        order = audit_logger_instance._severity_order

        assert order[AuditSeverity.DEBUG] < order[AuditSeverity.INFO]
        assert order[AuditSeverity.INFO] < order[AuditSeverity.WARNING]
        assert order[AuditSeverity.WARNING] < order[AuditSeverity.ERROR]
        assert order[AuditSeverity.ERROR] < order[AuditSeverity.CRITICAL]


# =============================================================================
# Singleton Instance Tests
# =============================================================================


class TestSingletonInstances:
    """Tests for singleton service instances."""

    def test_rate_limiter_singleton_exists(self):
        """Test rate limiter singleton is available."""
        assert rate_limiter is not None
        assert isinstance(rate_limiter, RateLimiter)

    def test_tenant_isolation_singleton_exists(self):
        """Test tenant isolation singleton is available."""
        assert tenant_isolation_service is not None
        assert isinstance(tenant_isolation_service, TenantIsolationService)

    def test_permissions_singleton_exists(self):
        """Test permissions singleton is available."""
        assert permissions_service is not None
        assert isinstance(permissions_service, PermissionsService)

    def test_audit_logger_singleton_exists(self):
        """Test audit logger singleton is available."""
        assert audit_logger is not None
        assert isinstance(audit_logger, AuditLogger)


# =============================================================================
# Integration Tests
# =============================================================================


class TestSecurityIntegration:
    """Integration tests for security services working together."""

    @pytest.mark.asyncio
    async def test_rate_limit_with_audit_logging(
        self, rate_limiter_instance, audit_logger_instance
    ):
        """Test rate limiting triggers audit logging."""
        config = RateLimitConfig(
            name="test_audit_limit",
            max_requests=2,
            window_seconds=60,
        )
        rate_limiter_instance.register_limit(config)

        # Exhaust limit
        await rate_limiter_instance.check("test_audit_limit", "user-001")
        await rate_limiter_instance.check("test_audit_limit", "user-001")

        # This should be rate limited
        result = await rate_limiter_instance.check("test_audit_limit", "user-001")

        if not result.allowed:
            # Log the rate limit event
            await audit_logger_instance.log_security_event(
                AuditEventType.RATE_LIMIT_EXCEEDED,
                user_id="user-001",
                details={"limit": "test_audit_limit"},
            )

        events = await audit_logger_instance.query(
            event_types=[AuditEventType.RATE_LIMIT_EXCEEDED]
        )
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_permission_check_with_audit_logging(
        self, permissions_svc, audit_logger_instance
    ):
        """Test permission check triggers audit logging."""
        user_perms = permissions_svc.create_user_permissions(
            user_id="user-001",
            tenant_id="tenant-123",
            role=Role.MEMBER,
        )

        # Attempt unauthorized action
        try:
            permissions_svc.check_permission(user_perms, Permission.ORG_DELETE)
        except PermissionError:
            await audit_logger_instance.log(AuditEvent(
                event_type=AuditEventType.PERMISSION_DENIED,
                timestamp=datetime.now(UTC),
                tenant_id="tenant-123",
                user_id="user-001",
                details={"permission": Permission.ORG_DELETE.value},
                severity=AuditSeverity.WARNING,
                success=False,
            ))

        events = await audit_logger_instance.query(
            event_types=[AuditEventType.PERMISSION_DENIED]
        )
        assert len(events) == 1
        assert events[0].details["permission"] == "org:delete"

    def test_tenant_isolation_with_permissions(self, tenant_isolation, permissions_svc):
        """Test tenant isolation works with permission system."""
        # Create context
        context = tenant_isolation.create_tenant_context(
            tenant_id="tenant-123",
            user_id="user-456",
            permissions={Permission.PROJECT_READ, Permission.PROJECT_WRITE},
        )

        # Verify permissions are in context
        assert Permission.PROJECT_READ in context.permissions
        assert Permission.PROJECT_WRITE in context.permissions

        # Verify tenant access
        assert context.can_access_resource("tenant-123") is True
        assert context.can_access_resource("tenant-999") is False


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_rate_limiter_with_zero_cost(self, rate_limiter_instance, sliding_window_config):
        """Test rate limiter with zero cost (status check)."""
        rate_limiter_instance.register_limit(sliding_window_config)

        # Zero cost should not consume quota
        for _ in range(10):
            result = await rate_limiter_instance.check(
                "test_sliding", "user-001", cost=0
            )
            assert result.allowed is True

    def test_tenant_context_default_permissions(self):
        """Test TenantContext default permissions."""
        context = TenantContext(
            tenant_id="tenant-123",
            user_id="user-456",
        )
        assert context.permissions == set()

    def test_tool_permission_default_values(self):
        """Test ToolPermission default values."""
        tool = ToolPermission(tool_name="test_tool")

        assert tool.allowed_roles == {Role.OWNER, Role.ADMIN}
        assert tool.requires_confirmation is False
        assert tool.max_executions_per_hour == 100
        assert tool.allowed_parameters is None
        assert tool.blocked_parameters == set()

    def test_user_permissions_tool_override(self, permissions_svc):
        """Test user permissions with tool override."""
        custom_tool = ToolPermission(
            tool_name="custom_tool",
            allowed_roles={Role.GUEST},  # Allow guests
        )

        user_perms = permissions_svc.create_user_permissions(
            user_id="guest-001",
            tenant_id="tenant-123",
            role=Role.GUEST,
        )
        user_perms.tool_overrides["custom_tool"] = custom_tool

        # Guest should be able to use this specific tool
        assert user_perms.can_use_tool("custom_tool") is True

    @pytest.mark.asyncio
    async def test_audit_truncates_long_summaries(self, audit_logger_instance):
        """Test audit logger truncates long input/output summaries."""
        long_input = "a" * 1000
        long_output = "b" * 1000

        await audit_logger_instance.log_agent_execution(
            tenant_id="tenant-123",
            user_id="user-456",
            agent_id="agent-789",
            agent_type="test",
            input_summary=long_input,
            output_summary=long_output,
            success=True,
        )

        events = await audit_logger_instance.query()
        details = events[0].details

        # Should be truncated to 500 chars
        assert len(details["input_summary"]) <= 500
        assert len(details["output_summary"]) <= 500

    def test_rate_limit_config_post_init_token_bucket(self):
        """Test RateLimitConfig post_init for token bucket."""
        config = RateLimitConfig(
            name="test",
            max_requests=100,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET,
        )

        # Should auto-calculate burst_limit and refill_rate
        assert config.burst_limit == 100
        assert config.refill_rate == pytest.approx(100 / 60)

    def test_rate_limit_state_post_init_token_bucket(self):
        """Test RateLimitState post_init for token bucket."""
        config = RateLimitConfig(
            name="test",
            max_requests=50,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            burst_limit=75,
        )
        state = RateLimitState(key="test_key", config=config)

        # Should initialize with full tokens
        assert state.tokens == 75
        assert state.last_refill > 0

    @pytest.mark.asyncio
    async def test_concurrent_rate_limit_checks(self, rate_limiter_instance, sliding_window_config):
        """Test concurrent rate limit checks are safe."""
        rate_limiter_instance.register_limit(sliding_window_config)

        # Run many concurrent checks
        tasks = [
            rate_limiter_instance.check("test_sliding", "concurrent-user")
            for _ in range(20)
        ]
        results = await asyncio.gather(*tasks)

        # Exactly 5 should be allowed (the limit)
        allowed = sum(1 for r in results if r.allowed)
        assert allowed == 5
