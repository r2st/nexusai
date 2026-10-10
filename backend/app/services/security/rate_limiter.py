"""Rate Limiting Service.

Provides:
- Sliding window rate limiting
- Token bucket rate limiting
- Per-user and per-tenant limits
- Configurable limits per endpoint/operation
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import structlog

logger = structlog.get_logger()


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""

    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit."""

    name: str
    max_requests: int
    window_seconds: int
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    burst_limit: int | None = None  # For token bucket
    refill_rate: float | None = None  # Tokens per second for token bucket

    def __post_init__(self):
        if self.strategy == RateLimitStrategy.TOKEN_BUCKET:
            if self.burst_limit is None:
                self.burst_limit = self.max_requests
            if self.refill_rate is None:
                self.refill_rate = self.max_requests / self.window_seconds


@dataclass
class RateLimitState:
    """Current state for a rate limit."""

    key: str
    config: RateLimitConfig
    request_times: list[float] = field(default_factory=list)
    tokens: float = 0
    last_refill: float = 0

    def __post_init__(self):
        if self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            self.tokens = self.config.burst_limit or self.config.max_requests
            self.last_refill = time.time()


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    remaining: int
    reset_after_seconds: float
    retry_after_seconds: float | None = None
    limit: int = 0

    def to_headers(self) -> dict[str, str]:
        """Convert to HTTP rate limit headers."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_after_seconds)),
        }
        if self.retry_after_seconds:
            headers["Retry-After"] = str(int(self.retry_after_seconds))
        return headers


# Default rate limits
DEFAULT_RATE_LIMITS: dict[str, RateLimitConfig] = {
    # LLM operations
    "llm_request": RateLimitConfig(
        name="llm_request",
        max_requests=100,
        window_seconds=3600,  # 100 per hour
    ),
    "llm_chat": RateLimitConfig(
        name="llm_chat",
        max_requests=60,
        window_seconds=60,  # 60 per minute
    ),

    # API operations
    "api_request": RateLimitConfig(
        name="api_request",
        max_requests=1000,
        window_seconds=60,  # 1000 per minute
    ),
    "api_write": RateLimitConfig(
        name="api_write",
        max_requests=100,
        window_seconds=60,  # 100 writes per minute
    ),

    # Agent operations
    "agent_execute": RateLimitConfig(
        name="agent_execute",
        max_requests=50,
        window_seconds=3600,  # 50 per hour
    ),
    "tool_execute": RateLimitConfig(
        name="tool_execute",
        max_requests=200,
        window_seconds=3600,  # 200 per hour
    ),

    # Auth operations
    "login_attempt": RateLimitConfig(
        name="login_attempt",
        max_requests=5,
        window_seconds=300,  # 5 per 5 minutes
    ),
    "password_reset": RateLimitConfig(
        name="password_reset",
        max_requests=3,
        window_seconds=3600,  # 3 per hour
    ),

    # DevLake operations
    "devlake_sync": RateLimitConfig(
        name="devlake_sync",
        max_requests=10,
        window_seconds=3600,  # 10 per hour
    ),
    "metrics_query": RateLimitConfig(
        name="metrics_query",
        max_requests=120,
        window_seconds=60,  # 120 per minute
    ),

    # Document operations
    "document_upload": RateLimitConfig(
        name="document_upload",
        max_requests=50,
        window_seconds=3600,  # 50 per hour
    ),
    "rag_query": RateLimitConfig(
        name="rag_query",
        max_requests=100,
        window_seconds=60,  # 100 per minute
    ),
}


class RateLimiter:
    """
    Rate limiting service with multiple strategies.

    Supports:
    - Sliding window (default)
    - Token bucket (for burst handling)
    - Fixed window (simple)
    """

    def __init__(self, redis_client=None):
        """
        Initialize rate limiter.

        Args:
            redis_client: Optional Redis client for distributed limiting
        """
        self.redis = redis_client
        self._configs = DEFAULT_RATE_LIMITS.copy()
        self._states: dict[str, RateLimitState] = {}
        self._lock = asyncio.Lock()

    def register_limit(self, config: RateLimitConfig) -> None:
        """Register a new rate limit configuration."""
        self._configs[config.name] = config
        logger.info(
            "Registered rate limit",
            name=config.name,
            max_requests=config.max_requests,
            window_seconds=config.window_seconds,
        )

    def _get_key(
        self,
        limit_name: str,
        identifier: str,
        tenant_id: str | None = None,
    ) -> str:
        """Generate rate limit key."""
        parts = ["ratelimit", limit_name]
        if tenant_id:
            parts.append(f"tenant:{tenant_id}")
        parts.append(f"id:{identifier}")
        return ":".join(parts)

    async def check(
        self,
        limit_name: str,
        identifier: str,
        tenant_id: str | None = None,
        cost: int = 1,
    ) -> RateLimitResult:
        """
        Check rate limit and consume quota if allowed.

        Args:
            limit_name: Name of the rate limit to check
            identifier: User ID, IP, or other identifier
            tenant_id: Optional tenant ID for tenant-scoped limits
            cost: Cost of this operation (default 1)

        Returns:
            RateLimitResult with allowed status and metadata
        """
        config = self._configs.get(limit_name)
        if config is None:
            logger.warning(f"Unknown rate limit: {limit_name}")
            return RateLimitResult(
                allowed=True,
                remaining=999999,
                reset_after_seconds=0,
                limit=999999,
            )

        key = self._get_key(limit_name, identifier, tenant_id)

        # Use Redis if available, otherwise in-memory
        if self.redis:
            return await self._check_redis(key, config, cost)
        else:
            return await self._check_memory(key, config, cost)

    async def _check_memory(
        self,
        key: str,
        config: RateLimitConfig,
        cost: int,
    ) -> RateLimitResult:
        """Check rate limit using in-memory storage."""
        async with self._lock:
            now = time.time()

            # Get or create state
            if key not in self._states:
                self._states[key] = RateLimitState(key=key, config=config)

            state = self._states[key]

            if config.strategy == RateLimitStrategy.SLIDING_WINDOW:
                return self._check_sliding_window(state, now, cost)
            elif config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                return self._check_token_bucket(state, now, cost)
            else:
                return self._check_fixed_window(state, now, cost)

    def _check_sliding_window(
        self,
        state: RateLimitState,
        now: float,
        cost: int,
    ) -> RateLimitResult:
        """Sliding window rate limit check."""
        config = state.config
        window_start = now - config.window_seconds

        # Remove old requests outside the window
        state.request_times = [
            t for t in state.request_times if t > window_start
        ]

        current_count = len(state.request_times)
        remaining = max(0, config.max_requests - current_count - cost)

        if current_count + cost > config.max_requests:
            # Rate limited
            oldest = state.request_times[0] if state.request_times else now
            retry_after = oldest + config.window_seconds - now

            logger.warning(
                "Rate limit exceeded",
                key=state.key,
                current=current_count,
                limit=config.max_requests,
            )

            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_after_seconds=config.window_seconds,
                retry_after_seconds=max(0, retry_after),
                limit=config.max_requests,
            )

        # Add request times
        for _ in range(cost):
            state.request_times.append(now)

        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            reset_after_seconds=config.window_seconds,
            limit=config.max_requests,
        )

    def _check_token_bucket(
        self,
        state: RateLimitState,
        now: float,
        cost: int,
    ) -> RateLimitResult:
        """Token bucket rate limit check."""
        config = state.config

        # Refill tokens
        time_passed = now - state.last_refill
        refill_rate = config.refill_rate if config.refill_rate else 1.0
        burst_limit = config.burst_limit if config.burst_limit else config.max_requests
        tokens_to_add = time_passed * refill_rate
        state.tokens = min(burst_limit, state.tokens + tokens_to_add)
        state.last_refill = now

        if state.tokens >= cost:
            # Consume tokens
            state.tokens -= cost
            return RateLimitResult(
                allowed=True,
                remaining=int(state.tokens),
                reset_after_seconds=config.window_seconds,
                limit=burst_limit,
            )

        # Not enough tokens
        tokens_needed = cost - state.tokens
        wait_time = tokens_needed / refill_rate

        return RateLimitResult(
            allowed=False,
            remaining=0,
            reset_after_seconds=config.window_seconds,
            retry_after_seconds=wait_time,
            limit=burst_limit,
        )

    def _check_fixed_window(
        self,
        state: RateLimitState,
        now: float,
        cost: int,
    ) -> RateLimitResult:
        """Fixed window rate limit check."""
        config = state.config

        # Calculate current window
        window_number = int(now / config.window_seconds)

        # Reset if new window
        if not hasattr(state, "_window_number") or state._window_number != window_number:
            state._window_number = window_number
            state.request_times = []

        current_count = len(state.request_times)

        if current_count + cost > config.max_requests:
            # Rate limited
            window_end = (window_number + 1) * config.window_seconds
            retry_after = window_end - now

            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_after_seconds=retry_after,
                retry_after_seconds=retry_after,
                limit=config.max_requests,
            )

        # Add requests
        for _ in range(cost):
            state.request_times.append(now)

        return RateLimitResult(
            allowed=True,
            remaining=config.max_requests - current_count - cost,
            reset_after_seconds=((window_number + 1) * config.window_seconds) - now,
            limit=config.max_requests,
        )

    async def _check_redis(
        self,
        key: str,
        config: RateLimitConfig,
        cost: int,
    ) -> RateLimitResult:
        """Check rate limit using Redis (for distributed systems)."""
        # Simplified Redis implementation using INCR
        try:
            now = time.time()
            window_key = f"{key}:{int(now / config.window_seconds)}"

            # Increment counter
            count = await self.redis.incr(window_key)

            # Set expiry on first request
            if count == 1:
                await self.redis.expire(window_key, config.window_seconds + 1)

            if count > config.max_requests:
                ttl = await self.redis.ttl(window_key)
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_after_seconds=ttl,
                    retry_after_seconds=ttl,
                    limit=config.max_requests,
                )

            return RateLimitResult(
                allowed=True,
                remaining=config.max_requests - count,
                reset_after_seconds=await self.redis.ttl(window_key),
                limit=config.max_requests,
            )

        except Exception as e:
            logger.error("Redis rate limit check failed", error=str(e))
            # Fail open (allow) on Redis errors
            return RateLimitResult(
                allowed=True,
                remaining=config.max_requests,
                reset_after_seconds=config.window_seconds,
                limit=config.max_requests,
            )

    async def reset(
        self,
        limit_name: str,
        identifier: str,
        tenant_id: str | None = None,
    ) -> None:
        """Reset rate limit for an identifier."""
        key = self._get_key(limit_name, identifier, tenant_id)

        if self.redis:
            # Delete all keys matching pattern
            pattern = f"{key}:*"
            async for k in self.redis.scan_iter(pattern):
                await self.redis.delete(k)
        else:
            async with self._lock:
                if key in self._states:
                    del self._states[key]

        logger.info("Rate limit reset", key=key)

    async def get_status(
        self,
        limit_name: str,
        identifier: str,
        tenant_id: str | None = None,
    ) -> RateLimitResult:
        """Get current rate limit status without consuming quota."""
        # Check with cost of 0
        result = await self.check(limit_name, identifier, tenant_id, cost=0)
        return result

    def cleanup_expired(self) -> int:
        """Clean up expired rate limit states."""
        now = time.time()
        cleaned = 0

        keys_to_remove = []
        for key, state in self._states.items():
            # Remove states with no recent activity
            if state.request_times:
                latest = max(state.request_times)
                if now - latest > state.config.window_seconds * 2:
                    keys_to_remove.append(key)
                    cleaned += 1

        for key in keys_to_remove:
            del self._states[key]

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} expired rate limit states")

        return cleaned


# Singleton instance
rate_limiter = RateLimiter()
