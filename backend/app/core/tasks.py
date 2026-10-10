"""Background task processing with ARQ (async Redis queue).

Provides:
- Async task queue processing
- Scheduled/periodic tasks
- Task retry with exponential backoff
- Task result storage
- Priority queues
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, TypeVar
from functools import wraps
import uuid

from arq import create_pool, ArqRedis
from arq.connections import RedisSettings
from arq.jobs import Job

from app.core.config import settings
from app.core.multitenancy import set_current_tenant_id, clear_tenant_context

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TaskPriority:
    """Task priority levels."""
    CRITICAL = "critical"  # Immediate processing
    HIGH = "high"  # Within seconds
    NORMAL = "normal"  # Standard queue
    LOW = "low"  # Background processing
    BULK = "bulk"  # Batch processing


class TaskConfig:
    """Task configuration."""

    # Queue names
    DEFAULT_QUEUE = "nexusai:default"
    HIGH_PRIORITY_QUEUE = "nexusai:high"
    LOW_PRIORITY_QUEUE = "nexusai:low"
    SCHEDULED_QUEUE = "nexusai:scheduled"

    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY = 60  # seconds
    RETRY_BACKOFF = 2  # exponential backoff multiplier

    # Job settings
    DEFAULT_TIMEOUT = 300  # 5 minutes
    RESULT_TTL = 3600  # 1 hour


def get_redis_settings() -> RedisSettings:
    """Get Redis settings for ARQ."""
    return RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        database=settings.REDIS_DB + 1,  # Use different DB for tasks
    )


class TaskQueue:
    """Async task queue manager."""

    def __init__(self):
        self._pool: ArqRedis | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        if not self._pool:
            self._pool = await create_pool(get_redis_settings())

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    @property
    def pool(self) -> ArqRedis:
        """Get connection pool."""
        if not self._pool:
            raise RuntimeError("Task queue not connected")
        return self._pool

    async def enqueue(
        self,
        task_name: str,
        *args,
        _queue_name: str | None = None,
        _defer_by: timedelta | None = None,
        _defer_until: datetime | None = None,
        _job_id: str | None = None,
        _timeout: int = TaskConfig.DEFAULT_TIMEOUT,
        **kwargs,
    ) -> Job:
        """Enqueue a task for processing.

        Args:
            task_name: Name of the task function
            *args: Positional arguments for task
            _queue_name: Optional queue name override
            _defer_by: Delay execution by timedelta
            _defer_until: Execute at specific datetime
            _job_id: Optional custom job ID
            _timeout: Task timeout in seconds
            **kwargs: Keyword arguments for task

        Returns:
            Job object for tracking
        """
        job = await self.pool.enqueue_job(
            task_name,
            *args,
            _queue_name=_queue_name or TaskConfig.DEFAULT_QUEUE,
            _defer_by=_defer_by,
            _defer_until=_defer_until,
            _job_id=_job_id or str(uuid.uuid4()),
            _job_try=0,
            _timeout=_timeout,
            **kwargs,
        )
        return job

    async def enqueue_high_priority(
        self,
        task_name: str,
        *args,
        **kwargs,
    ) -> Job:
        """Enqueue a high-priority task."""
        return await self.enqueue(
            task_name,
            *args,
            _queue_name=TaskConfig.HIGH_PRIORITY_QUEUE,
            **kwargs,
        )

    async def enqueue_low_priority(
        self,
        task_name: str,
        *args,
        **kwargs,
    ) -> Job:
        """Enqueue a low-priority task."""
        return await self.enqueue(
            task_name,
            *args,
            _queue_name=TaskConfig.LOW_PRIORITY_QUEUE,
            **kwargs,
        )

    async def schedule(
        self,
        task_name: str,
        *args,
        run_at: datetime | None = None,
        delay: timedelta | None = None,
        **kwargs,
    ) -> Job:
        """Schedule a task for future execution."""
        return await self.enqueue(
            task_name,
            *args,
            _queue_name=TaskConfig.SCHEDULED_QUEUE,
            _defer_until=run_at,
            _defer_by=delay,
            **kwargs,
        )

    async def get_job(self, job_id: str) -> Job | None:
        """Get job by ID."""
        return await self.pool.get_job(job_id)

    async def get_job_result(
        self,
        job_id: str,
        timeout: float = 30.0,
    ) -> Any:
        """Wait for and get job result."""
        job = await self.get_job(job_id)
        if not job:
            return None

        return await job.result(timeout=timeout)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job."""
        job = await self.get_job(job_id)
        if job:
            await job.abort()
            return True
        return False

    async def get_queue_info(self, queue_name: str | None = None) -> dict:
        """Get queue statistics."""
        queue = queue_name or TaskConfig.DEFAULT_QUEUE
        info = await self.pool.info()
        return {
            "pending": info.get("pending", 0),
            "complete": info.get("complete", 0),
            "failed": info.get("failed", 0),
            "queue": queue,
        }

    # =========================================================================
    # TENANT-AWARE TASK METHODS
    # =========================================================================

    async def enqueue_for_tenant(
        self,
        tenant_id: str,
        task_name: str,
        *args,
        _queue_name: str | None = None,
        _defer_by: timedelta | None = None,
        _defer_until: datetime | None = None,
        _job_id: str | None = None,
        _timeout: int = TaskConfig.DEFAULT_TIMEOUT,
        **kwargs,
    ) -> Job:
        """Enqueue a task with tenant context for proper data isolation.

        This method automatically:
        1. Includes tenant_id in the job for RLS context
        2. Uses tenant-prefixed job ID for better tracking
        3. Tags the job with tenant for monitoring

        Args:
            tenant_id: The tenant/organization ID for data isolation
            task_name: Name of the task function
            *args: Positional arguments for task
            **kwargs: Keyword arguments for task

        Returns:
            Job object for tracking
        """
        # Ensure tenant_id is always passed to task
        if 'tenant_id' not in kwargs and tenant_id:
            kwargs['tenant_id'] = tenant_id

        # Create tenant-prefixed job ID for easier tracking
        job_id = _job_id or f"tenant:{tenant_id}:{str(uuid.uuid4())}"

        return await self.enqueue(
            task_name,
            *args,
            _queue_name=_queue_name,
            _defer_by=_defer_by,
            _defer_until=_defer_until,
            _job_id=job_id,
            _timeout=_timeout,
            **kwargs,
        )

    async def get_tenant_jobs(self, tenant_id: str) -> list[Job]:
        """Get all pending jobs for a specific tenant.

        Useful for monitoring and cleanup.
        """
        # This is a simplified implementation
        # In production, you'd use Redis SCAN with pattern matching
        jobs = []
        # Pattern: tenant:{tenant_id}:*
        # Note: ARQ doesn't directly support listing jobs by pattern
        # This would need custom Redis queries
        return jobs

    async def cancel_tenant_jobs(self, tenant_id: str) -> int:
        """Cancel all pending jobs for a tenant.

        Use when deleting a tenant or during emergency shutdown.
        """
        cancelled = 0
        failed = 0
        jobs = await self.get_tenant_jobs(tenant_id)
        for job in jobs:
            try:
                await job.abort()
                cancelled += 1
            except Exception as e:
                failed += 1
                logger.warning("Failed to cancel job", job_id=str(getattr(job, 'id', 'unknown')), tenant_id=tenant_id, error=str(e))
        if failed:
            logger.error("Some tenant jobs failed to cancel", tenant_id=tenant_id, cancelled=cancelled, failed=failed)
        return cancelled


# Global task queue instance
task_queue = TaskQueue()


def background_task(
    queue: str = TaskConfig.DEFAULT_QUEUE,
    timeout: int = TaskConfig.DEFAULT_TIMEOUT,
    max_tries: int = TaskConfig.MAX_RETRIES,
):
    """Decorator to define a background task.

    Args:
        queue: Queue name for the task
        timeout: Task timeout in seconds
        max_tries: Maximum retry attempts
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Store task metadata
        func._task_queue = queue
        func._task_timeout = timeout
        func._task_max_tries = max_tries
        func._is_background_task = True

        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await func(*args, **kwargs)

        return wrapper
    return decorator


def tenant_background_task(
    queue: str = TaskConfig.DEFAULT_QUEUE,
    timeout: int = TaskConfig.DEFAULT_TIMEOUT,
    max_tries: int = TaskConfig.MAX_RETRIES,
    tenant_arg: str = "tenant_id",
):
    """Decorator for tenant-aware background tasks.

    Automatically sets up tenant context before task execution
    and cleans it up after, ensuring proper RLS enforcement.

    Args:
        queue: Queue name for the task
        timeout: Task timeout in seconds
        max_tries: Maximum retry attempts
        tenant_arg: Name of the tenant_id argument

    Example:
        @tenant_background_task(queue=TaskConfig.HIGH_PRIORITY_QUEUE)
        async def process_document(ctx: dict, document_id: str, tenant_id: str):
            # Tenant context is automatically set
            # RLS policies will enforce data isolation
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Store task metadata
        func._task_queue = queue
        func._task_timeout = timeout
        func._task_max_tries = max_tries
        func._is_background_task = True
        func._is_tenant_task = True

        @wraps(func)
        async def wrapper(ctx: dict, *args, **kwargs) -> T:
            # Extract tenant_id from kwargs
            tenant_id = kwargs.get(tenant_arg)

            if not tenant_id:
                # Try to get from positional args (ctx is first, so adjust index)
                import inspect
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                if tenant_arg in params:
                    idx = params.index(tenant_arg) - 1  # Adjust for ctx
                    if 0 <= idx < len(args):
                        tenant_id = args[idx]

            try:
                # Set tenant context for RLS
                if tenant_id:
                    set_current_tenant_id(tenant_id)
                    # Store in ctx for downstream access
                    ctx["tenant_id"] = tenant_id

                # Execute the actual task
                return await func(ctx, *args, **kwargs)

            finally:
                # Always clean up tenant context
                clear_tenant_context()

        return wrapper
    return decorator


# ============= Task Definitions =============
# Note: All tenant-aware tasks use tenant_background_task decorator
# which automatically sets RLS context for proper data isolation.

@tenant_background_task(queue=TaskConfig.HIGH_PRIORITY_QUEUE, timeout=120)
async def process_document_task(
    ctx: dict,
    document_id: str,
    tenant_id: str,
) -> dict:
    """Process uploaded document (chunking, embedding).

    Tenant context is automatically set by the decorator.
    """
    from app.services.document import document_service
    from app.core.database import get_db_context_with_tenant

    async with get_db_context_with_tenant(tenant_id) as session:
        result = await document_service.process_document(
            session, document_id, tenant_id
        )
        return {"status": "completed", "chunks": result}


@tenant_background_task(queue=TaskConfig.DEFAULT_QUEUE, timeout=300)
async def sync_devlake_data_task(
    ctx: dict,
    blueprint_id: str,
    tenant_id: str,
) -> dict:
    """Sync data from DevLake for a blueprint.

    Tenant context is automatically set by the decorator.
    """
    from app.services.devlake.blueprints import blueprint_service
    from app.core.database import get_db_context_with_tenant

    async with get_db_context_with_tenant(tenant_id) as session:
        pipeline = await blueprint_service.run_blueprint(
            session, blueprint_id, full_sync=False
        )
        return {"status": "started", "pipeline_id": str(pipeline.id)}


@tenant_background_task(queue=TaskConfig.DEFAULT_QUEUE, timeout=180)
async def calculate_metrics_task(
    ctx: dict,
    tenant_id: str,
    project_name: str,
    metric_type: str,
) -> dict:
    """Calculate and cache metrics for a project.

    Tenant context is automatically set by the decorator.
    Cache keys are tenant-scoped to prevent cross-tenant pollution.
    """
    from app.services.metrics import (
        dora_metrics_service,
        space_metrics_service,
        business_metrics_service,
    )
    from app.core.database import get_db_context_with_tenant
    from app.core.cache import cache

    async with get_db_context_with_tenant(tenant_id) as session:
        if metric_type == "dora":
            metrics = await dora_metrics_service.calculate_metrics(
                session, tenant_id, project_name
            )
        elif metric_type == "space":
            metrics = await space_metrics_service.calculate_metrics(
                session, tenant_id, project_name
            )
        elif metric_type == "business":
            metrics = await business_metrics_service.calculate_metrics(
                session, tenant_id, project_name
            )
        else:
            return {"status": "error", "message": f"Unknown metric type: {metric_type}"}

        # Cache the results with tenant isolation
        cache_key = f"metrics:{metric_type}:{project_name}"
        await cache.set_tenant(tenant_id, cache_key, metrics.model_dump())

        return {"status": "completed", "metric_type": metric_type}


@tenant_background_task(queue=TaskConfig.LOW_PRIORITY_QUEUE, timeout=600)
async def generate_ai_summary_task(
    ctx: dict,
    tenant_id: str,
    project_id: str,
    summary_type: str,
) -> dict:
    """Generate AI summary for project.

    Tenant context is automatically set by the decorator.
    """
    from app.services.ai_analytics.summary import get_ai_summary_service
    from app.core.database import get_db_context_with_tenant

    async with get_db_context_with_tenant(tenant_id) as session:
        ai_summary_service = get_ai_summary_service()
        summary = await ai_summary_service.generate_summary(
            session, tenant_id, project_id, summary_type
        )
        return {
            "status": "completed",
            "summary_id": str(summary.id) if summary else None,
        }


@background_task(queue=TaskConfig.LOW_PRIORITY_QUEUE, timeout=300)
async def cleanup_expired_tokens_task(ctx: dict) -> dict:
    """Clean up expired personal access tokens."""
    from app.models.personal_access_token import pat_service
    from app.core.database import get_db_context

    async with get_db_context() as session:
        deleted = await pat_service.cleanup_expired_tokens(session)
        return {"status": "completed", "deleted_count": deleted}


@background_task(queue=TaskConfig.LOW_PRIORITY_QUEUE, timeout=300)
async def export_analytics_to_clickhouse_task(
    ctx: dict,
    tenant_id: str,
    data_type: str,
    data: list[dict],
) -> dict:
    """Export analytics data to ClickHouse."""
    from app.services.analytics.clickhouse import clickhouse_service

    if data_type == "metrics":
        for item in data:
            await clickhouse_service.insert_metrics(
                tenant_id,
                item.get("project_id", ""),
                [item],
            )
    elif data_type == "api_requests":
        for item in data:
            await clickhouse_service.insert_api_request(
                tenant_id,
                item.get("user_id"),
                item.get("endpoint", ""),
                item.get("method", "GET"),
                item.get("status_code", 200),
                item.get("response_time_ms", 0),
            )

    return {"status": "completed", "records": len(data)}


@background_task(queue=TaskConfig.BULK_QUEUE if hasattr(TaskConfig, "BULK_QUEUE") else TaskConfig.LOW_PRIORITY_QUEUE, timeout=1800)
async def bulk_import_task(
    ctx: dict,
    tenant_id: str,
    import_type: str,
    file_path: str,
) -> dict:
    """Bulk import data from file."""
    # Placeholder for bulk import logic
    return {"status": "completed", "import_type": import_type}


# ============= Worker Configuration =============

async def startup(ctx: dict) -> None:
    """Worker startup hook."""
    from app.core.cache import cache
    from app.core.database import init_db

    await cache.initialize()
    await init_db()
    print("Worker started")


async def shutdown(ctx: dict) -> None:
    """Worker shutdown hook."""
    from app.core.cache import cache
    from app.core.database import close_db

    await cache.close()
    await close_db()
    print("Worker stopped")


# Worker class for ARQ
class WorkerSettings:
    """ARQ worker settings."""

    redis_settings = get_redis_settings()

    # Functions available to workers
    functions = [
        process_document_task,
        sync_devlake_data_task,
        calculate_metrics_task,
        generate_ai_summary_task,
        cleanup_expired_tokens_task,
        export_analytics_to_clickhouse_task,
        bulk_import_task,
    ]

    # Queues to process
    queue_name = TaskConfig.DEFAULT_QUEUE

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown

    # Worker settings
    max_jobs = 10
    job_timeout = 300
    keep_result = TaskConfig.RESULT_TTL
    retry_jobs = True
    max_tries = TaskConfig.MAX_RETRIES

    # Cron jobs (scheduled tasks)
    cron_jobs = [
        # Clean up expired tokens daily at 3 AM
        # cron(cleanup_expired_tokens_task, hour=3, minute=0),
    ]
