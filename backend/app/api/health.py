"""Health check and metrics endpoints."""

import time
from typing import Any

from fastapi import APIRouter, Response
from pydantic import BaseModel
import structlog

from app.core.config import settings
from app.services.guardrails.nemo import get_nemo_guardrails_adapter

logger = structlog.get_logger()


def _timed_check(result: dict, start: float) -> dict:
    result["response_time_ms"] = round((time.perf_counter() - start) * 1000, 2)
    return result

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
    t0 = time.perf_counter()
    try:
        from app.core.database import check_db_health
        db_health = await check_db_health()
        checks["database"] = _timed_check(db_health, t0)
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        checks["database"] = _timed_check({"status": "unhealthy", "error": "Database connection failed"}, t0)

    # Redis check
    t0 = time.perf_counter()
    try:
        from app.core.cache import cache
        redis_health = await cache.health_check()
        checks["redis"] = _timed_check(redis_health, t0)
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        checks["redis"] = _timed_check({"status": "unhealthy", "error": "Cache service connection failed"}, t0)

    # Guardrails / NeMo status
    try:
        guardrails_status = "disabled"
        nemo_status = "disabled"

        if settings.GUARDRAILS_ENABLED:
            guardrails_status = "enabled"

        if settings.NEMO_GUARDRAILS_ENABLED:
            if not settings.NEMO_GUARDRAILS_CONFIG_PATH:
                nemo_status = "misconfigured"
                guardrails_status = "degraded"
            else:
                adapter = get_nemo_guardrails_adapter()
                if adapter is None:
                    nemo_status = "unavailable"
                    guardrails_status = "degraded"
                elif adapter.is_ready:
                    nemo_status = "ready"
                else:
                    nemo_status = "not_initialized"

        checks["guardrails"] = {
            "status": "healthy" if guardrails_status in {"enabled", "disabled"} else "degraded",
            "guardrails_enabled": settings.GUARDRAILS_ENABLED,
            "nemo_enabled": settings.NEMO_GUARDRAILS_ENABLED,
            "nemo_config_path_set": bool(settings.NEMO_GUARDRAILS_CONFIG_PATH),
            "nemo_status": nemo_status,
        }
    except Exception as e:
        logger.error("Guardrails health check failed", error=str(e))
        checks["guardrails"] = {"status": "degraded", "error": "Guardrails check failed"}

    # Langfuse observability check
    try:
        from app.services.observability.service import _observability_service
        if _observability_service and _observability_service.langfuse._enabled:
            connected = _observability_service.langfuse._client is not None
            checks["langfuse"] = {
                "status": "healthy" if connected else "degraded",
                "connected": connected,
            }
        else:
            checks["langfuse"] = {"status": "disabled"}
    except Exception as e:
        logger.error("Langfuse health check failed", error=str(e))
        checks["langfuse"] = {"status": "degraded", "error": "Langfuse check failed"}

    # LLM provider availability
    try:
        providers_configured = []
        if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"):
            providers_configured.append("openai")
        if settings.ANTHROPIC_API_KEY:
            providers_configured.append("anthropic")
        if getattr(settings, "GOOGLE_API_KEY", None):
            providers_configured.append("google")

        checks["llm_providers"] = {
            "status": "healthy" if providers_configured else "degraded",
            "configured": providers_configured,
            "count": len(providers_configured),
        }
    except Exception as e:
        logger.error("LLM provider health check failed", error=str(e))
        checks["llm_providers"] = {"status": "unknown", "error": "Check failed"}

    # Determine overall status
    all_healthy = all(
        c.get("status") in {"healthy", "disabled"} for c in checks.values()
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

    # Check guardrails configuration readiness
    if settings.GUARDRAILS_ENABLED and settings.NEMO_GUARDRAILS_ENABLED:
        checks["guardrails"] = bool(settings.NEMO_GUARDRAILS_CONFIG_PATH)
    else:
        checks["guardrails"] = True

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
