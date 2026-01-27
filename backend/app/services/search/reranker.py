"""Result reranking service with Jina and other providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from app.core.config import settings
from app.services.search.web import SearchResult

logger = structlog.get_logger()


@dataclass
class RerankResult:
    """Result after reranking."""

    index: int
    score: float
    original_result: SearchResult


class Reranker(ABC):
    """Base class for rerankers."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int | None = None,
    ) -> list[RerankResult]:
        """Rerank search results based on relevance to query."""
        pass


class JinaReranker(Reranker):
    """Jina AI reranker."""

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        model: str = "jina-reranker-v2-base-multilingual",
    ):
        self.api_key = api_key or settings.JINA_API_KEY
        self.api_url = api_url or "https://api.jina.ai/v1/rerank"
        self.model = model

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int | None = None,
    ) -> list[RerankResult]:
        """Rerank using Jina API."""
        if not self.api_key:
            logger.warning("Jina API key not configured, returning original order")
            return [
                RerankResult(index=i, score=1.0 - (i * 0.1), original_result=r)
                for i, r in enumerate(results)
            ]

        # Prepare documents
        documents = [
            {"text": f"{r.title}\n{r.snippet}"} for r in results
        ]

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.api_url,
                    json={
                        "model": self.model,
                        "query": query,
                        "documents": documents,
                        "top_n": top_k or len(results),
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                reranked = []
                for item in data.get("results", []):
                    idx = item.get("index", 0)
                    reranked.append(RerankResult(
                        index=idx,
                        score=item.get("relevance_score", 0.0),
                        original_result=results[idx],
                    ))

                # Sort by score descending
                reranked.sort(key=lambda x: x.score, reverse=True)

                return reranked

            except Exception as e:
                logger.error("Jina reranking failed", error=str(e))
                # Return original order
                return [
                    RerankResult(index=i, score=1.0 - (i * 0.1), original_result=r)
                    for i, r in enumerate(results)
                ]


class CohereReranker(Reranker):
    """Cohere reranker."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "rerank-english-v3.0",
    ):
        self.api_key = api_key or settings.COHERE_API_KEY
        self.model = model
        self.api_url = "https://api.cohere.ai/v1/rerank"

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int | None = None,
    ) -> list[RerankResult]:
        """Rerank using Cohere API."""
        if not self.api_key:
            logger.warning("Cohere API key not configured")
            return [
                RerankResult(index=i, score=1.0 - (i * 0.1), original_result=r)
                for i, r in enumerate(results)
            ]

        documents = [f"{r.title}\n{r.snippet}" for r in results]

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.api_url,
                    json={
                        "model": self.model,
                        "query": query,
                        "documents": documents,
                        "top_n": top_k or len(results),
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                reranked = []
                for item in data.get("results", []):
                    idx = item.get("index", 0)
                    reranked.append(RerankResult(
                        index=idx,
                        score=item.get("relevance_score", 0.0),
                        original_result=results[idx],
                    ))

                reranked.sort(key=lambda x: x.score, reverse=True)
                return reranked

            except Exception as e:
                logger.error("Cohere reranking failed", error=str(e))
                return [
                    RerankResult(index=i, score=1.0 - (i * 0.1), original_result=r)
                    for i, r in enumerate(results)
                ]


class CrossEncoderReranker(Reranker):
    """Local cross-encoder reranker using sentence-transformers."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        """Lazy load the model."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
            except ImportError:
                logger.error("sentence-transformers not installed")
                raise

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int | None = None,
    ) -> list[RerankResult]:
        """Rerank using local cross-encoder."""
        import asyncio

        try:
            self._load_model()

            # Prepare pairs
            pairs = [(query, f"{r.title}\n{r.snippet}") for r in results]

            # Run in executor to not block
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(
                None, self._model.predict, pairs
            )

            # Create reranked results
            reranked = [
                RerankResult(index=i, score=float(score), original_result=r)
                for i, (r, score) in enumerate(zip(results, scores))
            ]

            # Sort by score
            reranked.sort(key=lambda x: x.score, reverse=True)

            if top_k:
                reranked = reranked[:top_k]

            return reranked

        except Exception as e:
            logger.error("Cross-encoder reranking failed", error=str(e))
            return [
                RerankResult(index=i, score=1.0 - (i * 0.1), original_result=r)
                for i, r in enumerate(results)
            ]


# Factory for creating rerankers
def get_reranker(provider: str = "jina") -> Reranker:
    """Get a reranker instance."""
    if provider == "jina":
        return JinaReranker()
    elif provider == "cohere":
        return CohereReranker()
    elif provider == "local":
        return CrossEncoderReranker()
    else:
        return JinaReranker()
