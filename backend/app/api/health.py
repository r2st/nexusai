"""Health check and metrics endpoints."""

import time
from typing import Any

from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()

# Simple in-memory metrics (for production, use prometheus_client library)
_metrics = {
    "requests_total": 0,
    "requests_success": 0,
    "requests_failed": 0,
    "startup_time": time.time(),
}


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    environment: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response with dependency status."""

    status: str
    version: str
    environment: str
    checks: dict[str, Any]


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check() -> DetailedHealthResponse:
    """Detailed health check with all dependencies."""
    checks: dict[str, Any] = {}

    # Database check
    try:
        from app.core.database import check_db_health
        db_health = await check_db_health()
        checks["database"] = db_health
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}

    # Redis check
    try:
        from app.core.cache import cache
        redis_health = await cache.health_check()
        checks["redis"] = redis_health
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}

    # Determine overall status
    all_healthy = all(
        c.get("status") == "healthy" for c in checks.values()
    )

    return DetailedHealthResponse(
        status="healthy" if all_healthy else "degraded",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        checks=checks,
    )


@router.get("/ready")
async def readiness_check() -> dict:
    """Readiness check for Kubernetes.

    Checks if the application can accept traffic.
    """
    checks = {}

    # Check database connection
    try:
        from app.core.database import check_db_health
        db_status = await check_db_health()
        checks["database"] = db_status.get("status") == "healthy"
    except Exception:
        checks["database"] = False

    # Check Redis connection
    try:
        from app.core.cache import cache
        redis_status = await cache.health_check()
        checks["redis"] = redis_status.get("status") == "healthy"
    except Exception:
        checks["redis"] = False

    is_ready = all(checks.values())

    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
    }


@router.get("/live")
async def liveness_check() -> dict:
    """Liveness check for Kubernetes.

    Simple check that the process is alive.
    """
    return {"status": "alive"}


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format.
    """
    uptime = time.time() - _metrics["startup_time"]

    # Collect metrics
    metrics_lines = [
        "# HELP nexusai_up Whether the service is up",
        "# TYPE nexusai_up gauge",
        "nexusai_up 1",
        "",
        "# HELP nexusai_info Application info",
        "# TYPE nexusai_info gauge",
        f'nexusai_info{{version="{settings.APP_VERSION}",environment="{settings.ENVIRONMENT}"}} 1',
        "",
        "# HELP nexusai_uptime_seconds Time since application started",
        "# TYPE nexusai_uptime_seconds gauge",
        f"nexusai_uptime_seconds {uptime:.2f}",
        "",
    ]

    # Database pool metrics (if available)
    try:
        from app.core.database import engine
        pool = engine.pool
        if hasattr(pool, "size"):
            metrics_lines.extend([
                "# HELP nexusai_db_pool_size Database connection pool size",
                "# TYPE nexusai_db_pool_size gauge",
                f"nexusai_db_pool_size {pool.size()}",
                "",
                "# HELP nexusai_db_pool_checkedin Checked-in connections",
                "# TYPE nexusai_db_pool_checkedin gauge",
                f"nexusai_db_pool_checkedin {pool.checkedin()}",
                "",
                "# HELP nexusai_db_pool_checkedout Checked-out connections",
                "# TYPE nexusai_db_pool_checkedout gauge",
                f"nexusai_db_pool_checkedout {pool.checkedout()}",
                "",
                "# HELP nexusai_db_pool_overflow Overflow connections",
                "# TYPE nexusai_db_pool_overflow gauge",
                f"nexusai_db_pool_overflow {pool.overflow()}",
                "",
            ])
    except Exception:
        pass

    # Redis metrics (if available)
    try:
        from app.core.cache import cache
        if cache._initialized:
            info = await cache.client.info("memory")
            metrics_lines.extend([
                "# HELP nexusai_redis_used_memory_bytes Redis memory usage",
                "# TYPE nexusai_redis_used_memory_bytes gauge",
                f"nexusai_redis_used_memory_bytes {info.get('used_memory', 0)}",
                "",
            ])
    except Exception:
        pass

    # Configuration metrics
    metrics_lines.extend([
        "# HELP nexusai_config_workers Configured worker count",
        "# TYPE nexusai_config_workers gauge",
        f"nexusai_config_workers {settings.WORKERS}",
        "",
        "# HELP nexusai_config_db_pool_size Configured DB pool size",
        "# TYPE nexusai_config_db_pool_size gauge",
        f"nexusai_config_db_pool_size {settings.DATABASE_POOL_SIZE}",
        "",
        "# HELP nexusai_config_rate_limit_per_tenant Per-tenant rate limit",
        "# TYPE nexusai_config_rate_limit_per_tenant gauge",
        f"nexusai_config_rate_limit_per_tenant {settings.PER_TENANT_RATE_LIMIT}",
        "",
    ])

    # Feature flags
    feature_flags = [
        ("ai_analytics", settings.FEATURE_AI_ANALYTICS),
        ("code_interpreter", settings.FEATURE_CODE_INTERPRETER),
        ("web_search", settings.FEATURE_WEB_SEARCH),
        ("devops_agents", settings.FEATURE_DEVOPS_AGENTS),
        ("knowledge_graph", settings.FEATURE_KNOWLEDGE_GRAPH),
        ("mcp_tools", settings.FEATURE_MCP_TOOLS),
    ]

    metrics_lines.append("# HELP nexusai_feature_enabled Feature flag status")
    metrics_lines.append("# TYPE nexusai_feature_enabled gauge")
    for feature, enabled in feature_flags:
        metrics_lines.append(
            f'nexusai_feature_enabled{{feature="{feature}"}} {1 if enabled else 0}'
        )
    metrics_lines.append("")

    return Response(
        content="\n".join(metrics_lines),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
