"""Embedding generation services."""

from abc import ABC, abstractmethod

import structlog

from app.services.rag.config import EmbeddingConfig

logger = structlog.get_logger()


class BaseEmbedder(ABC):
    """Base class for embedding providers."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a single query."""
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Get embedding dimensions."""
        pass


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI embeddings."""

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self._dimensions = config.dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using OpenAI."""
        import httpx
        from app.core.config import settings

        embeddings = []

        # Process in batches
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.config.model,
                        "input": batch,
                    },
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()

                for item in data["data"]:
                    embeddings.append(item["embedding"])

        return embeddings

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query."""
        result = await self.embed([query])
        return result[0]

    @property
    def dimensions(self) -> int:
        return self._dimensions


class OllamaEmbedder(BaseEmbedder):
    """Ollama local embeddings."""

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self._dimensions = 768  # nomic-embed-text default

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Ollama."""
        import httpx

        embeddings = []

        async with httpx.AsyncClient() as client:
            for text in texts:
                response = await client.post(
                    f"{self.config.ollama_url}/api/embeddings",
                    json={
                        "model": self.config.ollama_model,
                        "prompt": text,
                    },
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embedding"])

        return embeddings

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query."""
        result = await self.embed([query])
        return result[0]

    @property
    def dimensions(self) -> int:
        return self._dimensions


def get_embedder(config: EmbeddingConfig) -> BaseEmbedder:
    """Get embedder based on configuration."""
    if config.provider == "openai":
        return OpenAIEmbedder(config)
    elif config.provider == "ollama":
        return OllamaEmbedder(config)
    else:
        raise ValueError(f"Unknown embedding provider: {config.provider}")
