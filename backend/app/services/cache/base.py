"""Base cache interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """A cache entry with metadata."""

    key: str
    value: T
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    ttl: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "ttl": self.ttl,
            "metadata": self.metadata,
            "hit_count": self.hit_count,
        }


class BaseCache(ABC):
    """Abstract base class for cache implementations."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """
        Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            metadata: Optional metadata

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: Cache key

        Returns:
            True if exists
        """
        pass

    @abstractmethod
    async def clear(self, pattern: str | None = None) -> int:
        """
        Clear cache entries.

        Args:
            pattern: Optional pattern to match keys

        Returns:
            Number of entries cleared
        """
        pass

    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary of cache stats
        """
        pass

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """
        Get multiple values from the cache.

        Args:
            keys: List of cache keys

        Returns:
            Dictionary of key-value pairs
        """
        results = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                results[key] = value
        return results

    async def set_many(
        self,
        items: dict[str, Any],
        ttl: int | None = None,
    ) -> int:
        """
        Set multiple values in the cache.

        Args:
            items: Dictionary of key-value pairs
            ttl: Time to live in seconds

        Returns:
            Number of items set
        """
        count = 0
        for key, value in items.items():
            if await self.set(key, value, ttl=ttl):
                count += 1
        return count

    async def delete_many(self, keys: list[str]) -> int:
        """
        Delete multiple keys from the cache.

        Args:
            keys: List of cache keys

        Returns:
            Number of keys deleted
        """
        count = 0
        for key in keys:
            if await self.delete(key):
                count += 1
        return count

    async def get_or_set(
        self,
        key: str,
        factory: callable,
        ttl: int | None = None,
    ) -> Any:
        """
        Get from cache or set using factory function.

        Args:
            key: Cache key
            factory: Async function to generate value if not cached
            ttl: Time to live in seconds

        Returns:
            Cached or newly generated value
        """
        value = await self.get(key)
        if value is not None:
            return value

        value = await factory()
        await self.set(key, value, ttl=ttl)
        return value
