"""RAG data models."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Supported document types."""

    MARKDOWN = "markdown"
    PDF = "pdf"
    TEXT = "text"
    HTML = "html"
    CODE = "code"
    DOCX = "docx"
    CSV = "csv"
    JSON = "json"


class DocumentMetadata(BaseModel):
    """Metadata for a document."""

    title: str | None = None
    source: str | None = None  # File path or URL
    source_type: DocumentType = DocumentType.TEXT
    author: str | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    language: str = "en"
    tags: list[str] = Field(default_factory=list)
    custom: dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """A document for RAG indexing."""

    id: UUID = Field(default_factory=uuid4)
    content: str
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Processing state
    chunk_count: int = 0
    token_count: int = 0
    indexed: bool = False
    index_error: str | None = None


class DocumentChunk(BaseModel):
    """A chunk of a document with embedding."""

    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    content: str
    embedding: list[float] | None = None

    # Position in document
    chunk_index: int = 0
    start_char: int = 0
    end_char: int = 0

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    token_count: int = 0

    # For code chunks
    language: str | None = None
    function_name: str | None = None
    class_name: str | None = None


class RAGQuery(BaseModel):
    """A query to the RAG system."""

    query: str
    top_k: int = 5
    similarity_threshold: float = 0.7
    rerank: bool = True
    rerank_top_k: int = 3

    # Filters
    document_ids: list[UUID] | None = None
    tags: list[str] | None = None
    source_type: DocumentType | None = None
    metadata_filter: dict[str, Any] | None = None

    # Search mode
    hybrid_search: bool = True  # Combine semantic + keyword
    keyword_weight: float = 0.3  # Weight for keyword search

    # Context options
    include_context: bool = True  # Include surrounding chunks
    context_window: int = 1  # Chunks before/after


class RetrievalResult(BaseModel):
    """A single retrieval result."""

    chunk: DocumentChunk
    score: float  # Similarity score
    rerank_score: float | None = None
    combined_score: float | None = None

    # Source info
    document_title: str | None = None
    document_source: str | None = None


class RAGResult(BaseModel):
    """Complete RAG query result."""

    query: str
    results: list[RetrievalResult] = Field(default_factory=list)

    # Assembled context
    context: str | None = None
    context_token_count: int = 0

    # Metrics
    retrieval_time_ms: float = 0.0
    rerank_time_ms: float = 0.0
    total_time_ms: float = 0.0

    # For citations
    sources: list[dict[str, Any]] = Field(default_factory=list)


class EmbeddingRequest(BaseModel):
    """Request for embedding generation."""

    texts: list[str]
    model: str = "text-embedding-3-small"
    batch_size: int = 100


class EmbeddingResult(BaseModel):
    """Result of embedding generation."""

    embeddings: list[list[float]]
    model: str
    dimensions: int
    total_tokens: int = 0
