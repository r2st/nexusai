"""Semantic cache for LLM responses using embedding similarity."""

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

import numpy as np
import structlog

from app.services.cache.config import CacheConfig
from app.services.cache.redis_cache import RedisCache

logger = structlog.get_logger()


@dataclass
class SemanticCacheEntry:
    """A semantic cache entry with embedding."""

    key: str
    query: str
    response: str
    embedding: list[float]
    model: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    ttl: int = 7200
    metadata: dict[str, Any] = field(default_factory=dict)
    hit_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "key": self.key,
            "query": self.query,
            "response": self.response,
            "embedding": self.embedding,
            "model": self.model,
            "created_at": self.created_at.isoformat(),
            "ttl": self.ttl,
            "metadata": self.metadata,
            "hit_count": self.hit_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticCacheEntry":
        """Create from dictionary."""
        return cls(
            key=data["key"],
            query=data["query"],
            response=data["response"],
            embedding=data["embedding"],
            model=data["model"],
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"],
            ttl=data.get("ttl", 7200),
            metadata=data.get("metadata", {}),
            hit_count=data.get("hit_count", 0),
        )


class SemanticCache:
    """
    Semantic cache for LLM responses.

    Uses embedding similarity to find cached responses for
    semantically similar queries, reducing redundant LLM calls.
    """

    def __init__(
        self,
        redis_cache: RedisCache | None = None,
        config: CacheConfig | None = None,
        embedder=None,
    ):
        """
        Initialize semantic cache.

        Args:
            redis_cache: Redis cache instance
            config: Cache configuration
            embedder: Embedding service for generating embeddings
        """
        self.config = config or CacheConfig()
        self.redis = redis_cache
        self.embedder = embedder

        # In-memory index for fast similarity search
        # In production, use a vector database or Redis Search
        self._index: dict[str, SemanticCacheEntry] = {}
        self._embedding_matrix: np.ndarray | None = None
        self._keys: list[str] = []

        # Statistics
        self._hits = 0
        self._misses = 0
        self._semantic_hits = 0

    async def initialize(self) -> None:
        """Initialize the cache and load existing entries."""
        if self.redis:
            await self.redis.connect()
            await self._load_index()

        logger.info(
            "Semantic cache initialized",
            entries=len(self._index),
            threshold=self.config.similarity_threshold,
        )

    async def _load_index(self) -> None:
        """Load existing entries from Redis."""
        if not self.redis:
            return

        try:
            # Load all semantic cache entries
            pattern = f"{self.config.prefix_semantic}*"
            keys = []

            client = await self.redis._ensure_connected()
            async for key in client.scan_iter(match=pattern):
                if not key.decode().endswith(":meta"):
                    keys.append(key.decode())

            if not keys:
                return

            # Load entries
            entries = await self.redis.get_many(keys)

            for key, data in entries.items():
                if data:
                    try:
                        entry = SemanticCacheEntry.from_dict(data)
                        self._index[key] = entry
                    except (KeyError, TypeError) as e:
                        logger.warning("Invalid cache entry", key=key, error=str(e))

            # Rebuild embedding matrix
            self._rebuild_embedding_matrix()

            logger.info("Loaded semantic cache entries", count=len(self._index))

        except Exception as e:
            logger.error("Failed to load semantic cache index", error=str(e))

    def _rebuild_embedding_matrix(self) -> None:
        """Rebuild the embedding matrix for similarity search."""
        if not self._index:
            self._embedding_matrix = None
            self._keys = []
            return

        self._keys = list(self._index.keys())
        embeddings = [self._index[k].embedding for k in self._keys]
        self._embedding_matrix = np.array(embeddings)

    def _compute_similarity(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        """
        Compute cosine similarity between query and cached embeddings.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of top results to return

        Returns:
            List of (key, similarity) tuples
        """
        if self._embedding_matrix is None or len(self._keys) == 0:
            return []

        # Normalize query embedding
        query = np.array(query_embedding)
        query_norm = query / (np.linalg.norm(query) + 1e-8)

        # Normalize cached embeddings
        norms = np.linalg.norm(self._embedding_matrix, axis=1, keepdims=True) + 1e-8
        normalized_matrix = self._embedding_matrix / norms

        # Compute cosine similarity
        similarities = np.dot(normalized_matrix, query_norm)

        # Get top-k indices
        if len(similarities) <= top_k:
            top_indices = np.argsort(similarities)[::-1]
        else:
            top_indices = np.argpartition(similarities, -top_k)[-top_k:]
            top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]

        results = [
            (self._keys[i], float(similarities[i]))
            for i in top_indices
            if similarities[i] >= self.config.similarity_threshold
        ]

        return results

    def _generate_key(self, query: str, model: str) -> str:
        """Generate a unique key for a query."""
        content = f"{model}:{query}"
        hash_value = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{self.config.prefix_semantic}{hash_value}"

    async def get(
        self,
        query: str,
        model: str,
        query_embedding: list[float] | None = None,
    ) -> tuple[str | None, float]:
        """
        Get a cached response for a query.

        First tries exact match, then semantic similarity.

        Args:
            query: The query string
            model: Model identifier
            query_embedding: Pre-computed query embedding (optional)

        Returns:
            Tuple of (response, similarity_score)
        """
        start_time = time.time()

        # Try exact match first
        key = self._generate_key(query, model)

        if key in self._index:
            entry = self._index[key]
            entry.hit_count += 1
            self._hits += 1

            logger.debug("Semantic cache exact hit", key=key)
            return entry.response, 1.0

        # Try semantic similarity
        if query_embedding is None:
            if self.embedder:
                query_embedding = await self.embedder.embed(query)
            else:
                self._misses += 1
                return None, 0.0

        similar = self._compute_similarity(query_embedding)

        if similar:
            best_key, similarity = similar[0]
            entry = self._index[best_key]
            entry.hit_count += 1
            self._semantic_hits += 1

            logger.debug(
                "Semantic cache similarity hit",
                key=best_key,
                similarity=similarity,
                latency_ms=(time.time() - start_time) * 1000,
            )
            return entry.response, similarity

        self._misses += 1
        return None, 0.0

    async def set(
        self,
        query: str,
        response: str,
        model: str,
        query_embedding: list[float] | None = None,
        ttl: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Cache a query-response pair.

        Args:
            query: The query string
            response: The response to cache
            model: Model identifier
            query_embedding: Pre-computed query embedding (optional)
            ttl: Time to live in seconds
            metadata: Optional metadata

        Returns:
            True if cached successfully
        """
        # Generate embedding if not provided
        if query_embedding is None:
            if self.embedder:
                query_embedding = await self.embedder.embed(query)
            else:
                logger.warning("No embedder available for semantic cache")
                return False

        key = self._generate_key(query, model)
        ttl = ttl or self.config.semantic_cache_ttl

        entry = SemanticCacheEntry(
            key=key,
            query=query,
            response=response,
            embedding=query_embedding,
            model=model,
            ttl=ttl,
            metadata=metadata or {},
        )

        # Store in memory index
        self._index[key] = entry
        self._rebuild_embedding_matrix()

        # Store in Redis for persistence
        if self.redis:
            try:
                await self.redis.set(key, entry.to_dict(), ttl=ttl)
            except Exception as e:
                logger.error("Failed to persist semantic cache entry", error=str(e))

        # Enforce max entries
        if len(self._index) > self.config.max_semantic_entries:
            await self._evict_oldest()

        logger.debug("Cached response", key=key, query_length=len(query))
        return True

    async def delete(self, query: str, model: str) -> bool:
        """Delete a cached entry."""
        key = self._generate_key(query, model)

        if key in self._index:
            del self._index[key]
            self._rebuild_embedding_matrix()

            if self.redis:
                await self.redis.delete(key)

            return True

        return False

    async def clear(self) -> int:
        """Clear all cached entries."""
        count = len(self._index)

        self._index.clear()
        self._embedding_matrix = None
        self._keys = []

        if self.redis:
            pattern = f"{self.config.prefix_semantic}*"
            await self.redis.clear(pattern)

        logger.info("Semantic cache cleared", entries=count)
        return count

    async def _evict_oldest(self) -> None:
        """Evict oldest entries to stay under max size."""
        if len(self._index) <= self.config.max_semantic_entries:
            return

        # Sort by creation time and hit count
        entries = sorted(
            self._index.items(),
            key=lambda x: (x[1].hit_count, x[1].created_at),
        )

        # Remove oldest 10%
        num_to_remove = max(1, len(entries) // 10)
        for key, _ in entries[:num_to_remove]:
            del self._index[key]
            if self.redis:
                await self.redis.delete(key)

        self._rebuild_embedding_matrix()
        logger.debug("Evicted semantic cache entries", count=num_to_remove)

    async def get_similar(
        self,
        query: str,
        model: str,
        top_k: int = 5,
        query_embedding: list[float] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Find similar cached queries.

        Args:
            query: The query string
            model: Model identifier
            top_k: Number of similar entries to return
            query_embedding: Pre-computed query embedding (optional)

        Returns:
            List of similar entries with similarity scores
        """
        if query_embedding is None:
            if self.embedder:
                query_embedding = await self.embedder.embed(query)
            else:
                return []

        similar = self._compute_similarity(query_embedding, top_k=top_k)

        results = []
        for key, similarity in similar:
            if key in self._index:
                entry = self._index[key]
                results.append({
                    "query": entry.query,
                    "response": entry.response[:200] + "..." if len(entry.response) > 200 else entry.response,
                    "similarity": similarity,
                    "model": entry.model,
                    "hit_count": entry.hit_count,
                })

        return results

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._semantic_hits + self._misses

        return {
            "entries": len(self._index),
            "max_entries": self.config.max_semantic_entries,
            "exact_hits": self._hits,
            "semantic_hits": self._semantic_hits,
            "misses": self._misses,
            "total_requests": total_requests,
            "hit_rate": (self._hits + self._semantic_hits) / total_requests if total_requests > 0 else 0,
            "semantic_hit_rate": self._semantic_hits / total_requests if total_requests > 0 else 0,
            "similarity_threshold": self.config.similarity_threshold,
        }

    async def warm(self, queries: list[dict[str, Any]]) -> int:
        """
        Warm the cache with pre-defined queries.

        Args:
            queries: List of dicts with 'query', 'response', 'model' keys

        Returns:
            Number of entries added
        """
        count = 0
        for item in queries:
            try:
                await self.set(
                    query=item["query"],
                    response=item["response"],
                    model=item.get("model", "default"),
                )
                count += 1
            except Exception as e:
                logger.warning("Failed to warm cache entry", error=str(e))

        logger.info("Cache warming completed", entries=count)
        return count
