"""Redis cache implementation."""

import json
from datetime import datetime, UTC, timedelta
from typing import Any

import structlog
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError

from app.services.cache.base import BaseCache, CacheEntry
from app.services.cache.config import CacheConfig

logger = structlog.get_logger()


class RedisCache(BaseCache):
    """Redis-based cache implementation."""

    def __init__(self, config: CacheConfig | None = None):
        """
        Initialize Redis cache.

        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None

        # Statistics
        self._hits = 0
        self._misses = 0
        self._errors = 0

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._client is not None:
            return

        try:
            self._pool = ConnectionPool.from_url(
                self.config.redis_url,
                max_connections=self.config.redis_max_connections,
                socket_timeout=self.config.redis_socket_timeout,
                retry_on_timeout=self.config.redis_retry_on_timeout,
            )
            self._client = Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()

            logger.info("Redis cache connected", url=self.config.redis_url)

        except RedisError as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._client = None

        if self._pool:
            await self._pool.disconnect()
            self._pool = None

        logger.info("Redis cache disconnected")

    async def _ensure_connected(self) -> Redis:
        """Ensure Redis is connected and return client."""
        if self._client is None:
            await self.connect()
        return self._client

    def _serialize(self, value: Any) -> str:
        """Serialize value for storage."""
        if isinstance(value, (str, int, float, bool)):
            return json.dumps({"_type": "primitive", "_value": value})

        if isinstance(value, dict):
            return json.dumps({"_type": "dict", "_value": value})

        if isinstance(value, list):
            return json.dumps({"_type": "list", "_value": value})

        # For complex objects, try JSON serialization
        try:
            return json.dumps({"_type": "object", "_value": value})
        except (TypeError, ValueError):
            # Fallback to string representation
            return json.dumps({"_type": "string", "_value": str(value)})

    def _deserialize(self, data: str) -> Any:
        """Deserialize value from storage."""
        try:
            parsed = json.loads(data)

            if isinstance(parsed, dict) and "_type" in parsed:
                return parsed["_value"]

            return parsed

        except (json.JSONDecodeError, KeyError):
            return data

    async def get(self, key: str) -> Any | None:
        """Get a value from the cache."""
        try:
            client = await self._ensure_connected()
            data = await client.get(key)

            if data is None:
                self._misses += 1
                return None

            self._hits += 1
            return self._deserialize(data.decode("utf-8"))

        except RedisError as e:
            self._errors += 1
            logger.error("Redis get error", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Set a value in the cache."""
        try:
            client = await self._ensure_connected()

            serialized = self._serialize(value)
            ttl = ttl or self.config.default_ttl

            await client.set(key, serialized, ex=ttl)

            # Store metadata separately if provided
            if metadata:
                meta_key = f"{key}:meta"
                await client.set(meta_key, json.dumps(metadata), ex=ttl)

            return True

        except RedisError as e:
            self._errors += 1
            logger.error("Redis set error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        try:
            client = await self._ensure_connected()
            result = await client.delete(key)

            # Also delete metadata
            await client.delete(f"{key}:meta")

            return result > 0

        except RedisError as e:
            self._errors += 1
            logger.error("Redis delete error", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        try:
            client = await self._ensure_connected()
            return await client.exists(key) > 0

        except RedisError as e:
            self._errors += 1
            logger.error("Redis exists error", key=key, error=str(e))
            return False

    async def clear(self, pattern: str | None = None) -> int:
        """Clear cache entries."""
        try:
            client = await self._ensure_connected()

            if pattern:
                # Use SCAN to find matching keys
                count = 0
                async for key in client.scan_iter(match=pattern):
                    await client.delete(key)
                    count += 1
                return count
            else:
                # Flush the entire database
                await client.flushdb()
                return -1  # Unknown count

        except RedisError as e:
            self._errors += 1
            logger.error("Redis clear error", pattern=pattern, error=str(e))
            return 0

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        try:
            client = await self._ensure_connected()
            info = await client.info()

            return {
                "hits": self._hits,
                "misses": self._misses,
                "errors": self._errors,
                "hit_rate": self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0,
                "redis": {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "total_keys": info.get("db0", {}).get("keys", 0) if isinstance(info.get("db0"), dict) else 0,
                    "uptime_seconds": info.get("uptime_in_seconds", 0),
                },
            }

        except RedisError as e:
            self._errors += 1
            logger.error("Redis stats error", error=str(e))
            return {
                "hits": self._hits,
                "misses": self._misses,
                "errors": self._errors,
                "redis": {"error": str(e)},
            }

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values using MGET."""
        if not keys:
            return {}

        try:
            client = await self._ensure_connected()
            values = await client.mget(keys)

            results = {}
            for key, value in zip(keys, values):
                if value is not None:
                    results[key] = self._deserialize(value.decode("utf-8"))
                    self._hits += 1
                else:
                    self._misses += 1

            return results

        except RedisError as e:
            self._errors += 1
            logger.error("Redis mget error", error=str(e))
            return {}

    async def set_many(
        self,
        items: dict[str, Any],
        ttl: int | None = None,
    ) -> int:
        """Set multiple values using pipeline."""
        if not items:
            return 0

        try:
            client = await self._ensure_connected()
            ttl = ttl or self.config.default_ttl

            async with client.pipeline(transaction=True) as pipe:
                for key, value in items.items():
                    serialized = self._serialize(value)
                    pipe.set(key, serialized, ex=ttl)

                await pipe.execute()

            return len(items)

        except RedisError as e:
            self._errors += 1
            logger.error("Redis mset error", error=str(e))
            return 0

    async def increment(
        self,
        key: str,
        amount: int = 1,
        ttl: int | None = None,
    ) -> int:
        """Increment a counter."""
        try:
            client = await self._ensure_connected()

            if ttl:
                # Use a Lua script for atomic increment with TTL
                script = """
                local current = redis.call('INCR', KEYS[1])
                if current == 1 then
                    redis.call('EXPIRE', KEYS[1], ARGV[1])
                end
                return current
                """
                result = await client.eval(script, 1, key, ttl)
            else:
                result = await client.incrby(key, amount)

            return result

        except RedisError as e:
            self._errors += 1
            logger.error("Redis increment error", key=key, error=str(e))
            return 0

    async def get_ttl(self, key: str) -> int:
        """Get remaining TTL for a key."""
        try:
            client = await self._ensure_connected()
            return await client.ttl(key)

        except RedisError as e:
            self._errors += 1
            logger.error("Redis TTL error", key=key, error=str(e))
            return -1

    async def set_expiry(self, key: str, ttl: int) -> bool:
        """Set or update expiry for a key."""
        try:
            client = await self._ensure_connected()
            return await client.expire(key, ttl)

        except RedisError as e:
            self._errors += 1
            logger.error("Redis expire error", key=key, error=str(e))
            return False

    # Rate limiting methods

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Check and update rate limit.

        Args:
            key: Rate limit key
            limit: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (allowed, remaining_requests)
        """
        try:
            client = await self._ensure_connected()
            rate_key = f"{self.config.prefix_rate_limit}{key}"

            # Use sliding window counter
            now = datetime.now(UTC)
            window_start = (now - timedelta(seconds=window_seconds)).timestamp()

            async with client.pipeline(transaction=True) as pipe:
                # Remove old entries
                pipe.zremrangebyscore(rate_key, 0, window_start)
                # Count current entries
                pipe.zcard(rate_key)
                # Add current request
                pipe.zadd(rate_key, {str(now.timestamp()): now.timestamp()})
                # Set expiry
                pipe.expire(rate_key, window_seconds)

                results = await pipe.execute()

            current_count = results[1]
            remaining = max(0, limit - current_count - 1)
            allowed = current_count < limit

            return allowed, remaining

        except RedisError as e:
            self._errors += 1
            logger.error("Rate limit check error", key=key, error=str(e))
            # Fail open on error
            return True, limit

    async def get_rate_limit_status(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> dict[str, Any]:
        """Get current rate limit status."""
        try:
            client = await self._ensure_connected()
            rate_key = f"{self.config.prefix_rate_limit}{key}"

            now = datetime.now(UTC)
            window_start = (now - timedelta(seconds=window_seconds)).timestamp()

            # Count requests in window
            count = await client.zcount(rate_key, window_start, now.timestamp())

            return {
                "limit": limit,
                "remaining": max(0, limit - count),
                "used": count,
                "window_seconds": window_seconds,
                "reset_at": (now + timedelta(seconds=window_seconds)).isoformat(),
            }

        except RedisError as e:
            self._errors += 1
            logger.error("Rate limit status error", key=key, error=str(e))
            return {
                "limit": limit,
                "remaining": limit,
                "error": str(e),
            }
