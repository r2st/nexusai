"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
import structlog

from app.api import api_router
from app.core.cache import cache
from app.core.config import settings
from app.core.database import close_db, init_db

# Optional: Neo4j Knowledge Graph
neo4j_client = None
if settings.NEO4J_ENABLED:
    if not settings.NEO4J_PASSWORD:
        raise ValueError("NEO4J_PASSWORD is required when NEO4J_ENABLED=True")
    try:
        from app.services.knowledge_graph import Neo4jClient
        neo4j_client = Neo4jClient(
            uri=settings.NEO4J_URI,
            username=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD,
            database=settings.NEO4J_DATABASE,
        )
    except ImportError:
        pass

_SENSITIVE_KEYS = frozenset({
    "password", "hashed_password", "secret", "secret_key", "api_key",
    "token", "access_token", "refresh_token", "authorization",
    "openai_api_key", "anthropic_api_key", "private_key",
    "client_secret", "cookie", "session_token", "csrf_token",
    "google_api_key", "stripe_secret_key", "webhook_secret",
})


def _redact_sensitive_fields(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: dict,
) -> dict:
    for key in event_dict:
        if key.lower() in _SENSITIVE_KEYS and isinstance(event_dict[key], str):
            event_dict[key] = "[REDACTED]"
    return event_dict


# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        _redact_sensitive_fields,
        structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def seed_dev_users_on_startup() -> None:
    """Seed development users if in dev mode.

    Creates default test users automatically when running in development:
    - admin@nexusai.dev (admin123) - Admin user with superuser privileges
    - user@nexusai.dev (user123) - Regular user
    - viewer@nexusai.dev (viewer123) - Viewer user
    """
    if not settings.is_development:
        return

    try:
        from sqlalchemy import select
        from app.core.database import async_session_factory
        from app.core.security import get_password_hash
        from app.models.user import User, UserRole

        DEV_USERS = [
            {
                "email": "admin@nexusai.dev",
                "username": "admin",
                "password": "admin123",
                "full_name": "Admin User",
                "role": UserRole.ADMIN.value,
                "is_verified": True,
                "is_active": True,
                "is_superuser": True,
            },
            {
                "email": "user@nexusai.dev",
                "username": "devuser",
                "password": "user123",
                "full_name": "Dev User",
                "role": UserRole.USER.value,
                "is_verified": True,
                "is_active": True,
                "is_superuser": False,
            },
            {
                "email": "viewer@nexusai.dev",
                "username": "viewer",
                "password": "viewer123",
                "full_name": "Viewer User",
                "role": UserRole.VIEWER.value,
                "is_verified": True,
                "is_active": True,
                "is_superuser": False,
            },
        ]

        async with async_session_factory() as session:
            created_count = 0
            existing_users = []
            created_users = []

            for user_data in DEV_USERS:
                result = await session.execute(
                    select(User).where(User.email == user_data["email"])
                )
                if result.scalar_one_or_none():
                    existing_users.append(user_data.copy())
                    continue

                password = user_data.pop("password")
                user = User(
                    **user_data,
                    hashed_password=get_password_hash(password),
                )
                session.add(user)
                created_users.append({**user_data, "password": password})
                created_count += 1

            await session.commit()

            logger.info(
                "Development users ready",
                created=created_count,
                existing=len(existing_users),
                accounts="admin@nexusai.dev | user@nexusai.dev | viewer@nexusai.dev",
            )

    except Exception as e:
        logger.warning("Failed to seed dev users", error=str(e))


async def seed_langfuse_prompts() -> None:
    """Seed default prompts to Langfuse on startup.

    Creates the ``nexusai-system-prompt`` in Langfuse if it doesn't
    already exist, so it appears in the Langfuse dashboard for editing.
    Gracefully skips if Langfuse is not configured.
    """
    try:
        from app.services.prompts.langfuse_manager import get_langfuse_prompt_manager
        from app.services.chat import NEXUSAI_SYSTEM_PROMPT

        manager = await get_langfuse_prompt_manager()
        if not manager.enabled:
            logger.debug("Langfuse prompts seeding skipped (not configured)")
            return

        result = await manager.sync_from_local(
            name="nexusai-system-prompt",
            template=NEXUSAI_SYSTEM_PROMPT,
            labels=["production"],
            tags=["system", "default"],
            commit_message="Default NexusAI system prompt",
        )
        if result:
            logger.info(
                "Langfuse prompt seeded",
                name="nexusai-system-prompt",
                version=result.version if hasattr(result, "version") else "unknown",
            )
    except Exception as e:
        logger.debug("Langfuse prompt seeding skipped", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting application", version=settings.APP_VERSION)
    await init_db()
    logger.info("Database initialized")

    await cache.initialize()
    logger.info("Redis cache initialized")

    # Seed development users
    await seed_dev_users_on_startup()

    # Seed default prompts to Langfuse
    await seed_langfuse_prompts()

    # Initialize Neo4j if enabled
    if neo4j_client and settings.NEO4J_ENABLED:
        try:
            await neo4j_client.connect()
            logger.info("Neo4j Knowledge Graph connected")
            app.state.neo4j = neo4j_client
        except Exception as e:
            logger.warning("Neo4j connection failed", error=str(e))
            app.state.neo4j = None
    else:
        app.state.neo4j = None

    # Store feature flags in app state for easy access
    app.state.features = {
        "knowledge_graph": settings.FEATURE_KNOWLEDGE_GRAPH and app.state.neo4j is not None,
        "devops_agents": settings.FEATURE_DEVOPS_AGENTS,
        "openapi_actions": settings.FEATURE_OPENAPI_ACTIONS,
        "code_interpreter": settings.FEATURE_CODE_INTERPRETER,
    }
    logger.info("Feature flags loaded", features=app.state.features)

    # Log observability configuration summary
    logger.info(
        "Observability configuration",
        log_format=settings.LOG_FORMAT,
        otel_enabled=settings.OTEL_ENABLED,
        multi_tenant=settings.MULTI_TENANT_ENABLED,
        environment=settings.ENVIRONMENT,
    )

    yield

    # Shutdown
    logger.info("Shutting down application")

    # Close Neo4j connection
    if neo4j_client:
        try:
            await neo4j_client.close()
            logger.info("Neo4j connection closed")
        except Exception as e:
            logger.warning("Error closing Neo4j", error=str(e))

    await cache.close()
    logger.info("Redis cache closed")

    await close_db()
    logger.info("Database connections closed")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Modern AI-powered chat and analytics platform",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # Import middleware
    from app.core.middleware import (
        TenantMiddleware,
        TenantRateLimitMiddleware,
        RequestIDMiddleware,
        ResponseTimeMiddleware,
        SecurityHeadersMiddleware,
        ErrorTrackingMiddleware,
    )

    # ==========================================================================
    # MIDDLEWARE ORDER IS IMPORTANT!
    # Middleware is executed in REVERSE order of registration (LIFO)
    # So the first registered middleware executes LAST on request, FIRST on response
    # ==========================================================================

    # Security headers (runs last on request, first on response)
    app.add_middleware(SecurityHeadersMiddleware)

    # Error tracking (catches unhandled exceptions)
    app.add_middleware(ErrorTrackingMiddleware)

    # Response time tracking
    app.add_middleware(ResponseTimeMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # Per-tenant rate limiting (after tenant context is set)
    if settings.MULTI_TENANT_ENABLED:
        app.add_middleware(
            TenantRateLimitMiddleware,
            requests_per_minute_per_tenant=settings.PER_TENANT_RATE_LIMIT,
            requests_per_minute_per_user=settings.RATE_LIMIT_PER_MINUTE,
        )

    # Tenant context extraction (runs early to set context)
    if settings.MULTI_TENANT_ENABLED:
        app.add_middleware(TenantMiddleware)

    # Request ID tracking (runs first on request)
    app.add_middleware(RequestIDMiddleware)

    # Include API routes
    app.include_router(api_router, prefix=settings.API_PREFIX)

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
        }

    # Health check endpoints at root level (for Docker/Traefik healthchecks)
    @app.get("/health")
    @app.get("/healthz")
    @app.get("/api/health")
    @app.get("/api/healthz")
    async def health():
        """Health check for Docker and load balancers.

        Verifies DB connectivity with a lightweight query.
        """
        from sqlalchemy import text
        from app.core.database import async_session_factory

        db_ok = True
        try:
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
        except Exception as e:
            db_ok = False
            logger.error("Health check DB probe failed", error=str(e))

        status = "healthy" if db_ok else "degraded"
        return ORJSONResponse(
            content={
                "status": status,
                "version": settings.APP_VERSION,
                "database": "ok" if db_ok else "unreachable",
            },
            status_code=200 if db_ok else 503,
        )

    # Features endpoint
    @app.get("/features")
    async def get_features():
        """Get available features and their status."""
        return {
            "features": getattr(app.state, "features", {}),
            "agents_enabled": settings.AGENTS_ENABLED,
            "neo4j_enabled": settings.NEO4J_ENABLED,
            "devops_enabled": settings.FEATURE_DEVOPS_AGENTS,
        }

    # Observability status endpoint
    @app.get("/observability/status")
    async def observability_status():
        """Get observability services status (Langfuse, Prometheus)."""
        status = {
            "langfuse": {"enabled": False, "connected": False},
            "prometheus": {"enabled": False},
            "devlake": {"enabled": settings.DEVLAKE_ENABLED, "url": settings.DEVLAKE_API_URL},
        }

        try:
            from app.services.observability.service import _observability_service
            if _observability_service:
                status["langfuse"]["enabled"] = _observability_service.langfuse._enabled
                status["langfuse"]["connected"] = _observability_service.langfuse._client is not None
                status["prometheus"]["enabled"] = _observability_service.metrics._enabled
                status["metrics"] = _observability_service.langfuse.get_metrics()
        except Exception as e:
            status["error"] = str(e)

        return status

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=1 if settings.RELOAD else settings.WORKERS,
    )
