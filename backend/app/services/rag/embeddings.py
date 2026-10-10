"""
Embeddings Service

Multi-model embedding generation for semantic search.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional
import hashlib
import logging

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingModel(str, Enum):
    """Supported embedding models."""
    OPENAI_ADA_002 = "text-embedding-ada-002"
    OPENAI_3_SMALL = "text-embedding-3-small"
    OPENAI_3_LARGE = "text-embedding-3-large"
    COHERE_ENGLISH = "embed-english-v3.0"
    COHERE_MULTILINGUAL = "embed-multilingual-v3.0"
    VOYAGE_CODE = "voyage-code-2"
    VOYAGE_LARGE = "voyage-large-2"
    LOCAL_CODEBERT = "microsoft/codebert-base"
    LOCAL_INSTRUCTOR = "hkunlp/instructor-xl"


@dataclass
class EmbeddingResult:
    """Result of an embedding operation."""
    text: str
    embedding: List[float]
    model: str
    dimensions: int
    tokens_used: int
    cache_hit: bool = False


class EmbeddingProvider(ABC):
    """Abstract embedding provider."""
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def dimensions(self) -> int:
        pass
    
    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embeddings provider."""
    
    def __init__(
        self,
        api_key: str,
        model: EmbeddingModel = EmbeddingModel.OPENAI_3_SMALL,
    ):
        self.api_key = api_key
        self.model = model
        self._dimensions = {
            EmbeddingModel.OPENAI_ADA_002: 1536,
            EmbeddingModel.OPENAI_3_SMALL: 1536,
            EmbeddingModel.OPENAI_3_LARGE: 3072,
        }
    
    @property
    def model_name(self) -> str:
        return self.model.value
    
    @property
    def dimensions(self) -> int:
        return self._dimensions.get(self.model, 1536)
    
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        try:
            import openai
            
            client = openai.AsyncOpenAI(api_key=self.api_key)
            response = await client.embeddings.create(
                model=self.model.value,
                input=texts,
            )
            
            return [item.embedding for item in response.data]
            
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise


class VoyageEmbeddingProvider(EmbeddingProvider):
    """Voyage AI embeddings - optimized for code."""
    
    def __init__(
        self,
        api_key: str,
        model: EmbeddingModel = EmbeddingModel.VOYAGE_CODE,
    ):
        self.api_key = api_key
        self.model = model
    
    @property
    def model_name(self) -> str:
        return self.model.value
    
    @property
    def dimensions(self) -> int:
        return 1024
    
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Voyage API."""
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.voyageai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model.value,
                        "input": texts,
                        "input_type": "document",
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                return [item["embedding"] for item in data["data"]]
                
        except Exception as e:
            logger.error(f"Voyage embedding error: {e}")
            raise


class EmbeddingsService:
    """
    Service for generating and caching embeddings.
    
    Features:
    - Multi-model support
    - Automatic batching
    - Embedding cache
    - Fallback providers
    """
    
    def __init__(
        self,
        primary_provider: EmbeddingProvider,
        fallback_provider: Optional[EmbeddingProvider] = None,
        cache_backend: Optional[Any] = None,
        batch_size: int = 100,
    ):
        self.primary = primary_provider
        self.fallback = fallback_provider
        self.cache = cache_backend
        self.batch_size = batch_size
    
    @property
    def model_name(self) -> str:
        return self.primary.model_name
    
    @property
    def dimensions(self) -> int:
        return self.primary.dimensions
    
    async def embed_single(self, text: str) -> EmbeddingResult:
        """Embed a single text."""
        results = await self.embed_batch([text])
        return results[0]
    
    async def embed_batch(
        self,
        texts: List[str],
        use_cache: bool = True,
    ) -> List[EmbeddingResult]:
        """Embed multiple texts with batching and caching."""
        if not texts:
            return []
        
        results: List[Optional[EmbeddingResult]] = [None] * len(texts)
        texts_to_embed: List[tuple[int, str]] = []
        
        # Check cache first
        if use_cache and self.cache:
            for i, text in enumerate(texts):
                cached = await self._get_cached(text)
                if cached:
                    results[i] = cached
                else:
                    texts_to_embed.append((i, text))
        else:
            texts_to_embed = list(enumerate(texts))
        
        # Batch embed remaining texts
        if texts_to_embed:
            indices, uncached_texts = zip(*texts_to_embed)
            embeddings = await self._embed_with_fallback(list(uncached_texts))
            
            for idx, text, embedding in zip(indices, uncached_texts, embeddings):
                result = EmbeddingResult(
                    text=text,
                    embedding=embedding,
                    model=self.primary.model_name,
                    dimensions=len(embedding),
                    tokens_used=self._estimate_tokens(text),
                    cache_hit=False,
                )
                results[idx] = result
                
                # Cache the result
                if use_cache and self.cache:
                    await self._set_cached(text, result)
        
        return [r for r in results if r is not None]
    
    async def _embed_with_fallback(self, texts: List[str]) -> List[List[float]]:
        """Embed with automatic fallback."""
        try:
            return await self._batch_embed(self.primary, texts)
        except Exception as e:
            logger.warning(f"Primary provider failed: {e}")
            if self.fallback:
                logger.info("Falling back to secondary provider")
                return await self._batch_embed(self.fallback, texts)
            raise
    
    async def _batch_embed(
        self,
        provider: EmbeddingProvider,
        texts: List[str],
    ) -> List[List[float]]:
        """Embed texts in batches."""
        all_embeddings: List[List[float]] = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            embeddings = await provider.embed(batch)
            all_embeddings.extend(embeddings)
        
        return all_embeddings
    
    def _cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        content = f"{self.primary.model_name}:{text}"
        return f"emb:{hashlib.sha256(content.encode()).hexdigest()[:32]}"
    
    async def _get_cached(self, text: str) -> Optional[EmbeddingResult]:
        """Get cached embedding."""
        if not self.cache:
            return None
        
        try:
            key = self._cache_key(text)
            data = await self.cache.get(key)
            if data:
                return EmbeddingResult(
                    text=text,
                    embedding=data["embedding"],
                    model=data["model"],
                    dimensions=len(data["embedding"]),
                    tokens_used=data.get("tokens", 0),
                    cache_hit=True,
                )
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        
        return None
    
    async def _set_cached(self, text: str, result: EmbeddingResult) -> None:
        """Cache embedding result."""
        if not self.cache:
            return
        
        try:
            key = self._cache_key(text)
            await self.cache.set(
                key,
                {
                    "embedding": result.embedding,
                    "model": result.model,
                    "tokens": result.tokens_used,
                },
                ttl=86400 * 7,  # 7 days
            )
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation."""
        return len(text) // 4

    def cosine_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """Calculate cosine similarity between two embeddings."""
        a = np.array(embedding1)
        b = np.array(embedding2)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


_embeddings_service: Optional[EmbeddingsService] = None


async def get_embeddings_service() -> Optional[EmbeddingsService]:
    """Get or create the global EmbeddingsService instance.

    Returns None if no OpenAI API key is configured.
    """
    global _embeddings_service

    if _embeddings_service is not None:
        return _embeddings_service

    from app.core.config import settings

    if not settings.OPENAI_API_KEY:
        return None

    provider = OpenAIEmbeddingProvider(
        api_key=settings.OPENAI_API_KEY,
        model=EmbeddingModel(settings.EMBEDDING_MODEL),
    )
    _embeddings_service = EmbeddingsService(primary_provider=provider)
    return _embeddings_service
