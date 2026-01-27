"""Redis caching layer for scalable performance.

Provides:
- Distributed caching with Redis
- Cache decorators for functions
- TTL-based expiration
- Cache invalidation patterns
- Serialization for complex objects
"""

import asyncio
import functools
import hashlib
import json
import pickle
from datetime import timedelta
from typing import Any, Callable, TypeVar, ParamSpec
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import settings

P = ParamSpec("P")
T = TypeVar("T")


class CacheConfig:
    """Cache configuration constants."""

    # Default TTLs
    SHORT_TTL = 60  # 1 minute
    MEDIUM_TTL = 300  # 5 minutes
    LONG_TTL = 3600  # 1 hour
    VERY_LONG_TTL = 86400  # 24 hours

    # Key prefixes
    PREFIX = "nexusai:"
    METRICS_PREFIX = f"{PREFIX}metrics:"
    SESSION_PREFIX = f"{PREFIX}session:"
    RATE_LIMIT_PREFIX = f"{PREFIX}ratelimit:"
    LOCK_PREFIX = f"{PREFIX}lock:"
    OAUTH_PREFIX = f"{PREFIX}oauth:"
    USER_PREFIX = f"{PREFIX}user:"
    TENANT_PREFIX = f"{PREFIX}tenant:"

    @staticmethod
    def tenant_key(tenant_id: str | None, key: str) -> str:
        """Generate a tenant-scoped cache key.

        Args:
            tenant_id: The tenant/organization ID (can be None for global keys)
            key: The base key

        Returns:
            Tenant-scoped key: nexusai:tenant:{tenant_id}:{key}
            Or global key if tenant_id is None: nexusai:{key}
        """
        if tenant_id:
            return f"{CacheConfig.TENANT_PREFIX}{tenant_id}:{key}"
        return f"{CacheConfig.PREFIX}{key}"


class RedisCache:
    """Redis cache client with connection pooling."""

    def __init__(self):
        self._pool: ConnectionPool | None = None
        self._client: redis.Redis | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Redis connection pool."""
        if self._initialized:
            return

        self._pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=100,
            decode_responses=False,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        self._client = redis.Redis(connection_pool=self._pool)
        self._initialized = True

    async def close(self) -> None:
        """Close Redis connections."""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
        self._initialized = False

    @property
    def client(self) -> redis.Redis:
        """Get Redis client, initializing if needed."""
        if not self._client:
            raise RuntimeError("Redis not initialized. Call initialize() first.")
        return self._client

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        try:
            data = await self.client.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception:
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | timedelta = CacheConfig.MEDIUM_TTL,
    ) -> bool:
        """Set value in cache with TTL."""
        try:
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            data = pickle.dumps(value)
            await self.client.setex(key, ttl, data)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            await self.client.delete(key)
            return True
        except Exception:
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        try:
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = await self.client.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted += await self.client.delete(*keys)
                if cursor == 0:
                    break
            return deleted
        except Exception:
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return await self.client.exists(key) > 0
        except Exception:
            return False

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment counter."""
        try:
            return await self.client.incrby(key, amount)
        except Exception:
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on existing key."""
        try:
            return await self.client.expire(key, ttl)
        except Exception:
            return False

    async def ttl(self, key: str) -> int:
        """Get remaining TTL for key."""
        try:
            return await self.client.ttl(key)
        except Exception:
            return -1

    async def get_json(self, key: str) -> dict | list | None:
        """Get JSON value from cache."""
        try:
            data = await self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception:
            return None

    async def set_json(
        self,
        key: str,
        value: dict | list,
        ttl: int = CacheConfig.MEDIUM_TTL,
    ) -> bool:
        """Set JSON value in cache."""
        try:
            data = json.dumps(value)
            await self.client.setex(key, ttl, data)
            return True
        except Exception:
            return False

    @asynccontextmanager
    async def distributed_lock(
        self,
        name: str,
        timeout: int = 30,
        blocking: bool = True,
        blocking_timeout: int = 10,
    ):
        """Distributed lock using Redis."""
        lock_key = f"{CacheConfig.LOCK_PREFIX}{name}"
        lock = self.client.lock(
            lock_key,
            timeout=timeout,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
        )
        try:
            acquired = await lock.acquire()
            if not acquired:
                raise TimeoutError(f"Could not acquire lock: {name}")
            yield lock
        finally:
            try:
                await lock.release()
            except Exception:
                pass

    async def health_check(self) -> dict[str, Any]:
        """Check Redis connectivity."""
        try:
            await self.client.ping()
            info = await self.client.info("memory")
            return {
                "status": "healthy",
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", "N/A"),
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    # ==========================================================================
    # TENANT-AWARE CACHE METHODS
    # ==========================================================================

    async def get_tenant(self, tenant_id: str | None, key: str) -> Any | None:
        """Get value from tenant-scoped cache."""
        full_key = CacheConfig.tenant_key(tenant_id, key)
        return await self.get(full_key)

    async def set_tenant(
        self,
        tenant_id: str | None,
        key: str,
        value: Any,
        ttl: int | timedelta = CacheConfig.MEDIUM_TTL,
    ) -> bool:
        """Set value in tenant-scoped cache."""
        full_key = CacheConfig.tenant_key(tenant_id, key)
        return await self.set(full_key, value, ttl)

    async def delete_tenant(self, tenant_id: str | None, key: str) -> bool:
        """Delete tenant-scoped key from cache."""
        full_key = CacheConfig.tenant_key(tenant_id, key)
        return await self.delete(full_key)

    async def delete_tenant_pattern(self, tenant_id: str, pattern: str = "*") -> int:
        """Delete all keys for a tenant matching pattern.

        Use this to invalidate all cached data for a specific tenant.
        """
        full_pattern = f"{CacheConfig.TENANT_PREFIX}{tenant_id}:{pattern}"
        return await self.delete_pattern(full_pattern)

    async def get_tenant_json(self, tenant_id: str | None, key: str) -> dict | list | None:
        """Get JSON value from tenant-scoped cache."""
        full_key = CacheConfig.tenant_key(tenant_id, key)
        return await self.get_json(full_key)

    async def set_tenant_json(
        self,
        tenant_id: str | None,
        key: str,
        value: dict | list,
        ttl: int = CacheConfig.MEDIUM_TTL,
    ) -> bool:
        """Set JSON value in tenant-scoped cache."""
        full_key = CacheConfig.tenant_key(tenant_id, key)
        return await self.set_json(full_key, value, ttl)


# Global cache instance
cache = RedisCache()


def generate_cache_key(*args, **kwargs) -> str:
    """Generate a cache key from arguments."""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(
    prefix: str,
    ttl: int = CacheConfig.MEDIUM_TTL,
    key_builder: Callable[..., str] | None = None,
):
    """Decorator for caching function results.

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_builder: Optional custom key builder function

    Example:
        @cached("metrics:dora", ttl=300)
        async def get_dora_metrics(project_id: str):
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Build cache key
            if key_builder:
                cache_key = f"{CacheConfig.PREFIX}{prefix}:{key_builder(*args, **kwargs)}"
            else:
                cache_key = f"{CacheConfig.PREFIX}{prefix}:{generate_cache_key(*args, **kwargs)}"

            # Try to get from cache
            try:
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    return cached_value
            except Exception:
                pass

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            try:
                await cache.set(cache_key, result, ttl)
            except Exception:
                pass

            return result

        return wrapper
    return decorator


def cache_invalidate(pattern: str):
    """Decorator to invalidate cache after function execution.

    Args:
        pattern: Cache key pattern to invalidate (supports wildcards)

    Example:
        @cache_invalidate("metrics:dora:*")
        async def update_project_metrics(project_id: str):
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            result = await func(*args, **kwargs)

            # Invalidate cache
            try:
                await cache.delete_pattern(f"{CacheConfig.PREFIX}{pattern}")
            except Exception:
                pass

            return result

        return wrapper
    return decorator


def tenant_cached(
    prefix: str,
    ttl: int = CacheConfig.MEDIUM_TTL,
    tenant_arg: str = "tenant_id",
    key_builder: Callable[..., str] | None = None,
):
    """Decorator for tenant-aware caching of function results.

    This ensures cache keys are isolated per tenant, preventing data leakage.

    Args:
        prefix: Cache key prefix (after tenant prefix)
        ttl: Time to live in seconds
        tenant_arg: Name of the tenant_id argument (keyword or first positional)
        key_builder: Optional custom key builder function

    Example:
        @tenant_cached("metrics:dora", ttl=300)
        async def get_dora_metrics(tenant_id: str, project_id: str):
            # Returns tenant-isolated cached metrics
            ...

        @tenant_cached("projects", tenant_arg="org_id")
        async def get_projects(org_id: str, status: str = "active"):
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Extract tenant_id from kwargs or first positional arg
            tenant_id = kwargs.get(tenant_arg)
            if tenant_id is None and args:
                # Try to get from first positional argument
                import inspect
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                if tenant_arg in params:
                    idx = params.index(tenant_arg)
                    if idx < len(args):
                        tenant_id = args[idx]

            # Build base key (excluding tenant_id from key generation)
            if key_builder:
                base_key = f"{prefix}:{key_builder(*args, **kwargs)}"
            else:
                # Filter out tenant_id from cache key generation
                filtered_kwargs = {k: v for k, v in kwargs.items() if k != tenant_arg}
                base_key = f"{prefix}:{generate_cache_key(*args, **filtered_kwargs)}"

            # Generate tenant-scoped cache key
            cache_key = CacheConfig.tenant_key(tenant_id, base_key)

            # Try to get from cache
            try:
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    return cached_value
            except Exception:
                pass

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            try:
                await cache.set(cache_key, result, ttl)
            except Exception:
                pass

            return result

        return wrapper
    return decorator


def tenant_cache_invalidate(pattern: str, tenant_arg: str = "tenant_id"):
    """Decorator to invalidate tenant-scoped cache after function execution.

    Args:
        pattern: Cache key pattern to invalidate (supports wildcards)
        tenant_arg: Name of the tenant_id argument

    Example:
        @tenant_cache_invalidate("metrics:*")
        async def update_project(tenant_id: str, project_id: str, data: dict):
            # Invalidates all metrics cache for this tenant after update
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Extract tenant_id
            tenant_id = kwargs.get(tenant_arg)
            if tenant_id is None and args:
                import inspect
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                if tenant_arg in params:
                    idx = params.index(tenant_arg)
                    if idx < len(args):
                        tenant_id = args[idx]

            result = await func(*args, **kwargs)

            # Invalidate tenant-scoped cache
            if tenant_id:
                try:
                    await cache.delete_tenant_pattern(tenant_id, pattern)
                except Exception:
                    pass

            return result

        return wrapper
    return decorator


class RateLimiter:
    """Token bucket rate limiter using Redis."""

    def __init__(
        self,
        key_prefix: str = "default",
        max_requests: int = 100,
        window_seconds: int = 60,
    ):
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def is_allowed(self, identifier: str) -> tuple[bool, dict[str, int]]:
        """Check if request is allowed under rate limit.

        Args:
            identifier: Unique identifier (e.g., user_id, IP address)

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        key = f"{CacheConfig.RATE_LIMIT_PREFIX}{self.key_prefix}:{identifier}"

        try:
            current = await cache.incr(key)

            if current == 1:
                await cache.expire(key, self.window_seconds)

            remaining = max(0, self.max_requests - current)
            ttl = await cache.ttl(key)

            info = {
                "limit": self.max_requests,
                "remaining": remaining,
                "reset_in": ttl if ttl > 0 else self.window_seconds,
            }

            return current <= self.max_requests, info

        except Exception:
            # Fail open if Redis is unavailable
            return True, {"limit": self.max_requests, "remaining": self.max_requests, "reset_in": 0}

    async def reset(self, identifier: str) -> bool:
        """Reset rate limit for identifier."""
        key = f"{CacheConfig.RATE_LIMIT_PREFIX}{self.key_prefix}:{identifier}"
        return await cache.delete(key)


# Pre-configured rate limiters
api_rate_limiter = RateLimiter(
    key_prefix="api",
    max_requests=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=60,
)

hourly_rate_limiter = RateLimiter(
    key_prefix="hourly",
    max_requests=settings.RATE_LIMIT_PER_HOUR,
    window_seconds=3600,
)


class TenantRateLimiter:
    """Tenant-aware rate limiter with separate limits for tenant and user.

    Provides fair usage across tenants by tracking:
    1. Per-tenant global limit (shared across all users in tenant)
    2. Per-user limit within a tenant (prevents single user from consuming tenant quota)

    This ensures:
    - Tenant A's heavy usage doesn't affect Tenant B
    - A single user can't monopolize a tenant's quota
    """

    def __init__(
        self,
        requests_per_minute_per_tenant: int = 1000,
        requests_per_minute_per_user: int = 100,
        window_seconds: int = 60,
    ):
        self.tenant_limit = requests_per_minute_per_tenant
        self.user_limit = requests_per_minute_per_user
        self.window_seconds = window_seconds

    async def is_allowed(
        self,
        identifier: str,
        tenant_id: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """Check if request is allowed under tenant and user rate limits.

        Args:
            identifier: User identifier (e.g., user_id, API key)
            tenant_id: Tenant/organization ID (optional)

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        info: dict[str, Any] = {
            "tenant_limit": self.tenant_limit,
            "user_limit": self.user_limit,
            "window_seconds": self.window_seconds,
        }

        try:
            # Check tenant-level limit if tenant_id provided
            if tenant_id:
                tenant_key = f"{CacheConfig.RATE_LIMIT_PREFIX}tenant:{tenant_id}"
                tenant_current = await cache.incr(tenant_key)

                if tenant_current == 1:
                    await cache.expire(tenant_key, self.window_seconds)

                info["tenant_remaining"] = max(0, self.tenant_limit - tenant_current)
                info["tenant_reset_in"] = await cache.ttl(tenant_key)

                if tenant_current > self.tenant_limit:
                    info["limited_by"] = "tenant"
                    info["retry_after"] = info["tenant_reset_in"]
                    return False, info

            # Check user-level limit (scoped to tenant if provided)
            if tenant_id:
                user_key = f"{CacheConfig.RATE_LIMIT_PREFIX}tenant:{tenant_id}:user:{identifier}"
            else:
                user_key = f"{CacheConfig.RATE_LIMIT_PREFIX}user:{identifier}"

            user_current = await cache.incr(user_key)

            if user_current == 1:
                await cache.expire(user_key, self.window_seconds)

            info["user_remaining"] = max(0, self.user_limit - user_current)
            info["user_reset_in"] = await cache.ttl(user_key)

            if user_current > self.user_limit:
                info["limited_by"] = "user"
                info["retry_after"] = info["user_reset_in"]
                return False, info

            return True, info

        except Exception:
            # Fail open if Redis is unavailable
            return True, {
                "tenant_limit": self.tenant_limit,
                "user_limit": self.user_limit,
                "tenant_remaining": self.tenant_limit,
                "user_remaining": self.user_limit,
            }

    async def reset_tenant(self, tenant_id: str) -> bool:
        """Reset rate limit for entire tenant."""
        pattern = f"{CacheConfig.RATE_LIMIT_PREFIX}tenant:{tenant_id}*"
        await cache.delete_pattern(pattern)
        return True

    async def reset_user(self, identifier: str, tenant_id: str | None = None) -> bool:
        """Reset rate limit for specific user."""
        if tenant_id:
            key = f"{CacheConfig.RATE_LIMIT_PREFIX}tenant:{tenant_id}:user:{identifier}"
        else:
            key = f"{CacheConfig.RATE_LIMIT_PREFIX}user:{identifier}"
        return await cache.delete(key)


# Pre-configured tenant rate limiter
tenant_rate_limiter = TenantRateLimiter(
    requests_per_minute_per_tenant=settings.PER_TENANT_RATE_LIMIT,
    requests_per_minute_per_user=settings.PER_USER_RATE_LIMIT,
)


class SessionStore:
    """Redis-based session storage."""

    @staticmethod
    async def create_session(
        session_id: str,
        data: dict[str, Any],
        ttl: int = 86400,  # 24 hours
    ) -> bool:
        """Create a new session."""
        key = f"{CacheConfig.SESSION_PREFIX}{session_id}"
        return await cache.set_json(key, data, ttl)

    @staticmethod
    async def get_session(session_id: str) -> dict[str, Any] | None:
        """Get session data."""
        key = f"{CacheConfig.SESSION_PREFIX}{session_id}"
        return await cache.get_json(key)

    @staticmethod
    async def update_session(
        session_id: str,
        data: dict[str, Any],
        ttl: int = 86400,
    ) -> bool:
        """Update session data."""
        return await SessionStore.create_session(session_id, data, ttl)

    @staticmethod
    async def delete_session(session_id: str) -> bool:
        """Delete session."""
        key = f"{CacheConfig.SESSION_PREFIX}{session_id}"
        return await cache.delete(key)

    @staticmethod
    async def extend_session(session_id: str, ttl: int = 86400) -> bool:
        """Extend session TTL."""
        key = f"{CacheConfig.SESSION_PREFIX}{session_id}"
        return await cache.expire(key, ttl)


class OAuthStateStore:
    """Redis-based OAuth state storage."""

    @staticmethod
    async def create_state(
        state: str,
        data: dict[str, Any],
        ttl: int = 600,  # 10 minutes
    ) -> bool:
        """Store OAuth state."""
        key = f"{CacheConfig.OAUTH_PREFIX}{state}"
        return await cache.set_json(key, data, ttl)

    @staticmethod
    async def get_state(state: str) -> dict[str, Any] | None:
        """Get OAuth state data."""
        key = f"{CacheConfig.OAUTH_PREFIX}{state}"
        return await cache.get_json(key)

    @staticmethod
    async def delete_state(state: str) -> bool:
        """Delete OAuth state (consume it)."""
        key = f"{CacheConfig.OAUTH_PREFIX}{state}"
        return await cache.delete(key)

    @staticmethod
    async def validate_and_consume(state: str) -> dict[str, Any] | None:
        """Validate state exists and consume it atomically."""
        data = await OAuthStateStore.get_state(state)
        if data:
            await OAuthStateStore.delete_state(state)
        return data
