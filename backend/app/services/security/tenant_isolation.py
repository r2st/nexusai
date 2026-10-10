"""Tenant Isolation Service.

Provides strict tenant data separation and access control:
- Row-Level Security (RLS) enforcement
- Cross-tenant access prevention
- Tenant context validation
- Data boundary enforcement
"""

from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


class TenantScope(str, Enum):
    """Scope levels for tenant data access."""

    ORGANIZATION = "organization"  # Full organization access
    PROJECT = "project"  # Single project access
    TEAM = "team"  # Team-level access
    PERSONAL = "personal"  # Individual user only


@dataclass
class TenantContext:
    """Current tenant context for request processing."""

    tenant_id: str
    user_id: str
    scope: TenantScope = TenantScope.ORGANIZATION
    project_id: str | None = None
    team_id: str | None = None
    is_admin: bool = False
    permissions: set[str] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = set()

    def can_access_project(self, project_id: str) -> bool:
        """Check if context allows access to a project."""
        if self.is_admin:
            return True
        if self.scope == TenantScope.ORGANIZATION:
            return True
        if self.scope == TenantScope.PROJECT:
            return self.project_id == project_id
        return False

    def can_access_resource(self, resource_tenant_id: str) -> bool:
        """Check if context allows access to a resource."""
        return self.tenant_id == resource_tenant_id or self.is_admin


# Context variable to hold current tenant context
_current_context: ContextVar[TenantContext | None] = ContextVar(
    "tenant_context", default=None
)


def get_tenant_context() -> TenantContext | None:
    """Get the current tenant context."""
    return _current_context.get()


def set_tenant_context(context: TenantContext | None) -> None:
    """Set the current tenant context."""
    _current_context.set(context)


class TenantIsolationService:
    """
    Service for enforcing tenant data isolation.

    Ensures:
    - All queries are scoped to current tenant
    - Cross-tenant access is prevented
    - RLS policies are properly enforced
    - Tenant context is validated
    """

    # Tables that require tenant isolation
    ISOLATED_TABLES = [
        "organizations",
        "organization_members",
        "projects",
        "project_members",
        "connections",
        "blueprints",
        "pipelines",
        "conversations",
        "messages",
        "documents",
        "document_chunks",
        "ai_usage_logs",
        "ai_analytics_metrics",
        "agents",
        "agent_tools",
        "agent_executions",
        "openapi_actions",
        "workflow_executions",
        "audit_logs",
    ]

    def __init__(self, strict_mode: bool = True):
        """
        Initialize tenant isolation service.

        Args:
            strict_mode: If True, reject queries without tenant context
        """
        self.strict_mode = strict_mode
        self._initialized = False

    async def initialize(self, session: AsyncSession) -> None:
        """Initialize RLS policies in the database."""
        if self._initialized:
            return

        await self._create_rls_policies(session)
        self._initialized = True
        logger.info("Tenant isolation service initialized")

    async def _create_rls_policies(self, session: AsyncSession) -> None:
        """Create Row-Level Security policies for all isolated tables."""
        for table in self.ISOLATED_TABLES:
            try:
                # Enable RLS
                await session.execute(text(f"""
                    ALTER TABLE IF EXISTS {table} ENABLE ROW LEVEL SECURITY
                """))

                # Force RLS for table owner (critical)
                await session.execute(text(f"""
                    ALTER TABLE IF EXISTS {table} FORCE ROW LEVEL SECURITY
                """))

                # Drop existing policy
                await session.execute(text(f"""
                    DROP POLICY IF EXISTS tenant_isolation ON {table}
                """))

                # Create strict isolation policy
                if self.strict_mode:
                    await session.execute(text(f"""
                        CREATE POLICY tenant_isolation ON {table}
                        FOR ALL
                        USING (
                            tenant_id = current_setting('app.current_tenant_id', true)::uuid
                        )
                        WITH CHECK (
                            tenant_id = current_setting('app.current_tenant_id', true)::uuid
                        )
                    """))
                else:
                    # Development mode - allow null tenant context
                    await session.execute(text(f"""
                        CREATE POLICY tenant_isolation ON {table}
                        FOR ALL
                        USING (
                            tenant_id = current_setting('app.current_tenant_id', true)::uuid
                            OR current_setting('app.current_tenant_id', true) IS NULL
                        )
                    """))

                logger.debug(f"Created RLS policy for table: {table}")

            except Exception as e:
                logger.warning(f"Could not create RLS for {table}: {e}")

        await session.commit()

    async def set_session_tenant(
        self,
        session: AsyncSession,
        tenant_id: str,
    ) -> None:
        """Set the tenant context for a database session."""
        await session.execute(
            text("SET app.current_tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )
        logger.debug("Set session tenant", tenant_id=tenant_id)

    async def clear_session_tenant(self, session: AsyncSession) -> None:
        """Clear the tenant context from a database session."""
        await session.execute(text("RESET app.current_tenant_id"))

    def validate_tenant_access(
        self,
        resource_tenant_id: str,
        context: TenantContext | None = None,
    ) -> bool:
        """
        Validate that current context can access a resource.

        Args:
            resource_tenant_id: The tenant ID of the resource
            context: Optional context override

        Returns:
            True if access is allowed

        Raises:
            PermissionError if access is denied
        """
        ctx = context or get_tenant_context()

        if ctx is None:
            if self.strict_mode:
                raise PermissionError("No tenant context set")
            return True

        if not ctx.can_access_resource(resource_tenant_id):
            logger.warning(
                "Cross-tenant access denied",
                current_tenant=ctx.tenant_id,
                resource_tenant=resource_tenant_id,
                user_id=ctx.user_id,
            )
            raise PermissionError(
                f"Access denied: cannot access resource from tenant {resource_tenant_id}"
            )

        return True

    def validate_project_access(
        self,
        project_id: str,
        context: TenantContext | None = None,
    ) -> bool:
        """Validate access to a specific project."""
        ctx = context or get_tenant_context()

        if ctx is None:
            if self.strict_mode:
                raise PermissionError("No tenant context set")
            return True

        if not ctx.can_access_project(project_id):
            logger.warning(
                "Project access denied",
                current_project=ctx.project_id,
                requested_project=project_id,
                user_id=ctx.user_id,
            )
            raise PermissionError(f"Access denied to project {project_id}")

        return True

    async def verify_rls_enabled(self, session: AsyncSession) -> dict[str, bool]:
        """Verify RLS is enabled on all isolated tables."""
        result = await session.execute(text("""
            SELECT
                tablename,
                rowsecurity
            FROM pg_tables
            WHERE schemaname = 'public'
        """))

        status = {row.tablename: row.rowsecurity for row in result}

        # Check isolated tables
        missing = []
        for table in self.ISOLATED_TABLES:
            if table not in status:
                missing.append(table)
            elif not status.get(table):
                missing.append(table)

        if missing:
            logger.warning("RLS not enabled on tables", tables=missing)

        return status

    def create_tenant_context(
        self,
        tenant_id: str,
        user_id: str,
        scope: TenantScope = TenantScope.ORGANIZATION,
        project_id: str | None = None,
        is_admin: bool = False,
        permissions: set[str] | None = None,
    ) -> TenantContext:
        """Create a new tenant context."""
        return TenantContext(
            tenant_id=tenant_id,
            user_id=user_id,
            scope=scope,
            project_id=project_id,
            is_admin=is_admin,
            permissions=permissions or set(),
        )

    class TenantContextManager:
        """Context manager for tenant-scoped operations."""

        def __init__(
            self,
            context: TenantContext,
            session: AsyncSession | None = None,
            service: "TenantIsolationService" = None,
        ):
            self.context = context
            self.session = session
            self.service = service
            self._previous_context = None

        async def __aenter__(self) -> TenantContext:
            self._previous_context = get_tenant_context()
            set_tenant_context(self.context)

            if self.session and self.service:
                await self.service.set_session_tenant(
                    self.session, self.context.tenant_id
                )

            return self.context

        async def __aexit__(self, *args) -> None:
            if self.session and self.service:
                await self.service.clear_session_tenant(self.session)

            set_tenant_context(self._previous_context)

    def scope(
        self,
        context: TenantContext,
        session: AsyncSession | None = None,
    ) -> TenantContextManager:
        """Create a context manager for tenant-scoped operations."""
        return self.TenantContextManager(context, session, self)


# Singleton instance
tenant_isolation_service = TenantIsolationService()
