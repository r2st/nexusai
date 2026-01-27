"""Multi-tenancy support with PostgreSQL Row-Level Security (RLS).

This module provides:
- Tenant/Organization model and management
- PostgreSQL RLS policy enforcement
- Tenant context for request handling
- Per-tenant database isolation
"""

from contextvars import ContextVar
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

# Context variable to hold current tenant ID for RLS
current_tenant_id: ContextVar[str | None] = ContextVar("current_tenant_id", default=None)


def get_current_tenant_id() -> str | None:
    """Get the current tenant ID from context."""
    return current_tenant_id.get()


def set_current_tenant_id(tenant_id: str | None) -> None:
    """Set the current tenant ID in context."""
    current_tenant_id.set(tenant_id)


class TenantContext:
    """Context manager for tenant-scoped operations."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.token: Any = None

    def __enter__(self) -> "TenantContext":
        self.token = current_tenant_id.set(self.tenant_id)
        return self

    def __exit__(self, *args: Any) -> None:
        current_tenant_id.reset(self.token)


async def set_tenant_context(session: AsyncSession, tenant_id: str | None) -> None:
    """Set the tenant context for RLS policies in PostgreSQL.

    This sets the session variable that RLS policies use to filter data.
    """
    if tenant_id:
        await session.execute(
            text("SET app.current_tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )
    else:
        await session.execute(text("RESET app.current_tenant_id"))


async def create_rls_policies(session: AsyncSession, strict_mode: bool = True) -> None:
    """Create Row-Level Security policies for all tenant-scoped tables.

    This should be run during database initialization.

    Args:
        session: Database session
        strict_mode: If True, reject queries without tenant context (SECURE).
                    If False, allow NULL tenant_id (INSECURE - dev only).
    """
    # List of tables that need RLS policies
    tenant_tables = [
        "organizations",
        "organization_members",
        "projects",
        "project_members",
        "connections",
        "blueprints",
        "pipelines",
        "conversations",
        "documents",
        "document_chunks",
        "ai_usage_logs",
        "ai_analytics_metrics",
        # New agent tables
        "agents",
        "agent_tools",
        "agent_executions",
        "openapi_actions",
        "workflow_executions",
    ]

    for table in tenant_tables:
        # Enable RLS on table
        await session.execute(text(f"""
            ALTER TABLE IF EXISTS {table} ENABLE ROW LEVEL SECURITY
        """))

        # Force RLS for table owner too (critical for security)
        await session.execute(text(f"""
            ALTER TABLE IF EXISTS {table} FORCE ROW LEVEL SECURITY
        """))

        # Drop existing policy
        await session.execute(text(f"""
            DROP POLICY IF EXISTS tenant_isolation_policy ON {table}
        """))

        # Create STRICT policy - requires tenant_id to be set
        # This is the SECURE version that prevents data leaks
        if strict_mode:
            await session.execute(text(f"""
                CREATE POLICY tenant_isolation_policy ON {table}
                FOR ALL
                USING (
                    -- Only allow access when tenant_id matches current tenant
                    tenant_id = current_setting('app.current_tenant_id', true)::uuid
                )
                WITH CHECK (
                    -- Only allow inserts/updates with matching tenant_id
                    tenant_id = current_setting('app.current_tenant_id', true)::uuid
                )
            """))
        else:
            # INSECURE mode - for development/testing only
            # Allows access when no tenant context is set
            await session.execute(text(f"""
                CREATE POLICY tenant_isolation_policy ON {table}
                FOR ALL
                USING (
                    tenant_id = current_setting('app.current_tenant_id', true)::uuid
                    OR current_setting('app.current_tenant_id', true) IS NULL
                    OR current_setting('app.current_tenant_id', true) = ''
                )
            """))

    await session.commit()


async def create_superuser_bypass_policy(session: AsyncSession) -> None:
    """Create a bypass policy for superuser/admin operations.

    This allows system-level operations without tenant context.
    Should be used sparingly and only for admin operations.
    """
    # This would typically check a separate superuser flag
    # For now, we skip this as it's a security risk
    pass


async def verify_rls_enabled(session: AsyncSession) -> dict[str, bool]:
    """Verify RLS is enabled on all tenant tables.

    Returns a dict of table -> rls_enabled status.
    """
    result = await session.execute(text("""
        SELECT
            schemaname,
            tablename,
            rowsecurity
        FROM pg_tables
        WHERE schemaname = 'public'
    """))

    return {
        row.tablename: row.rowsecurity
        for row in result
    }


def generate_domain_id(
    tenant_id: str,
    plugin: str,
    connection_id: str,
    scope_type: str,
    scope_id: str,
) -> str:
    """Generate a 5-segment domain ID for project-scoped entities.

    Format: {tenant_id}:{plugin}:{connection_id}:{scope_type}:{scope_id}

    Example: org123:github:conn1:repo:myorg/myrepo
    """
    return f"{tenant_id}:{plugin}:{connection_id}:{scope_type}:{scope_id}"


def parse_domain_id(domain_id: str) -> dict[str, str]:
    """Parse a 5-segment domain ID into its components."""
    parts = domain_id.split(":", 4)
    if len(parts) != 5:
        raise ValueError(f"Invalid domain ID format: {domain_id}")

    return {
        "tenant_id": parts[0],
        "plugin": parts[1],
        "connection_id": parts[2],
        "scope_type": parts[3],
        "scope_id": parts[4],
    }


def generate_tenant_id() -> str:
    """Generate a new unique tenant ID."""
    return str(uuid4())
