"""Cache configuration."""

import os
from dataclasses import dataclass, field

from app.core.config import settings


@dataclass
class CacheConfig:
    """Configuration for cache services."""

    # Redis configuration - uses settings which reads from environment
    redis_url: str = field(
        default_factory=lambda: settings.REDIS_URL
    )
    redis_max_connections: int = 10
    redis_socket_timeout: float = 5.0
    redis_retry_on_timeout: bool = True

    # Cache TTLs (in seconds)
    default_ttl: int = 3600  # 1 hour
    session_ttl: int = 86400  # 24 hours
    llm_response_ttl: int = 7200  # 2 hours
    embedding_ttl: int = 86400 * 7  # 7 days

    # Semantic cache configuration
    enable_semantic_cache: bool = True
    similarity_threshold: float = 0.85  # Cosine similarity threshold
    semantic_cache_ttl: int = 7200  # 2 hours
    max_semantic_entries: int = 10000

    # Embedding configuration for semantic cache
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # Cache key prefixes
    prefix_session: str = "session:"
    prefix_llm: str = "llm:"
    prefix_embedding: str = "embedding:"
    prefix_semantic: str = "semantic:"
    prefix_rate_limit: str = "rate:"

    # Warming configuration
    enable_cache_warming: bool = False
    warm_common_queries: list[str] = field(default_factory=list)

    # Metrics
    enable_cache_metrics: bool = True


def get_cache_config() -> CacheConfig:
    """Get cache configuration from environment.

    All Redis settings come from the central settings object.
    """
    return CacheConfig(
        redis_url=settings.REDIS_URL,
        enable_semantic_cache=os.getenv("ENABLE_SEMANTIC_CACHE", "true").lower() == "true",
        similarity_threshold=float(os.getenv("SEMANTIC_SIMILARITY_THRESHOLD", "0.85")),
        default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "3600")),
        llm_response_ttl=int(os.getenv("CACHE_LLM_TTL", "7200")),
    )
