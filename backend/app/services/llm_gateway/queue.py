"""LLM Request Queue with rate limiting and priority handling.

Provides:
- Async request queue with configurable concurrency
- Priority-based scheduling (premium users, critical requests)
- Rate limiting per user/tenant/provider
- Request deduplication
- Timeout handling
- Retry with exponential backoff
"""

import asyncio
import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Coroutine
from uuid import UUID, uuid4

import structlog

from app.services.llm_gateway.models import LLMRequest, LLMResponse

logger = structlog.get_logger()


class RequestPriority(int, Enum):
    """Request priority levels."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class RequestStatus(str, Enum):
    """Request status in the queue."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    RATE_LIMITED = "rate_limited"


@dataclass
class QueuedRequest:
    """A request in the queue."""

    id: UUID
    request: LLMRequest
    priority: RequestPriority
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: RequestStatus = RequestStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    timeout_seconds: float = 60.0
    result: LLMResponse | None = None
    error: str | None = None
    future: asyncio.Future | None = field(default=None, repr=False)

    def __lt__(self, other: "QueuedRequest") -> bool:
        """Priority comparison for heap queue."""
        if self.priority != other.priority:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at

    @property
    def request_hash(self) -> str:
        """Generate hash for deduplication."""
        content = f"{self.request.model}:{self.request.provider}:"
        for msg in self.request.messages:
            content += f"{msg.role}:{msg.content}:"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    tokens_per_minute: int = 100000
    tokens_per_hour: int = 1000000
    burst_limit: int = 10  # Max concurrent requests


@dataclass
class RateLimitState:
    """Track rate limit state for an entity."""

    minute_requests: list[datetime] = field(default_factory=list)
    hour_requests: list[datetime] = field(default_factory=list)
    minute_tokens: list[tuple[datetime, int]] = field(default_factory=list)
    hour_tokens: list[tuple[datetime, int]] = field(default_factory=list)
    concurrent: int = 0

    def cleanup(self, now: datetime) -> None:
        """Remove expired entries."""
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)

        self.minute_requests = [t for t in self.minute_requests if t > minute_ago]
        self.hour_requests = [t for t in self.hour_requests if t > hour_ago]
        self.minute_tokens = [(t, n) for t, n in self.minute_tokens if t > minute_ago]
        self.hour_tokens = [(t, n) for t, n in self.hour_tokens if t > hour_ago]


class RequestQueue:
    """
    Async request queue with rate limiting and priority handling.

    Features:
    - Priority-based scheduling
    - Per-user/tenant/provider rate limiting
    - Request deduplication
    - Timeout handling
    - Retry with exponential backoff
    - Concurrent request limiting
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        default_timeout: float = 60.0,
        max_queue_size: int = 1000,
        dedup_window_seconds: float = 5.0,
        rate_limit_config: RateLimitConfig | None = None,
    ):
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.max_queue_size = max_queue_size
        self.dedup_window_seconds = dedup_window_seconds
        self.rate_limit_config = rate_limit_config or RateLimitConfig()

        # Queue state
        self._queue: asyncio.PriorityQueue[QueuedRequest] = asyncio.PriorityQueue(
            maxsize=max_queue_size
        )
        self._processing: dict[UUID, QueuedRequest] = {}
        self._completed: dict[UUID, QueuedRequest] = {}
        self._recent_hashes: dict[str, tuple[datetime, UUID]] = {}

        # Rate limiting state
        self._user_limits: dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._tenant_limits: dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._provider_limits: dict[str, RateLimitState] = defaultdict(RateLimitState)

        # Worker state
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._process_callback: Callable[
            [LLMRequest], Coroutine[Any, Any, LLMResponse]
        ] | None = None

        # Metrics
        self._stats = {
            "total_enqueued": 0,
            "total_processed": 0,
            "total_failed": 0,
            "total_timeouts": 0,
            "total_rate_limited": 0,
            "total_deduplicated": 0,
        }

    async def start(
        self,
        process_callback: Callable[[LLMRequest], Coroutine[Any, Any, LLMResponse]],
        num_workers: int | None = None,
    ) -> None:
        """Start the queue workers."""
        if self._running:
            return

        self._process_callback = process_callback
        self._running = True

        num_workers = num_workers or self.max_concurrent
        for i in range(num_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

        logger.info("Request queue started", workers=num_workers)

    async def stop(self) -> None:
        """Stop the queue workers gracefully."""
        self._running = False

        # Wait for workers to finish current requests
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
            self._workers.clear()

        logger.info("Request queue stopped")

    async def enqueue(
        self,
        request: LLMRequest,
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout: float | None = None,
        max_attempts: int = 3,
        deduplicate: bool = True,
    ) -> asyncio.Future[LLMResponse]:
        """
        Add a request to the queue.

        Args:
            request: The LLM request
            priority: Request priority
            timeout: Request timeout in seconds
            max_attempts: Maximum retry attempts
            deduplicate: Whether to deduplicate similar requests

        Returns:
            Future that resolves to the response
        """
        # Check queue capacity
        if self._queue.full():
            raise Exception("Queue is full")

        # Check rate limits
        rate_check = self._check_rate_limits(request)
        if not rate_check["allowed"]:
            raise Exception(f"Rate limited: {rate_check['reason']}")

        # Create queued request
        queued = QueuedRequest(
            id=request.request_id,
            request=request,
            priority=priority,
            created_at=datetime.utcnow(),
            timeout_seconds=timeout or self.default_timeout,
            max_attempts=max_attempts,
            future=asyncio.get_event_loop().create_future(),
        )

        # Check for deduplication
        if deduplicate:
            dedup_result = self._check_dedup(queued)
            if dedup_result:
                self._stats["total_deduplicated"] += 1
                logger.debug(
                    "Request deduplicated",
                    request_id=str(request.request_id),
                    original_id=str(dedup_result),
                )
                # Return the future from the original request
                if dedup_result in self._processing:
                    return self._processing[dedup_result].future
                elif dedup_result in self._completed:
                    future = asyncio.get_event_loop().create_future()
                    completed = self._completed[dedup_result]
                    if completed.result:
                        future.set_result(completed.result)
                    else:
                        future.set_exception(Exception(completed.error or "Unknown error"))
                    return future

        # Record for deduplication
        self._recent_hashes[queued.request_hash] = (queued.created_at, queued.id)

        # Add to queue
        await self._queue.put(queued)
        self._stats["total_enqueued"] += 1

        logger.debug(
            "Request enqueued",
            request_id=str(request.request_id),
            priority=priority.name,
            queue_size=self._queue.qsize(),
        )

        return queued.future

    def _check_rate_limits(self, request: LLMRequest) -> dict[str, Any]:
        """Check if request is within rate limits."""
        now = datetime.utcnow()
        config = self.rate_limit_config

        # Check user limits
        if request.user_id:
            state = self._user_limits[request.user_id]
            state.cleanup(now)

            if len(state.minute_requests) >= config.requests_per_minute:
                return {"allowed": False, "reason": "User rate limit exceeded (per minute)"}

            if len(state.hour_requests) >= config.requests_per_hour:
                return {"allowed": False, "reason": "User rate limit exceeded (per hour)"}

            if state.concurrent >= config.burst_limit:
                return {"allowed": False, "reason": "User concurrent limit exceeded"}

        # Check tenant limits (higher limits)
        if request.tenant_id:
            state = self._tenant_limits[request.tenant_id]
            state.cleanup(now)

            tenant_rpm = config.requests_per_minute * 10  # 10x for tenants
            if len(state.minute_requests) >= tenant_rpm:
                return {"allowed": False, "reason": "Tenant rate limit exceeded"}

        # Check provider limits
        if request.provider:
            state = self._provider_limits[request.provider]
            state.cleanup(now)

            provider_rpm = config.requests_per_minute * 5  # Per provider limit
            if len(state.minute_requests) >= provider_rpm:
                return {"allowed": False, "reason": "Provider rate limit exceeded"}

        return {"allowed": True}

    def _record_rate_limit(self, request: LLMRequest, tokens: int = 0) -> None:
        """Record a request for rate limiting."""
        now = datetime.utcnow()

        if request.user_id:
            state = self._user_limits[request.user_id]
            state.minute_requests.append(now)
            state.hour_requests.append(now)
            if tokens:
                state.minute_tokens.append((now, tokens))
                state.hour_tokens.append((now, tokens))

        if request.tenant_id:
            state = self._tenant_limits[request.tenant_id]
            state.minute_requests.append(now)
            state.hour_requests.append(now)

        if request.provider:
            state = self._provider_limits[request.provider]
            state.minute_requests.append(now)
            state.hour_requests.append(now)

    def _check_dedup(self, queued: QueuedRequest) -> UUID | None:
        """Check if a similar request was recently made."""
        now = datetime.utcnow()
        window = timedelta(seconds=self.dedup_window_seconds)

        # Clean old entries
        expired = [
            h for h, (t, _) in self._recent_hashes.items() if now - t > window
        ]
        for h in expired:
            del self._recent_hashes[h]

        # Check for match
        if queued.request_hash in self._recent_hashes:
            _, original_id = self._recent_hashes[queued.request_hash]
            return original_id

        return None

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes requests."""
        logger.debug("Worker started", worker_id=worker_id)

        while self._running:
            try:
                # Get next request with timeout
                try:
                    queued = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue

                # Track processing
                self._processing[queued.id] = queued
                queued.status = RequestStatus.PROCESSING
                queued.started_at = datetime.utcnow()
                queued.attempts += 1

                # Update concurrent count
                if queued.request.user_id:
                    self._user_limits[queued.request.user_id].concurrent += 1

                try:
                    # Process with timeout
                    response = await asyncio.wait_for(
                        self._process_callback(queued.request),
                        timeout=queued.timeout_seconds,
                    )

                    # Success
                    queued.status = RequestStatus.COMPLETED
                    queued.result = response
                    queued.completed_at = datetime.utcnow()
                    self._stats["total_processed"] += 1

                    # Record for rate limiting
                    tokens = (
                        response.usage.total_tokens if response.usage else 0
                    )
                    self._record_rate_limit(queued.request, tokens)

                    # Resolve future
                    if queued.future and not queued.future.done():
                        queued.future.set_result(response)

                except asyncio.TimeoutError:
                    queued.status = RequestStatus.TIMEOUT
                    queued.error = "Request timed out"
                    self._stats["total_timeouts"] += 1

                    if queued.future and not queued.future.done():
                        queued.future.set_exception(
                            Exception(f"Request timed out after {queued.timeout_seconds}s")
                        )

                except Exception as e:
                    logger.warning(
                        "Request failed",
                        request_id=str(queued.id),
                        attempt=queued.attempts,
                        error=str(e),
                    )

                    # Retry if attempts remaining
                    if queued.attempts < queued.max_attempts:
                        # Exponential backoff
                        delay = 2 ** queued.attempts
                        await asyncio.sleep(delay)

                        # Re-queue
                        queued.status = RequestStatus.PENDING
                        await self._queue.put(queued)
                    else:
                        queued.status = RequestStatus.FAILED
                        queued.error = str(e)
                        self._stats["total_failed"] += 1

                        if queued.future and not queued.future.done():
                            queued.future.set_exception(e)

                finally:
                    # Update concurrent count
                    if queued.request.user_id:
                        self._user_limits[queued.request.user_id].concurrent -= 1

                    # Move from processing to completed
                    if queued.id in self._processing:
                        del self._processing[queued.id]

                    if queued.status in (
                        RequestStatus.COMPLETED,
                        RequestStatus.FAILED,
                        RequestStatus.TIMEOUT,
                    ):
                        self._completed[queued.id] = queued

                    self._queue.task_done()

            except Exception as e:
                logger.error("Worker error", worker_id=worker_id, error=str(e))
                await asyncio.sleep(1)

        logger.debug("Worker stopped", worker_id=worker_id)

    async def cancel(self, request_id: UUID) -> bool:
        """Cancel a pending or processing request."""
        if request_id in self._processing:
            queued = self._processing.pop(request_id)
            queued.status = RequestStatus.CANCELLED
            queued.completed_at = datetime.utcnow()
            self._completed[request_id] = queued
            if queued.future and not queued.future.done():
                queued.future.cancel()
            if queued.request.user_id:
                self._user_limits[queued.request.user_id].concurrent -= 1
            return True

        return False

    def get_status(self, request_id: UUID) -> dict[str, Any] | None:
        """Get status of a request."""
        if request_id in self._processing:
            queued = self._processing[request_id]
            return {
                "id": str(queued.id),
                "status": queued.status.value,
                "attempts": queued.attempts,
                "created_at": queued.created_at.isoformat(),
                "started_at": queued.started_at.isoformat() if queued.started_at else None,
            }

        if request_id in self._completed:
            queued = self._completed[request_id]
            return {
                "id": str(queued.id),
                "status": queued.status.value,
                "attempts": queued.attempts,
                "created_at": queued.created_at.isoformat(),
                "started_at": queued.started_at.isoformat() if queued.started_at else None,
                "completed_at": queued.completed_at.isoformat() if queued.completed_at else None,
                "error": queued.error,
            }

        return None

    def get_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        return {
            **self._stats,
            "queue_size": self._queue.qsize(),
            "processing": len(self._processing),
            "completed": len(self._completed),
            "workers_running": len([w for w in self._workers if not w.done()]),
        }

    def get_rate_limit_status(self, user_id: str) -> dict[str, Any]:
        """Get rate limit status for a user."""
        now = datetime.utcnow()
        config = self.rate_limit_config
        state = self._user_limits.get(user_id, RateLimitState())
        state.cleanup(now)

        minute_requests = len(state.minute_requests)
        hour_requests = len(state.hour_requests)

        return {
            "user_id": user_id,
            "requests_per_minute": {
                "used": minute_requests,
                "limit": config.requests_per_minute,
                "remaining": max(0, config.requests_per_minute - minute_requests),
            },
            "requests_per_hour": {
                "used": hour_requests,
                "limit": config.requests_per_hour,
                "remaining": max(0, config.requests_per_hour - hour_requests),
            },
            "concurrent": {
                "current": state.concurrent,
                "limit": config.burst_limit,
            },
        }


# Global queue instance
_request_queue: RequestQueue | None = None


def get_request_queue() -> RequestQueue:
    """Get the global request queue instance."""
    global _request_queue
    if _request_queue is None:
        _request_queue = RequestQueue()
    return _request_queue
