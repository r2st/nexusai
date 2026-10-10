"""Database configuration and session management.

Scalable database layer supporting:
- Connection pooling with PgBouncer-ready configuration
- Read replica support for horizontal scaling
- Health checks and connection monitoring
- Async session management with proper isolation
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    metadata = metadata


def create_engine_with_config(
    database_url: str,
    pool_size: int = 20,
    max_overflow: int = 30,
    pool_timeout: int = 30,
    pool_recycle: int = 1800,
    echo: bool = False,
    use_null_pool: bool = False,
) -> AsyncEngine:
    """Create an async engine with optimized configuration.

    Args:
        database_url: Database connection URL
        pool_size: Number of connections to keep in the pool
        max_overflow: Max connections beyond pool_size
        pool_timeout: Seconds to wait for connection
        pool_recycle: Recycle connections after this many seconds
        echo: Enable SQL logging
        use_null_pool: Use NullPool (for serverless/PgBouncer)

    Returns:
        Configured AsyncEngine
    """
    engine_kwargs: dict[str, Any] = {
        "echo": echo,
        "pool_pre_ping": True,
        "pool_recycle": pool_recycle,
    }

    if use_null_pool:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs.update({
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout,
        })

    # Connection arguments for better performance
    engine_kwargs["connect_args"] = {
        "server_settings": {
            "application_name": settings.APP_NAME,
            "statement_timeout": "30000",
            "lock_timeout": "10000",
        },
        "command_timeout": 60,
    }

    return create_async_engine(database_url, **engine_kwargs)


# Primary write engine
engine = create_engine_with_config(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=False,  # Set to True for SQL debugging
    use_null_pool=getattr(settings, "DATABASE_USE_NULL_POOL", False),
)

# Read replica engine (optional - falls back to primary if not configured)
_read_replica_url = getattr(settings, "DATABASE_READ_REPLICA_URL", None)
read_engine = (
    create_engine_with_config(
        _read_replica_url,
        pool_size=settings.DATABASE_POOL_SIZE * 2,
        max_overflow=settings.DATABASE_MAX_OVERFLOW * 2,
        echo=False,
    )
    if _read_replica_url
    else engine
)

# Session factories
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Read-only session factory (uses replica if available)
async_read_session_factory = async_sessionmaker(
    read_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions (read-write)."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.warning("Database session rollback", error_type=type(e).__name__, error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_read_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting read-only database sessions (uses replica)."""
    async with async_read_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions outside of FastAPI dependencies."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.warning("Database context rollback", error_type=type(e).__name__, error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_read_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for read-only database sessions."""
    async with async_read_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context_with_tenant(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions with tenant context set.

    This is the CRITICAL context manager for background tasks that need
    tenant data isolation via RLS policies.

    Args:
        tenant_id: The tenant/organization ID for RLS enforcement

    Example:
        async with get_db_context_with_tenant(tenant_id) as session:
            # RLS policies are automatically enforced
            results = await session.execute(select(Project))
            # Only returns projects for this tenant
    """
    from app.core.multitenancy import set_tenant_context

    async with async_session_factory() as session:
        try:
            # Set tenant context for RLS enforcement
            await set_tenant_context(session, tenant_id)

            yield session
            await session.commit()
        except Exception as e:
            logger.warning("Database tenant context rollback", tenant_id=tenant_id, error_type=type(e).__name__, error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_read_db_context_with_tenant(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Context manager for read-only sessions with tenant context.

    Use for read-heavy background tasks that can use read replicas.

    Args:
        tenant_id: The tenant/organization ID for RLS enforcement
    """
    from app.core.multitenancy import set_tenant_context

    async with async_read_session_factory() as session:
        try:
            # Set tenant context for RLS enforcement
            await set_tenant_context(session, tenant_id)

            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database with required extensions.

    Note: Table creation is handled by Alembic migrations.
    Run `make migrate` to apply migrations after starting the database.
    """
    async with engine.begin() as conn:
        # Create required PostgreSQL extensions
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gin"))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))

        # Note: We don't call create_all() here anymore.
        # Use Alembic migrations for schema management:
        #   make migrate          - Apply all pending migrations
        #   make migrate-create   - Create a new migration
        #   make migrate-down     - Rollback last migration


async def close_db() -> None:
    """Close database connections gracefully."""
    await engine.dispose()
    if read_engine != engine:
        await read_engine.dispose()


async def check_db_health() -> dict[str, Any]:
    """Check database connectivity and pool status."""
    result = {"status": "healthy", "primary": {}, "replica": {}}

    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            pool = engine.pool
            result["primary"] = {
                "status": "healthy",
                "pool_size": pool.size() if hasattr(pool, "size") else "N/A",
                "checked_in": pool.checkedin() if hasattr(pool, "checkedin") else "N/A",
                "checked_out": pool.checkedout() if hasattr(pool, "checkedout") else "N/A",
            }
    except Exception as e:
        result["primary"] = {"status": "unhealthy", "error": str(e)}
        result["status"] = "unhealthy"

    if read_engine != engine:
        try:
            async with async_read_session_factory() as session:
                await session.execute(text("SELECT 1"))
                result["replica"] = {"status": "healthy"}
        except Exception as e:
            result["replica"] = {"status": "unhealthy", "error": str(e)}
    else:
        result["replica"] = {"status": "same_as_primary"}

    return result
