"""API dependencies with multi-tenant support."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db, get_read_db

logger = structlog.get_logger()
from app.core.security import verify_token
from app.core.multitenancy import (
    get_current_tenant_id,
    set_current_tenant_id,
    set_tenant_context,
)
from app.models.user import User
from app.services.auth import AuthService

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials

    token_data = verify_token(token, token_type="access")
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(token_data.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get current user if authenticated, otherwise return None.

    Use this for endpoints that work both with and without authentication.
    """
    if not credentials:
        return None

    token = credentials.credentials
    token_data = verify_token(token, token_type="access")

    if not token_data:
        return None

    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(token_data.user_id)

    if not user or not user.is_active:
        return None

    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    return user


async def get_current_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    """Get current admin user."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# =============================================================================
# MULTI-TENANT DEPENDENCIES
# =============================================================================


async def get_tenant_id_from_request(request: Request) -> str | None:
    """Extract tenant ID from request headers or context.

    Priority:
    1. X-Tenant-ID header (explicit)
    2. X-Organization-ID header (alias)
    3. Context variable (set by middleware)
    """
    # Check headers first
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        return tenant_id

    tenant_id = request.headers.get("X-Organization-ID")
    if tenant_id:
        return tenant_id

    # Fall back to context variable
    return get_current_tenant_id()


async def get_db_with_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AsyncSession:
    """Get database session with tenant context set for RLS.

    This is the CRITICAL dependency that enforces data isolation.
    Use this instead of get_db in all tenant-scoped endpoints.
    """
    # Get tenant ID from request
    tenant_id = await get_tenant_id_from_request(request)

    # If no explicit tenant, try to get user's default organization
    if not tenant_id and hasattr(current_user, 'default_organization_id'):
        tenant_id = str(current_user.default_organization_id) if current_user.default_organization_id else None

    # Set tenant context in PostgreSQL for RLS
    if tenant_id:
        await set_tenant_context(db, tenant_id)
        # Also set in context var for other uses
        set_current_tenant_id(tenant_id)

    return db


async def get_read_db_with_tenant(
    request: Request,
    db: AsyncSession = Depends(get_read_db),
    current_user: User = Depends(get_current_user),
) -> AsyncSession:
    """Get read-only database session with tenant context for RLS.

    Use for read-heavy operations that can use read replicas.
    """
    tenant_id = await get_tenant_id_from_request(request)

    if not tenant_id and hasattr(current_user, 'default_organization_id'):
        tenant_id = str(current_user.default_organization_id) if current_user.default_organization_id else None

    if tenant_id:
        await set_tenant_context(db, tenant_id)
        set_current_tenant_id(tenant_id)

    return db


async def require_tenant(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> str:
    """Require a valid tenant ID in the request.

    Use this dependency when an endpoint MUST have tenant context.
    Raises 400 if no tenant ID is available.
    """
    tenant_id = await get_tenant_id_from_request(request)

    if not tenant_id and hasattr(current_user, 'default_organization_id'):
        tenant_id = str(current_user.default_organization_id) if current_user.default_organization_id else None

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required. Provide X-Tenant-ID header or set default organization.",
        )

    return tenant_id


# Alias for backward compatibility
get_current_tenant = require_tenant
get_optional_current_user = get_current_user_optional


async def verify_tenant_access(
    tenant_id: str = Depends(require_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Verify the current user has access to the specified tenant.

    Checks organization membership before allowing access.
    Returns the verified tenant_id.
    """
    # Import here to avoid circular imports
    from app.models.organization import OrganizationMember

    # Check if user is member of the organization
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == tenant_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active == True,
        )
    )
    membership = result.scalar_one_or_none()

    if not membership and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this organization",
        )

    return tenant_id


class TenantScoped:
    """Dependency class for tenant-scoped operations with role checking.

    Usage:
        @router.get("/items")
        async def list_items(
            tenant: TenantScoped = Depends(TenantScoped(min_role="member")),
            db: AsyncSession = Depends(get_db_with_tenant),
        ):
            # tenant.id contains verified tenant ID
            # tenant.role contains user's role in tenant
            pass
    """

    ROLE_HIERARCHY = ["member", "admin", "owner"]

    def __init__(self, min_role: str = "member"):
        self.min_role = min_role
        self.id: str | None = None
        self.role: str | None = None

    async def __call__(
        self,
        request: Request,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> "TenantScoped":
        """Verify tenant access and minimum role."""
        from app.models.organization import OrganizationMember

        tenant_id = await get_tenant_id_from_request(request)

        if not tenant_id and hasattr(current_user, 'default_organization_id'):
            tenant_id = str(current_user.default_organization_id) if current_user.default_organization_id else None

        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant context required",
            )

        # Check membership and role
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == tenant_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.is_active == True,
            )
        )
        membership = result.scalar_one_or_none()

        if not membership and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this organization",
            )

        # For admin users without membership, grant owner-level access
        user_role = membership.role if membership else "owner"

        # Check role hierarchy
        if self._role_level(user_role) < self._role_level(self.min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {self.min_role} role or higher",
            )

        self.id = tenant_id
        self.role = user_role

        # Set tenant context for RLS
        await set_tenant_context(db, tenant_id)
        set_current_tenant_id(tenant_id)

        return self

    def _role_level(self, role: str) -> int:
        """Get numeric level for role comparison."""
        try:
            return self.ROLE_HIERARCHY.index(role)
        except ValueError:
            return -1


# =============================================================================
# RATE LIMITING DEPENDENCIES
# =============================================================================


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )


async def check_rate_limit(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> None:
    """Check rate limit for the current user/tenant.

    Uses Redis-based rate limiting with tenant isolation.
    """
    from app.core.cache import tenant_rate_limiter

    tenant_id = await get_tenant_id_from_request(request)
    identifier = f"user:{current_user.id}"

    allowed, info = await tenant_rate_limiter.is_allowed(
        identifier=identifier,
        tenant_id=tenant_id,
    )

    if not allowed:
        raise RateLimitExceeded(retry_after=info.get("retry_after", 60))


async def check_tenant_rate_limit(
    request: Request,
    tenant_id: str = Depends(require_tenant),
) -> None:
    """Check rate limit at the tenant level (shared across all users)."""
    from app.core.cache import tenant_rate_limiter

    allowed, info = await tenant_rate_limiter.is_allowed(
        identifier="tenant",
        tenant_id=tenant_id,
    )

    if not allowed:
        raise RateLimitExceeded(retry_after=info.get("retry_after", 60))
