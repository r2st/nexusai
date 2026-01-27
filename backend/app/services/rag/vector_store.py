"""
Vector Store

Abstraction for vector databases (Qdrant, Pinecone, pgvector).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import logging
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorStoreType(str, Enum):
    """Supported vector stores."""
    QDRANT = "qdrant"
    PINECONE = "pinecone"
    PGVECTOR = "pgvector"
    CHROMA = "chroma"
    WEAVIATE = "weaviate"


@dataclass
class Document:
    """A document to be indexed."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Source tracking
    source_type: str = "unknown"  # code, doc, ticket, incident
    source_id: str = ""
    source_url: Optional[str] = None
    
    # Tenant isolation
    tenant_id: str = ""
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SearchResult:
    """A search result with relevance score."""
    document: Document
    score: float
    highlights: Optional[List[str]] = None
    rerank_score: Optional[float] = None


@dataclass
class SearchQuery:
    """Search query parameters."""
    query: str
    embedding: Optional[List[float]] = None
    top_k: int = 10
    score_threshold: float = 0.0
    
    # Filters
    tenant_id: Optional[str] = None
    source_types: Optional[List[str]] = None
    metadata_filters: Dict[str, Any] = field(default_factory=dict)
    
    # Hybrid search
    use_keyword: bool = True
    use_semantic: bool = True
    keyword_weight: float = 0.3
    semantic_weight: float = 0.7


class VectorStoreBackend(ABC):
    """Abstract vector store backend."""
    
    @abstractmethod
    async def create_collection(
        self,
        name: str,
        dimensions: int,
        **kwargs,
    ) -> None:
        pass
    
    @abstractmethod
    async def delete_collection(self, name: str) -> None:
        pass
    
    @abstractmethod
    async def upsert(
        self,
        collection: str,
        documents: List[Document],
    ) -> int:
        pass
    
    @abstractmethod
    async def delete(
        self,
        collection: str,
        ids: List[str],
    ) -> int:
        pass
    
    @abstractmethod
    async def search(
        self,
        collection: str,
        query: SearchQuery,
    ) -> List[SearchResult]:
        pass


class QdrantBackend(VectorStoreBackend):
    """Qdrant vector store backend."""

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.url = url or settings.QDRANT_URL
        self.api_key = api_key or settings.QDRANT_API_KEY
        self._client = None
    
    async def _get_client(self):
        if self._client is None:
            from qdrant_client import AsyncQdrantClient
            self._client = AsyncQdrantClient(
                url=self.url,
                api_key=self.api_key,
            )
        return self._client
    
    async def create_collection(
        self,
        name: str,
        dimensions: int,
        **kwargs,
    ) -> None:
        from qdrant_client.models import Distance, VectorParams
        
        client = await self._get_client()
        
        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=dimensions,
                distance=Distance.COSINE,
            ),
        )
        logger.info(f"Created Qdrant collection: {name}")
    
    async def delete_collection(self, name: str) -> None:
        client = await self._get_client()
        await client.delete_collection(name)
        logger.info(f"Deleted Qdrant collection: {name}")
    
    async def upsert(
        self,
        collection: str,
        documents: List[Document],
    ) -> int:
        from qdrant_client.models import PointStruct
        
        client = await self._get_client()
        
        points = [
            PointStruct(
                id=doc.id,
                vector=doc.embedding,
                payload={
                    "content": doc.content,
                    "source_type": doc.source_type,
                    "source_id": doc.source_id,
                    "source_url": doc.source_url,
                    "tenant_id": doc.tenant_id,
                    "created_at": doc.created_at.isoformat(),
                    **doc.metadata,
                },
            )
            for doc in documents
            if doc.embedding is not None
        ]
        
        if points:
            await client.upsert(
                collection_name=collection,
                points=points,
            )
        
        return len(points)
    
    async def delete(
        self,
        collection: str,
        ids: List[str],
    ) -> int:
        from qdrant_client.models import PointIdsList
        
        client = await self._get_client()
        
        await client.delete(
            collection_name=collection,
            points_selector=PointIdsList(points=ids),
        )
        
        return len(ids)
    
    async def search(
        self,
        collection: str,
        query: SearchQuery,
    ) -> List[SearchResult]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        client = await self._get_client()
        
        # Build filter
        conditions = []
        
        if query.tenant_id:
            conditions.append(
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=query.tenant_id),
                )
            )
        
        if query.source_types:
            conditions.append(
                FieldCondition(
                    key="source_type",
                    match=MatchValue(any=query.source_types),
                )
            )
        
        for key, value in query.metadata_filters.items():
            conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value),
                )
            )
        
        filter_obj = Filter(must=conditions) if conditions else None
        
        # Perform search
        results = await client.search(
            collection_name=collection,
            query_vector=query.embedding,
            limit=query.top_k,
            score_threshold=query.score_threshold,
            query_filter=filter_obj,
        )
        
        return [
            SearchResult(
                document=Document(
                    id=str(r.id),
                    content=r.payload.get("content", ""),
                    metadata={
                        k: v for k, v in r.payload.items()
                        if k not in ["content", "source_type", "source_id", "tenant_id"]
                    },
                    source_type=r.payload.get("source_type", "unknown"),
                    source_id=r.payload.get("source_id", ""),
                    source_url=r.payload.get("source_url"),
                    tenant_id=r.payload.get("tenant_id", ""),
                ),
                score=r.score,
            )
            for r in results
        ]


class VectorStore:
    """
    High-level vector store interface.
    
    Features:
    - Multi-backend support
    - Collection management
    - Batch operations
    - Hybrid search (when supported)
    """
    
    def __init__(
        self,
        backend: VectorStoreBackend,
        default_collection: str = "documents",
    ):
        self.backend = backend
        self.default_collection = default_collection
    
    async def create_collection(
        self,
        name: str,
        dimensions: int,
        **kwargs,
    ) -> None:
        """Create a new collection."""
        await self.backend.create_collection(name, dimensions, **kwargs)
    
    async def delete_collection(self, name: str) -> None:
        """Delete a collection."""
        await self.backend.delete_collection(name)
    
    async def index_documents(
        self,
        documents: List[Document],
        collection: Optional[str] = None,
    ) -> int:
        """Index documents into the vector store."""
        return await self.backend.upsert(
            collection or self.default_collection,
            documents,
        )
    
    async def delete_documents(
        self,
        ids: List[str],
        collection: Optional[str] = None,
    ) -> int:
        """Delete documents by ID."""
        return await self.backend.delete(
            collection or self.default_collection,
            ids,
        )
    
    async def search(
        self,
        query: SearchQuery,
        collection: Optional[str] = None,
    ) -> List[SearchResult]:
        """Search for similar documents."""
        return await self.backend.search(
            collection or self.default_collection,
            query,
        )
    
    async def similarity_search(
        self,
        embedding: List[float],
        tenant_id: str,
        top_k: int = 10,
        source_types: Optional[List[str]] = None,
        collection: Optional[str] = None,
    ) -> List[SearchResult]:
        """Simple similarity search."""
        query = SearchQuery(
            query="",
            embedding=embedding,
            top_k=top_k,
            tenant_id=tenant_id,
            source_types=source_types,
        )
        return await self.search(query, collection)
