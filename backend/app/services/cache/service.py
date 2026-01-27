"""Unified cache service."""

import hashlib
import json
from typing import Any

import structlog

from app.services.cache.config import CacheConfig, get_cache_config
from app.services.cache.redis_cache import RedisCache
from app.services.cache.semantic_cache import SemanticCache

logger = structlog.get_logger()


class CacheService:
    """
    Unified cache service for NexusAI.

    Provides:
    - Simple key-value caching (Redis)
    - Semantic caching for LLM responses
    - Session management
    - Rate limiting
    """

    def __init__(
        self,
        config: CacheConfig | None = None,
        embedder=None,
    ):
        """
        Initialize the cache service.

        Args:
            config: Cache configuration
            embedder: Embedding service for semantic cache
        """
        self.config = config or get_cache_config()

        # Initialize Redis cache
        self.redis = RedisCache(config=self.config)

        # Initialize semantic cache
        self.semantic = SemanticCache(
            redis_cache=self.redis,
            config=self.config,
            embedder=embedder,
        ) if self.config.enable_semantic_cache else None

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all cache components."""
        if self._initialized:
            return

        await self.redis.connect()

        if self.semantic:
            await self.semantic.initialize()

        self._initialized = True
        logger.info("Cache service initialized")

    async def close(self) -> None:
        """Close all cache connections."""
        await self.redis.disconnect()
        self._initialized = False
        logger.info("Cache service closed")

    # Simple caching methods

    async def get(self, key: str) -> Any | None:
        """Get a value from the cache."""
        return await self.redis.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set a value in the cache."""
        return await self.redis.set(key, value, ttl=ttl)

    async def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        return await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        return await self.redis.exists(key)

    # LLM response caching

    def _llm_cache_key(
        self,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float,
    ) -> str:
        """Generate cache key for LLM request."""
        content = json.dumps({
            "messages": messages,
            "model": model,
            "temperature": temperature,
        }, sort_keys=True)
        hash_value = hashlib.sha256(content.encode()).hexdigest()
        return f"{self.config.prefix_llm}{hash_value}"

    async def get_llm_response(
        self,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float = 0.7,
        use_semantic: bool = True,
    ) -> tuple[Any | None, float, str]:
        """
        Get cached LLM response.

        Args:
            messages: Chat messages
            model: Model identifier
            temperature: Temperature setting
            use_semantic: Whether to use semantic cache

        Returns:
            Tuple of (response, similarity, cache_type)
        """
        # Try exact cache first
        key = self._llm_cache_key(messages, model, temperature)
        cached = await self.redis.get(key)

        if cached is not None:
            return cached, 1.0, "exact"

        # Try semantic cache for low-temperature requests
        if use_semantic and self.semantic and temperature <= 0.5:
            # Use last user message for semantic matching
            query = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    query = msg.get("content", "")
                    break

            if query:
                response, similarity = await self.semantic.get(query, model)
                if response is not None:
                    return {"content": response}, similarity, "semantic"

        return None, 0.0, "miss"

    async def set_llm_response(
        self,
        messages: list[dict[str, Any]],
        model: str,
        response: Any,
        temperature: float = 0.7,
        use_semantic: bool = True,
        embedding: list[float] | None = None,
    ) -> bool:
        """
        Cache an LLM response.

        Args:
            messages: Chat messages
            model: Model identifier
            response: LLM response to cache
            temperature: Temperature setting
            use_semantic: Whether to use semantic cache
            embedding: Pre-computed embedding for semantic cache

        Returns:
            True if cached successfully
        """
        # Exact cache
        key = self._llm_cache_key(messages, model, temperature)
        success = await self.redis.set(
            key,
            response,
            ttl=self.config.llm_response_ttl,
        )

        # Semantic cache for low-temperature requests
        if use_semantic and self.semantic and temperature <= 0.5:
            query = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    query = msg.get("content", "")
                    break

            if query:
                response_text = response.get("content", "") if isinstance(response, dict) else str(response)
                await self.semantic.set(
                    query=query,
                    response=response_text,
                    model=model,
                    query_embedding=embedding,
                )

        return success

    # Session management

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session data."""
        key = f"{self.config.prefix_session}{session_id}"
        return await self.redis.get(key)

    async def set_session(
        self,
        session_id: str,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """Set session data."""
        key = f"{self.config.prefix_session}{session_id}"
        return await self.redis.set(
            key,
            data,
            ttl=ttl or self.config.session_ttl,
        )

    async def update_session(
        self,
        session_id: str,
        updates: dict[str, Any],
    ) -> bool:
        """Update session data."""
        current = await self.get_session(session_id)
        if current is None:
            current = {}

        current.update(updates)
        return await self.set_session(session_id, current)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        key = f"{self.config.prefix_session}{session_id}"
        return await self.redis.delete(key)

    # Rate limiting

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Check rate limit for an identifier.

        Args:
            identifier: User/API key identifier
            limit: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (allowed, remaining_requests)
        """
        return await self.redis.check_rate_limit(
            identifier,
            limit,
            window_seconds,
        )

    async def get_rate_limit_status(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> dict[str, Any]:
        """Get current rate limit status."""
        return await self.redis.get_rate_limit_status(
            identifier,
            limit,
            window_seconds,
        )

    # Embedding caching

    async def get_embedding(self, text: str, model: str) -> list[float] | None:
        """Get cached embedding."""
        key = f"{self.config.prefix_embedding}{hashlib.sha256(f'{model}:{text}'.encode()).hexdigest()[:16]}"
        return await self.redis.get(key)

    async def set_embedding(
        self,
        text: str,
        model: str,
        embedding: list[float],
    ) -> bool:
        """Cache an embedding."""
        key = f"{self.config.prefix_embedding}{hashlib.sha256(f'{model}:{text}'.encode()).hexdigest()[:16]}"
        return await self.redis.set(
            key,
            embedding,
            ttl=self.config.embedding_ttl,
        )

    # Statistics

    async def get_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = {
            "redis": await self.redis.get_stats(),
        }

        if self.semantic:
            stats["semantic"] = self.semantic.get_stats()

        return stats

    async def clear_all(self) -> dict[str, int]:
        """Clear all caches."""
        results = {}

        results["redis"] = await self.redis.clear()

        if self.semantic:
            results["semantic"] = await self.semantic.clear()

        logger.info("All caches cleared", results=results)
        return results


# Global service instance
_cache_service: CacheService | None = None


async def get_cache_service(
    config: CacheConfig | None = None,
    embedder=None,
) -> CacheService:
    """Get or create the global cache service."""
    global _cache_service

    if _cache_service is None:
        _cache_service = CacheService(config=config, embedder=embedder)
        await _cache_service.initialize()

    return _cache_service


async def close_cache_service() -> None:
    """Close the global cache service."""
    global _cache_service

    if _cache_service is not None:
        await _cache_service.close()
        _cache_service = None
