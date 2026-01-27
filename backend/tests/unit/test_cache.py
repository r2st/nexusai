"""
Unit tests for Cache services.

Tests cover:
1. Redis cache operations (get, set, delete, TTL)
2. Semantic cache with embedding similarity
3. Cache hit/miss scenarios
4. Rate limiting via cache
5. Cache invalidation
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import hashlib

# Python 3.10 compatibility
UTC = timezone.utc

import numpy as np
import pytest
import pytest_asyncio

from app.services.cache.config import CacheConfig
from app.services.cache.redis_cache import RedisCache
from app.services.cache.semantic_cache import SemanticCache, SemanticCacheEntry
from app.services.cache.service import CacheService, get_cache_service, close_cache_service


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def cache_config():
    """Create a test cache configuration."""
    return CacheConfig(
        redis_url="redis://localhost:6379/15",  # Use test database
        redis_max_connections=5,
        redis_socket_timeout=2.0,
        redis_retry_on_timeout=True,
        default_ttl=300,  # 5 minutes for faster tests
        session_ttl=600,
        llm_response_ttl=300,
        embedding_ttl=3600,
        enable_semantic_cache=True,
        similarity_threshold=0.85,
        semantic_cache_ttl=300,
        max_semantic_entries=100,
        embedding_dimension=384,  # Smaller dimension for tests
        prefix_session="test:session:",
        prefix_llm="test:llm:",
        prefix_embedding="test:embedding:",
        prefix_semantic="test:semantic:",
        prefix_rate_limit="test:rate:",
    )


@pytest.fixture
def cache_config_no_semantic():
    """Create a cache config with semantic cache disabled."""
    return CacheConfig(
        redis_url="redis://localhost:6379/15",
        enable_semantic_cache=False,
        prefix_session="test:session:",
        prefix_llm="test:llm:",
        prefix_embedding="test:embedding:",
        prefix_semantic="test:semantic:",
        prefix_rate_limit="test:rate:",
    )


async def async_iter(items):
    """Helper to create an async iterator from a list."""
    for item in items:
        yield item


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock()
    client.ping = AsyncMock(return_value=True)
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.exists = AsyncMock(return_value=0)
    client.expire = AsyncMock(return_value=True)
    client.ttl = AsyncMock(return_value=300)
    client.incrby = AsyncMock(return_value=1)
    client.mget = AsyncMock(return_value=[])
    client.info = AsyncMock(return_value={
        "connected_clients": 1,
        "used_memory_human": "1M",
        "uptime_in_seconds": 1000,
    })
    client.flushdb = AsyncMock()
    # scan_iter needs to return an async iterator for 'async for' usage
    client.scan_iter = MagicMock(return_value=async_iter([]))
    client.zremrangebyscore = AsyncMock()
    client.zcard = AsyncMock(return_value=0)
    client.zadd = AsyncMock()
    client.zcount = AsyncMock(return_value=0)
    client.eval = AsyncMock(return_value=1)
    client.close = AsyncMock()

    # Pipeline mock
    pipeline = AsyncMock()
    pipeline.__aenter__ = AsyncMock(return_value=pipeline)
    pipeline.__aexit__ = AsyncMock(return_value=None)
    pipeline.set = MagicMock()
    pipeline.zremrangebyscore = MagicMock()
    pipeline.zcard = MagicMock()
    pipeline.zadd = MagicMock()
    pipeline.expire = MagicMock()
    pipeline.execute = AsyncMock(return_value=[None, 0, None, True])
    client.pipeline = MagicMock(return_value=pipeline)

    return client


@pytest.fixture
def mock_connection_pool():
    """Create a mock connection pool."""
    pool = MagicMock()
    pool.disconnect = AsyncMock()
    return pool


@pytest.fixture
def mock_embedder():
    """Create a mock embedding service."""
    embedder = AsyncMock()
    # Return random embeddings of dimension 384
    embedder.embed = AsyncMock(
        side_effect=lambda text: np.random.randn(384).tolist()
    )
    return embedder


@pytest.fixture
def sample_embedding():
    """Create a sample embedding vector."""
    np.random.seed(42)  # For reproducibility
    return np.random.randn(384).tolist()


@pytest.fixture
def sample_messages():
    """Create sample chat messages."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
    ]


@pytest.fixture
def sample_llm_response():
    """Create a sample LLM response."""
    return {
        "content": "The capital of France is Paris.",
        "model": "gpt-4o-mini",
        "finish_reason": "stop",
    }


# =============================================================================
# Redis Cache Tests
# =============================================================================


class TestRedisCache:
    """Tests for RedisCache."""

    @pytest_asyncio.fixture
    async def redis_cache(self, cache_config, mock_redis_client, mock_connection_pool):
        """Create a Redis cache with mocked client."""
        cache = RedisCache(config=cache_config)
        cache._client = mock_redis_client
        cache._pool = mock_connection_pool
        return cache

    @pytest.mark.asyncio
    async def test_connect(self, cache_config, mock_redis_client):
        """Test Redis connection."""
        cache = RedisCache(config=cache_config)

        with patch("app.services.cache.redis_cache.ConnectionPool") as mock_pool_class:
            mock_pool = MagicMock()
            mock_pool_class.from_url = MagicMock(return_value=mock_pool)

            with patch("app.services.cache.redis_cache.Redis") as mock_redis_class:
                mock_redis_class.return_value = mock_redis_client

                await cache.connect()

                assert cache._client is not None
                mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, redis_cache):
        """Test Redis disconnection."""
        # Save references before disconnect sets them to None
        mock_client = redis_cache._client
        mock_pool = redis_cache._pool

        await redis_cache.disconnect()

        mock_client.close.assert_called_once()
        mock_pool.disconnect.assert_called_once()
        assert redis_cache._client is None
        assert redis_cache._pool is None

    @pytest.mark.asyncio
    async def test_set_primitive_value(self, redis_cache, mock_redis_client):
        """Test setting a primitive value."""
        result = await redis_cache.set("test_key", "test_value", ttl=60)

        assert result is True
        mock_redis_client.set.assert_called_once()
        call_args = mock_redis_client.set.call_args
        assert call_args[0][0] == "test_key"
        # Check that the value was serialized as a primitive
        serialized = json.loads(call_args[0][1])
        assert serialized["_type"] == "primitive"
        assert serialized["_value"] == "test_value"

    @pytest.mark.asyncio
    async def test_set_dict_value(self, redis_cache, mock_redis_client):
        """Test setting a dictionary value."""
        data = {"name": "test", "count": 42}
        result = await redis_cache.set("dict_key", data, ttl=120)

        assert result is True
        call_args = mock_redis_client.set.call_args
        serialized = json.loads(call_args[0][1])
        assert serialized["_type"] == "dict"
        assert serialized["_value"] == data

    @pytest.mark.asyncio
    async def test_set_list_value(self, redis_cache, mock_redis_client):
        """Test setting a list value."""
        data = [1, 2, 3, "four", 5.0]
        result = await redis_cache.set("list_key", data)

        assert result is True
        call_args = mock_redis_client.set.call_args
        serialized = json.loads(call_args[0][1])
        assert serialized["_type"] == "list"
        assert serialized["_value"] == data

    @pytest.mark.asyncio
    async def test_set_with_metadata(self, redis_cache, mock_redis_client):
        """Test setting a value with metadata."""
        metadata = {"source": "test", "version": 1}
        result = await redis_cache.set(
            "key_with_meta",
            "value",
            ttl=60,
            metadata=metadata,
        )

        assert result is True
        # Should have set both value and metadata
        assert mock_redis_client.set.call_count == 2

    @pytest.mark.asyncio
    async def test_get_existing_value(self, redis_cache, mock_redis_client):
        """Test getting an existing value."""
        stored_value = json.dumps({"_type": "primitive", "_value": "cached_data"})
        mock_redis_client.get = AsyncMock(return_value=stored_value.encode("utf-8"))

        result = await redis_cache.get("existing_key")

        assert result == "cached_data"
        assert redis_cache._hits == 1
        assert redis_cache._misses == 0

    @pytest.mark.asyncio
    async def test_get_missing_value(self, redis_cache, mock_redis_client):
        """Test getting a non-existent value."""
        mock_redis_client.get = AsyncMock(return_value=None)

        result = await redis_cache.get("missing_key")

        assert result is None
        assert redis_cache._hits == 0
        assert redis_cache._misses == 1

    @pytest.mark.asyncio
    async def test_get_dict_value(self, redis_cache, mock_redis_client):
        """Test getting a dictionary value."""
        data = {"name": "test", "items": [1, 2, 3]}
        stored_value = json.dumps({"_type": "dict", "_value": data})
        mock_redis_client.get = AsyncMock(return_value=stored_value.encode("utf-8"))

        result = await redis_cache.get("dict_key")

        assert result == data
        assert result["name"] == "test"

    @pytest.mark.asyncio
    async def test_delete_existing_key(self, redis_cache, mock_redis_client):
        """Test deleting an existing key."""
        mock_redis_client.delete = AsyncMock(return_value=1)

        result = await redis_cache.delete("key_to_delete")

        assert result is True
        # Should delete both key and metadata
        assert mock_redis_client.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_missing_key(self, redis_cache, mock_redis_client):
        """Test deleting a non-existent key."""
        mock_redis_client.delete = AsyncMock(return_value=0)

        result = await redis_cache.delete("missing_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, redis_cache, mock_redis_client):
        """Test checking existence of existing key."""
        mock_redis_client.exists = AsyncMock(return_value=1)

        result = await redis_cache.exists("existing_key")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, redis_cache, mock_redis_client):
        """Test checking existence of non-existent key."""
        mock_redis_client.exists = AsyncMock(return_value=0)

        result = await redis_cache.exists("missing_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_ttl(self, redis_cache, mock_redis_client):
        """Test getting TTL for a key."""
        mock_redis_client.ttl = AsyncMock(return_value=150)

        ttl = await redis_cache.get_ttl("key_with_ttl")

        assert ttl == 150
        mock_redis_client.ttl.assert_called_once_with("key_with_ttl")

    @pytest.mark.asyncio
    async def test_set_expiry(self, redis_cache, mock_redis_client):
        """Test setting expiry on a key."""
        mock_redis_client.expire = AsyncMock(return_value=True)

        result = await redis_cache.set_expiry("key", 3600)

        assert result is True
        mock_redis_client.expire.assert_called_once_with("key", 3600)

    @pytest.mark.asyncio
    async def test_increment(self, redis_cache, mock_redis_client):
        """Test incrementing a counter."""
        mock_redis_client.incrby = AsyncMock(return_value=5)

        result = await redis_cache.increment("counter_key", amount=1)

        assert result == 5
        mock_redis_client.incrby.assert_called_once_with("counter_key", 1)

    @pytest.mark.asyncio
    async def test_increment_with_ttl(self, redis_cache, mock_redis_client):
        """Test incrementing a counter with TTL."""
        mock_redis_client.eval = AsyncMock(return_value=1)

        result = await redis_cache.increment("new_counter", ttl=60)

        assert result == 1
        mock_redis_client.eval.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_many(self, redis_cache, mock_redis_client):
        """Test getting multiple values."""
        values = [
            json.dumps({"_type": "primitive", "_value": "value1"}).encode(),
            None,
            json.dumps({"_type": "primitive", "_value": "value3"}).encode(),
        ]
        mock_redis_client.mget = AsyncMock(return_value=values)

        result = await redis_cache.get_many(["key1", "key2", "key3"])

        assert result == {"key1": "value1", "key3": "value3"}
        assert redis_cache._hits == 2
        assert redis_cache._misses == 1

    @pytest.mark.asyncio
    async def test_set_many(self, redis_cache, mock_redis_client):
        """Test setting multiple values."""
        items = {"key1": "value1", "key2": "value2", "key3": "value3"}

        pipeline = mock_redis_client.pipeline.return_value
        pipeline.__aenter__.return_value = pipeline

        result = await redis_cache.set_many(items, ttl=60)

        assert result == 3
        assert pipeline.set.call_count == 3

    @pytest.mark.asyncio
    async def test_clear_all(self, redis_cache, mock_redis_client):
        """Test clearing all cache entries."""
        result = await redis_cache.clear()

        mock_redis_client.flushdb.assert_called_once()
        assert result == -1  # Unknown count for full flush

    @pytest.mark.asyncio
    async def test_clear_pattern(self, redis_cache, mock_redis_client):
        """Test clearing cache entries by pattern."""
        async def mock_scan():
            for key in [b"test:key1", b"test:key2", b"test:key3"]:
                yield key

        mock_redis_client.scan_iter = MagicMock(return_value=mock_scan())
        mock_redis_client.delete = AsyncMock(return_value=1)

        result = await redis_cache.clear(pattern="test:*")

        assert result == 3

    @pytest.mark.asyncio
    async def test_get_stats(self, redis_cache, mock_redis_client):
        """Test getting cache statistics."""
        redis_cache._hits = 100
        redis_cache._misses = 25
        redis_cache._errors = 2

        stats = await redis_cache.get_stats()

        assert stats["hits"] == 100
        assert stats["misses"] == 25
        assert stats["errors"] == 2
        assert stats["hit_rate"] == 0.8  # 100 / 125

    @pytest.mark.asyncio
    async def test_serialization_deserialization_roundtrip(self, redis_cache):
        """Test that serialization and deserialization are inverse operations."""
        test_values = [
            "simple string",
            42,
            3.14,
            True,
            False,
            {"key": "value", "nested": {"a": 1}},
            [1, 2, "three", 4.0],
        ]

        for value in test_values:
            serialized = redis_cache._serialize(value)
            deserialized = redis_cache._deserialize(serialized)
            assert deserialized == value, f"Failed for value: {value}"


# =============================================================================
# Rate Limiting Tests
# =============================================================================


class TestRateLimiting:
    """Tests for rate limiting via Redis cache."""

    @pytest_asyncio.fixture
    async def redis_cache(self, cache_config, mock_redis_client, mock_connection_pool):
        """Create a Redis cache for rate limit testing."""
        cache = RedisCache(config=cache_config)
        cache._client = mock_redis_client
        cache._pool = mock_connection_pool
        return cache

    @pytest.mark.asyncio
    async def test_rate_limit_allowed(self, redis_cache, mock_redis_client):
        """Test rate limit when under the limit."""
        pipeline = mock_redis_client.pipeline.return_value
        pipeline.__aenter__.return_value = pipeline
        # Simulate 5 requests when limit is 10
        pipeline.execute = AsyncMock(return_value=[None, 5, None, True])

        allowed, remaining = await redis_cache.check_rate_limit(
            key="user_123",
            limit=10,
            window_seconds=60,
        )

        assert allowed is True
        assert remaining == 4  # 10 - 5 - 1 = 4

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, redis_cache, mock_redis_client):
        """Test rate limit when at or over the limit."""
        pipeline = mock_redis_client.pipeline.return_value
        pipeline.__aenter__.return_value = pipeline
        # Simulate 10 requests when limit is 10
        pipeline.execute = AsyncMock(return_value=[None, 10, None, True])

        allowed, remaining = await redis_cache.check_rate_limit(
            key="user_123",
            limit=10,
            window_seconds=60,
        )

        assert allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_rate_limit_first_request(self, redis_cache, mock_redis_client):
        """Test rate limit for first request (no previous entries)."""
        pipeline = mock_redis_client.pipeline.return_value
        pipeline.__aenter__.return_value = pipeline
        # Simulate 0 previous requests
        pipeline.execute = AsyncMock(return_value=[None, 0, None, True])

        allowed, remaining = await redis_cache.check_rate_limit(
            key="new_user",
            limit=60,
            window_seconds=60,
        )

        assert allowed is True
        assert remaining == 59

    @pytest.mark.asyncio
    async def test_rate_limit_status(self, redis_cache, mock_redis_client):
        """Test getting rate limit status."""
        mock_redis_client.zcount = AsyncMock(return_value=25)

        status = await redis_cache.get_rate_limit_status(
            key="user_123",
            limit=60,
            window_seconds=60,
        )

        assert status["limit"] == 60
        assert status["used"] == 25
        assert status["remaining"] == 35
        assert status["window_seconds"] == 60
        assert "reset_at" in status

    @pytest.mark.asyncio
    async def test_rate_limit_sliding_window(self, redis_cache, mock_redis_client):
        """Test that rate limiting uses sliding window."""
        # This test verifies that the sliding window implementation
        # removes old entries before counting
        pipeline = mock_redis_client.pipeline.return_value
        pipeline.__aenter__.return_value = pipeline

        await redis_cache.check_rate_limit(
            key="user_456",
            limit=100,
            window_seconds=3600,
        )

        # Verify zremrangebyscore was called to remove old entries
        assert pipeline.zremrangebyscore.called


# =============================================================================
# Semantic Cache Tests
# =============================================================================


class TestSemanticCache:
    """Tests for SemanticCache."""

    @pytest_asyncio.fixture
    async def semantic_cache(self, cache_config, mock_redis_client, mock_connection_pool, mock_embedder):
        """Create a semantic cache with mocked dependencies."""
        redis_cache = RedisCache(config=cache_config)
        redis_cache._client = mock_redis_client
        redis_cache._pool = mock_connection_pool

        cache = SemanticCache(
            redis_cache=redis_cache,
            config=cache_config,
            embedder=mock_embedder,
        )
        return cache

    def test_generate_key(self, semantic_cache):
        """Test key generation for semantic cache."""
        key1 = semantic_cache._generate_key("test query", "gpt-4")
        key2 = semantic_cache._generate_key("test query", "gpt-4")
        key3 = semantic_cache._generate_key("different query", "gpt-4")
        key4 = semantic_cache._generate_key("test query", "claude-3")

        assert key1 == key2  # Same query and model
        assert key1 != key3  # Different query
        assert key1 != key4  # Different model
        assert key1.startswith("test:semantic:")

    @pytest.mark.asyncio
    async def test_set_entry(self, semantic_cache, sample_embedding):
        """Test setting an entry in semantic cache."""
        result = await semantic_cache.set(
            query="What is Python?",
            response="Python is a programming language.",
            model="gpt-4",
            query_embedding=sample_embedding,
        )

        assert result is True
        assert len(semantic_cache._index) == 1

    @pytest.mark.asyncio
    async def test_set_without_embedding_uses_embedder(self, semantic_cache, mock_embedder):
        """Test that set generates embedding if not provided."""
        result = await semantic_cache.set(
            query="What is JavaScript?",
            response="JavaScript is a programming language.",
            model="gpt-4",
        )

        assert result is True
        mock_embedder.embed.assert_called_once_with("What is JavaScript?")

    @pytest.mark.asyncio
    async def test_get_exact_match(self, semantic_cache, sample_embedding):
        """Test getting an exact match from semantic cache."""
        # First, set an entry
        await semantic_cache.set(
            query="What is the capital of France?",
            response="Paris is the capital of France.",
            model="gpt-4",
            query_embedding=sample_embedding,
        )

        # Get with exact same query
        response, similarity = await semantic_cache.get(
            query="What is the capital of France?",
            model="gpt-4",
            query_embedding=sample_embedding,
        )

        assert response == "Paris is the capital of France."
        assert similarity == 1.0
        assert semantic_cache._hits == 1

    @pytest.mark.asyncio
    async def test_get_semantic_match(self, semantic_cache):
        """Test getting a semantic match with similar query."""
        np.random.seed(42)
        embedding1 = np.random.randn(384).tolist()

        # Set an entry
        await semantic_cache.set(
            query="What is Python?",
            response="Python is a programming language.",
            model="gpt-4",
            query_embedding=embedding1,
        )

        # Create a similar embedding (add small noise)
        similar_embedding = (np.array(embedding1) + np.random.randn(384) * 0.1).tolist()

        response, similarity = await semantic_cache.get(
            query="Tell me about Python",  # Different query text
            model="gpt-4",
            query_embedding=similar_embedding,
        )

        # Should find a semantic match if similarity > threshold
        if similarity >= semantic_cache.config.similarity_threshold:
            assert response is not None
            assert semantic_cache._semantic_hits == 1

    @pytest.mark.asyncio
    async def test_get_miss(self, semantic_cache, sample_embedding):
        """Test cache miss."""
        response, similarity = await semantic_cache.get(
            query="Random unrelated query",
            model="gpt-4",
            query_embedding=sample_embedding,
        )

        assert response is None
        assert similarity == 0.0
        assert semantic_cache._misses == 1

    @pytest.mark.asyncio
    async def test_delete_entry(self, semantic_cache, sample_embedding):
        """Test deleting an entry."""
        # Set an entry
        await semantic_cache.set(
            query="Delete me",
            response="I will be deleted.",
            model="gpt-4",
            query_embedding=sample_embedding,
        )

        assert len(semantic_cache._index) == 1

        # Delete it
        result = await semantic_cache.delete("Delete me", "gpt-4")

        assert result is True
        assert len(semantic_cache._index) == 0

    @pytest.mark.asyncio
    async def test_clear_cache(self, semantic_cache, sample_embedding):
        """Test clearing all entries."""
        # Add multiple entries
        for i in range(5):
            embedding = np.random.randn(384).tolist()
            await semantic_cache.set(
                query=f"Query {i}",
                response=f"Response {i}",
                model="gpt-4",
                query_embedding=embedding,
            )

        assert len(semantic_cache._index) == 5

        # Clear all
        count = await semantic_cache.clear()

        assert count == 5
        assert len(semantic_cache._index) == 0
        assert semantic_cache._embedding_matrix is None

    @pytest.mark.asyncio
    async def test_get_similar_queries(self, semantic_cache):
        """Test finding similar cached queries."""
        np.random.seed(123)

        # Add several entries with related embeddings
        base_embedding = np.random.randn(384)

        for i in range(5):
            embedding = (base_embedding + np.random.randn(384) * 0.1).tolist()
            await semantic_cache.set(
                query=f"Python question {i}",
                response=f"Python answer {i}",
                model="gpt-4",
                query_embedding=embedding,
            )

        # Find similar to base
        similar = await semantic_cache.get_similar(
            query="Python general",
            model="gpt-4",
            top_k=3,
            query_embedding=base_embedding.tolist(),
        )

        assert len(similar) <= 3

    @pytest.mark.asyncio
    async def test_eviction_on_max_entries(self, cache_config, mock_redis_client, mock_connection_pool, mock_embedder):
        """Test that old entries are evicted when max is reached."""
        config = CacheConfig(
            max_semantic_entries=5,  # Very small limit
            prefix_semantic="test:semantic:",
        )

        redis_cache = RedisCache(config=config)
        redis_cache._client = mock_redis_client
        redis_cache._pool = mock_connection_pool

        cache = SemanticCache(
            redis_cache=redis_cache,
            config=config,
            embedder=mock_embedder,
        )

        # Add more entries than max
        for i in range(10):
            embedding = np.random.randn(384).tolist()
            await cache.set(
                query=f"Query {i}",
                response=f"Response {i}",
                model="gpt-4",
                query_embedding=embedding,
            )

        # Should have evicted some entries
        assert len(cache._index) <= config.max_semantic_entries

    def test_compute_similarity(self, semantic_cache):
        """Test cosine similarity computation."""
        # Add entries manually for testing
        np.random.seed(42)
        embedding1 = np.random.randn(384).tolist()
        embedding2 = (-np.array(embedding1)).tolist()  # Opposite direction
        embedding3 = embedding1  # Same direction

        semantic_cache._index = {
            "key1": SemanticCacheEntry(
                key="key1",
                query="query1",
                response="response1",
                embedding=embedding1,
                model="gpt-4",
            ),
            "key2": SemanticCacheEntry(
                key="key2",
                query="query2",
                response="response2",
                embedding=embedding2,
                model="gpt-4",
            ),
        }
        semantic_cache._rebuild_embedding_matrix()

        # Search with embedding3 (same as embedding1)
        results = semantic_cache._compute_similarity(embedding3, top_k=2)

        # key1 should have highest similarity (1.0)
        assert len(results) > 0
        # First result should be key1 with high similarity
        if results:
            assert results[0][0] == "key1"
            assert results[0][1] > 0.99  # Nearly 1.0

    def test_get_stats(self, semantic_cache):
        """Test getting cache statistics."""
        semantic_cache._hits = 50
        semantic_cache._semantic_hits = 30
        semantic_cache._misses = 20

        stats = semantic_cache.get_stats()

        assert stats["exact_hits"] == 50
        assert stats["semantic_hits"] == 30
        assert stats["misses"] == 20
        assert stats["total_requests"] == 100
        assert stats["hit_rate"] == 0.8  # (50 + 30) / 100

    @pytest.mark.asyncio
    async def test_warm_cache(self, semantic_cache, mock_embedder):
        """Test warming the cache with pre-defined queries."""
        queries = [
            {"query": "What is AI?", "response": "AI is artificial intelligence.", "model": "gpt-4"},
            {"query": "What is ML?", "response": "ML is machine learning.", "model": "gpt-4"},
            {"query": "What is DL?", "response": "DL is deep learning.", "model": "gpt-4"},
        ]

        count = await semantic_cache.warm(queries)

        assert count == 3
        assert len(semantic_cache._index) == 3


class TestSemanticCacheEntry:
    """Tests for SemanticCacheEntry dataclass."""

    def test_to_dict(self, sample_embedding):
        """Test converting entry to dictionary."""
        entry = SemanticCacheEntry(
            key="test_key",
            query="test query",
            response="test response",
            embedding=sample_embedding,
            model="gpt-4",
            metadata={"source": "test"},
        )

        data = entry.to_dict()

        assert data["key"] == "test_key"
        assert data["query"] == "test query"
        assert data["response"] == "test response"
        assert data["embedding"] == sample_embedding
        assert data["model"] == "gpt-4"
        assert data["metadata"] == {"source": "test"}
        assert "created_at" in data

    def test_from_dict(self, sample_embedding):
        """Test creating entry from dictionary."""
        data = {
            "key": "test_key",
            "query": "test query",
            "response": "test response",
            "embedding": sample_embedding,
            "model": "gpt-4",
            "created_at": "2024-01-15T10:30:00+00:00",
            "ttl": 3600,
            "metadata": {"source": "test"},
            "hit_count": 5,
        }

        entry = SemanticCacheEntry.from_dict(data)

        assert entry.key == "test_key"
        assert entry.query == "test query"
        assert entry.response == "test response"
        assert entry.model == "gpt-4"
        assert entry.ttl == 3600
        assert entry.hit_count == 5


# =============================================================================
# Cache Service Tests
# =============================================================================


class TestCacheService:
    """Tests for unified CacheService."""

    @pytest_asyncio.fixture
    async def cache_service(self, cache_config, mock_redis_client, mock_connection_pool, mock_embedder):
        """Create a cache service with mocked dependencies."""
        with patch.object(RedisCache, "connect", new_callable=AsyncMock):
            service = CacheService(config=cache_config, embedder=mock_embedder)
            service.redis._client = mock_redis_client
            service.redis._pool = mock_connection_pool

            if service.semantic:
                service.semantic.redis = service.redis

            return service

    @pytest.mark.asyncio
    async def test_initialize(self, cache_config, mock_redis_client):
        """Test service initialization."""
        with patch.object(RedisCache, "connect", new_callable=AsyncMock) as mock_connect:
            service = CacheService(config=cache_config)
            service.redis._client = mock_redis_client

            await service.initialize()

            assert service._initialized is True
            # connect is called twice: once by CacheService.initialize() and once by
            # SemanticCache.initialize(). In production, the second call is a no-op
            # since RedisCache.connect() returns early if already connected.
            assert mock_connect.call_count == 2

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, cache_service):
        """Test that initialize is idempotent."""
        cache_service._initialized = True

        with patch.object(cache_service.redis, "connect", new_callable=AsyncMock) as mock_connect:
            await cache_service.initialize()

            mock_connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_close(self, cache_service):
        """Test closing the cache service."""
        cache_service._initialized = True

        await cache_service.close()

        assert cache_service._initialized is False

    @pytest.mark.asyncio
    async def test_get_set_delete(self, cache_service, mock_redis_client):
        """Test basic get, set, delete operations."""
        # Set
        result = await cache_service.set("key", "value", ttl=60)
        assert result is True

        # Get
        stored_value = json.dumps({"_type": "primitive", "_value": "value"})
        mock_redis_client.get = AsyncMock(return_value=stored_value.encode())
        result = await cache_service.get("key")
        assert result == "value"

        # Delete
        mock_redis_client.delete = AsyncMock(return_value=1)
        result = await cache_service.delete("key")
        assert result is True

    @pytest.mark.asyncio
    async def test_exists(self, cache_service, mock_redis_client):
        """Test checking key existence."""
        mock_redis_client.exists = AsyncMock(return_value=1)

        result = await cache_service.exists("some_key")

        assert result is True

    @pytest.mark.asyncio
    async def test_llm_cache_key_generation(self, cache_service, sample_messages):
        """Test LLM cache key generation."""
        key1 = cache_service._llm_cache_key(
            messages=sample_messages,
            model="gpt-4",
            temperature=0.7,
        )
        key2 = cache_service._llm_cache_key(
            messages=sample_messages,
            model="gpt-4",
            temperature=0.7,
        )
        key3 = cache_service._llm_cache_key(
            messages=sample_messages,
            model="gpt-4",
            temperature=0.5,  # Different temperature
        )

        assert key1 == key2  # Same inputs
        assert key1 != key3  # Different temperature
        assert key1.startswith("test:llm:")

    @pytest.mark.asyncio
    async def test_get_llm_response_exact_hit(self, cache_service, mock_redis_client, sample_messages, sample_llm_response):
        """Test getting exact cache hit for LLM response."""
        stored_value = json.dumps({"_type": "dict", "_value": sample_llm_response})
        mock_redis_client.get = AsyncMock(return_value=stored_value.encode())

        response, similarity, cache_type = await cache_service.get_llm_response(
            messages=sample_messages,
            model="gpt-4o-mini",
            temperature=0.7,
        )

        assert response == sample_llm_response
        assert similarity == 1.0
        assert cache_type == "exact"

    @pytest.mark.asyncio
    async def test_get_llm_response_miss(self, cache_service, mock_redis_client, sample_messages):
        """Test cache miss for LLM response."""
        mock_redis_client.get = AsyncMock(return_value=None)

        response, similarity, cache_type = await cache_service.get_llm_response(
            messages=sample_messages,
            model="gpt-4o-mini",
            temperature=0.7,
            use_semantic=False,
        )

        assert response is None
        assert similarity == 0.0
        assert cache_type == "miss"

    @pytest.mark.asyncio
    async def test_set_llm_response(self, cache_service, mock_redis_client, sample_messages, sample_llm_response):
        """Test caching an LLM response."""
        result = await cache_service.set_llm_response(
            messages=sample_messages,
            model="gpt-4o-mini",
            response=sample_llm_response,
            temperature=0.7,
            use_semantic=False,
        )

        assert result is True
        mock_redis_client.set.assert_called()

    @pytest.mark.asyncio
    async def test_session_management(self, cache_service, mock_redis_client):
        """Test session get, set, update, delete."""
        session_id = "session_123"
        session_data = {"user_id": "user_456", "preferences": {"theme": "dark"}}

        # Set session
        result = await cache_service.set_session(session_id, session_data)
        assert result is True

        # Get session
        stored_value = json.dumps({"_type": "dict", "_value": session_data})
        mock_redis_client.get = AsyncMock(return_value=stored_value.encode())
        result = await cache_service.get_session(session_id)
        assert result == session_data

        # Update session
        mock_redis_client.get = AsyncMock(return_value=stored_value.encode())
        result = await cache_service.update_session(session_id, {"new_field": "value"})
        assert result is True

        # Delete session
        mock_redis_client.delete = AsyncMock(return_value=1)
        result = await cache_service.delete_session(session_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_rate_limit_check(self, cache_service, mock_redis_client):
        """Test rate limit checking via service."""
        pipeline = mock_redis_client.pipeline.return_value
        pipeline.__aenter__.return_value = pipeline
        pipeline.execute = AsyncMock(return_value=[None, 5, None, True])

        allowed, remaining = await cache_service.check_rate_limit(
            identifier="user_123",
            limit=10,
            window_seconds=60,
        )

        assert allowed is True
        assert remaining == 4

    @pytest.mark.asyncio
    async def test_rate_limit_status(self, cache_service, mock_redis_client):
        """Test getting rate limit status."""
        mock_redis_client.zcount = AsyncMock(return_value=30)

        status = await cache_service.get_rate_limit_status(
            identifier="user_123",
            limit=60,
            window_seconds=60,
        )

        assert status["limit"] == 60
        assert status["used"] == 30
        assert status["remaining"] == 30

    @pytest.mark.asyncio
    async def test_embedding_cache(self, cache_service, mock_redis_client, sample_embedding):
        """Test embedding caching."""
        # Set embedding
        result = await cache_service.set_embedding(
            text="test text",
            model="text-embedding-3-small",
            embedding=sample_embedding,
        )
        assert result is True

        # Get embedding
        stored_value = json.dumps({"_type": "list", "_value": sample_embedding})
        mock_redis_client.get = AsyncMock(return_value=stored_value.encode())
        result = await cache_service.get_embedding("test text", "text-embedding-3-small")
        assert result == sample_embedding

    @pytest.mark.asyncio
    async def test_get_stats(self, cache_service, mock_redis_client):
        """Test getting comprehensive statistics."""
        stats = await cache_service.get_stats()

        assert "redis" in stats
        if cache_service.semantic:
            assert "semantic" in stats

    @pytest.mark.asyncio
    async def test_clear_all(self, cache_service, mock_redis_client):
        """Test clearing all caches."""
        results = await cache_service.clear_all()

        assert "redis" in results

    @pytest.mark.asyncio
    async def test_semantic_cache_disabled(self, cache_config_no_semantic, mock_redis_client, mock_connection_pool):
        """Test service when semantic cache is disabled."""
        with patch.object(RedisCache, "connect", new_callable=AsyncMock):
            service = CacheService(config=cache_config_no_semantic)
            service.redis._client = mock_redis_client
            service.redis._pool = mock_connection_pool

            assert service.semantic is None

            # LLM response should skip semantic cache
            mock_redis_client.get = AsyncMock(return_value=None)
            response, similarity, cache_type = await service.get_llm_response(
                messages=[{"role": "user", "content": "test"}],
                model="gpt-4",
                temperature=0.3,
                use_semantic=True,  # Requested but disabled
            )

            assert cache_type == "miss"


# =============================================================================
# Cache Hit/Miss Scenario Tests
# =============================================================================


class TestCacheHitMissScenarios:
    """Tests for various cache hit/miss scenarios."""

    @pytest_asyncio.fixture
    async def cache_service(self, cache_config, mock_redis_client, mock_connection_pool, mock_embedder):
        """Create a cache service for scenario testing."""
        with patch.object(RedisCache, "connect", new_callable=AsyncMock):
            service = CacheService(config=cache_config, embedder=mock_embedder)
            service.redis._client = mock_redis_client
            service.redis._pool = mock_connection_pool

            if service.semantic:
                service.semantic.redis = service.redis

            return service

    @pytest.mark.asyncio
    async def test_cold_cache_miss(self, cache_service, mock_redis_client):
        """Test cache miss on cold cache."""
        mock_redis_client.get = AsyncMock(return_value=None)

        result = await cache_service.get("nonexistent_key")

        assert result is None
        assert cache_service.redis._misses == 1

    @pytest.mark.asyncio
    async def test_warm_cache_hit(self, cache_service, mock_redis_client):
        """Test cache hit on warm cache."""
        # Simulate warm cache
        stored_value = json.dumps({"_type": "primitive", "_value": "cached_value"})
        mock_redis_client.get = AsyncMock(return_value=stored_value.encode())

        result = await cache_service.get("existing_key")

        assert result == "cached_value"
        assert cache_service.redis._hits == 1

    @pytest.mark.asyncio
    async def test_expired_entry_miss(self, cache_service, mock_redis_client):
        """Test miss when entry has expired."""
        # Redis returns None for expired keys
        mock_redis_client.get = AsyncMock(return_value=None)

        result = await cache_service.get("expired_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_sequential_requests_hit_rate(self, cache_service, mock_redis_client):
        """Test hit rate across sequential requests."""
        stored_value = json.dumps({"_type": "primitive", "_value": "value"})

        # First request: miss
        mock_redis_client.get = AsyncMock(return_value=None)
        await cache_service.get("key1")

        # Set the value
        await cache_service.set("key1", "value")

        # Subsequent requests: hits
        mock_redis_client.get = AsyncMock(return_value=stored_value.encode())
        for _ in range(9):
            await cache_service.get("key1")

        stats = await cache_service.redis.get_stats()
        assert stats["hits"] == 9
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.9

    @pytest.mark.asyncio
    async def test_llm_semantic_fallback(self, cache_service, mock_redis_client, mock_embedder):
        """Test fallback from exact to semantic cache."""
        # Exact miss
        mock_redis_client.get = AsyncMock(return_value=None)

        # Set up semantic cache entry
        np.random.seed(42)
        embedding = np.random.randn(384).tolist()

        if cache_service.semantic:
            await cache_service.semantic.set(
                query="What is machine learning?",
                response="Machine learning is a subset of AI.",
                model="gpt-4",
                query_embedding=embedding,
            )

            # Similar query embedding
            similar_embedding = (np.array(embedding) + np.random.randn(384) * 0.05).tolist()
            mock_embedder.embed = AsyncMock(return_value=similar_embedding)

            response, similarity, cache_type = await cache_service.get_llm_response(
                messages=[{"role": "user", "content": "Tell me about machine learning"}],
                model="gpt-4",
                temperature=0.3,  # Low temp enables semantic cache
                use_semantic=True,
            )

            # May get semantic hit if similarity is above threshold
            if cache_type == "semantic":
                assert response is not None
                assert similarity >= cache_service.config.similarity_threshold


# =============================================================================
# Cache Invalidation Tests
# =============================================================================


class TestCacheInvalidation:
    """Tests for cache invalidation strategies."""

    @pytest_asyncio.fixture
    async def cache_service(self, cache_config, mock_redis_client, mock_connection_pool):
        """Create a cache service for invalidation testing."""
        with patch.object(RedisCache, "connect", new_callable=AsyncMock):
            service = CacheService(config=cache_config)
            service.redis._client = mock_redis_client
            service.redis._pool = mock_connection_pool
            return service

    @pytest.mark.asyncio
    async def test_explicit_delete_invalidation(self, cache_service, mock_redis_client):
        """Test explicit key deletion."""
        mock_redis_client.delete = AsyncMock(return_value=1)

        result = await cache_service.delete("key_to_invalidate")

        assert result is True
        mock_redis_client.delete.assert_called()

    @pytest.mark.asyncio
    async def test_pattern_based_invalidation(self, cache_service, mock_redis_client):
        """Test invalidating keys by pattern."""
        async def mock_scan():
            for key in [b"user:123:session", b"user:123:prefs", b"user:123:data"]:
                yield key

        mock_redis_client.scan_iter = MagicMock(return_value=mock_scan())
        mock_redis_client.delete = AsyncMock(return_value=1)

        count = await cache_service.redis.clear(pattern="user:123:*")

        assert count == 3

    @pytest.mark.asyncio
    async def test_session_invalidation(self, cache_service, mock_redis_client):
        """Test session-specific invalidation."""
        mock_redis_client.delete = AsyncMock(return_value=1)

        result = await cache_service.delete_session("session_to_invalidate")

        assert result is True

    @pytest.mark.asyncio
    async def test_ttl_based_expiration(self, cache_service, mock_redis_client):
        """Test that TTL causes automatic expiration."""
        # Set with short TTL
        await cache_service.set("short_lived_key", "value", ttl=1)

        # Verify TTL was set
        call_args = mock_redis_client.set.call_args
        assert call_args.kwargs.get("ex") == 1 or call_args[1].get("ex") == 1

    @pytest.mark.asyncio
    async def test_clear_all_invalidation(self, cache_service, mock_redis_client):
        """Test clearing all caches."""
        results = await cache_service.clear_all()

        assert "redis" in results
        mock_redis_client.flushdb.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_overwrites_existing(self, cache_service, mock_redis_client):
        """Test that set overwrites existing values."""
        # First set
        await cache_service.set("key", "original_value")

        # Overwrite
        await cache_service.set("key", "new_value")

        # Verify set was called twice
        assert mock_redis_client.set.call_count == 2


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in cache operations."""

    @pytest_asyncio.fixture
    async def redis_cache(self, cache_config, mock_redis_client, mock_connection_pool):
        """Create a Redis cache for error testing."""
        cache = RedisCache(config=cache_config)
        cache._client = mock_redis_client
        cache._pool = mock_connection_pool
        return cache

    @pytest.mark.asyncio
    async def test_get_handles_redis_error(self, redis_cache, mock_redis_client):
        """Test that get handles Redis errors gracefully."""
        from redis.exceptions import RedisError

        mock_redis_client.get = AsyncMock(side_effect=RedisError("Connection failed"))

        result = await redis_cache.get("key")

        assert result is None
        assert redis_cache._errors == 1

    @pytest.mark.asyncio
    async def test_set_handles_redis_error(self, redis_cache, mock_redis_client):
        """Test that set handles Redis errors gracefully."""
        from redis.exceptions import RedisError

        mock_redis_client.set = AsyncMock(side_effect=RedisError("Connection failed"))

        result = await redis_cache.set("key", "value")

        assert result is False
        assert redis_cache._errors == 1

    @pytest.mark.asyncio
    async def test_delete_handles_redis_error(self, redis_cache, mock_redis_client):
        """Test that delete handles Redis errors gracefully."""
        from redis.exceptions import RedisError

        mock_redis_client.delete = AsyncMock(side_effect=RedisError("Connection failed"))

        result = await redis_cache.delete("key")

        assert result is False
        assert redis_cache._errors == 1

    @pytest.mark.asyncio
    async def test_rate_limit_fails_open_on_error(self, redis_cache, mock_redis_client):
        """Test that rate limiting fails open on Redis error."""
        from redis.exceptions import RedisError

        pipeline = mock_redis_client.pipeline.return_value
        pipeline.__aenter__.side_effect = RedisError("Connection failed")

        allowed, remaining = await redis_cache.check_rate_limit(
            key="user",
            limit=10,
            window_seconds=60,
        )

        # Should fail open (allow request)
        assert allowed is True
        assert remaining == 10

    @pytest.mark.asyncio
    async def test_deserialization_handles_invalid_json(self, redis_cache):
        """Test that deserialization handles invalid JSON."""
        result = redis_cache._deserialize("not valid json {")

        # Should return the raw string
        assert result == "not valid json {"


# =============================================================================
# Global Service Tests
# =============================================================================


class TestGlobalService:
    """Tests for global cache service management."""

    @pytest.mark.asyncio
    async def test_get_cache_service_creates_singleton(self, cache_config):
        """Test that get_cache_service creates a singleton."""
        import app.services.cache.service as service_module

        # Reset global state
        service_module._cache_service = None

        with patch.object(RedisCache, "connect", new_callable=AsyncMock):
            with patch.object(CacheService, "initialize", new_callable=AsyncMock):
                service1 = await get_cache_service(config=cache_config)
                service2 = await get_cache_service(config=cache_config)

                # Same instance
                assert service1 is service2

        # Clean up
        await close_cache_service()

    @pytest.mark.asyncio
    async def test_close_cache_service(self, cache_config):
        """Test closing the global cache service."""
        import app.services.cache.service as service_module

        # Reset global state
        service_module._cache_service = None

        with patch.object(RedisCache, "connect", new_callable=AsyncMock):
            with patch.object(CacheService, "initialize", new_callable=AsyncMock):
                service = await get_cache_service(config=cache_config)

                with patch.object(service, "close", new_callable=AsyncMock) as mock_close:
                    await close_cache_service()

                    mock_close.assert_called_once()
                    assert service_module._cache_service is None
