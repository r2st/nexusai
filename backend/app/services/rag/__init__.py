"""
RAG (Retrieval-Augmented Generation) Service

Enterprise-grade RAG system for code intelligence:
- Multi-source indexing (code, docs, tickets, incidents)
- Hybrid search (keyword + semantic)
- Cross-encoder reranking
- Tenant isolation
"""

from .embeddings import EmbeddingsService, EmbeddingModel
from .vector_store import VectorStore, SearchResult
from .chunking_strategy import CodeChunker, ChunkingStrategy
from .hybrid_retrieval import HybridRetriever, RetrievalConfig
from .indexers import CodeIndexer, DocumentIndexer, TicketIndexer
from .context_builder import ContextBuilder, ContextConfig

__all__ = [
    # Embeddings
    "EmbeddingsService",
    "EmbeddingModel",
    # Vector store
    "VectorStore",
    "SearchResult",
    # Chunking
    "CodeChunker",
    "ChunkingStrategy",
    # Retrieval
    "HybridRetriever",
    "RetrievalConfig",
    # Indexers
    "CodeIndexer",
    "DocumentIndexer",
    "TicketIndexer",
    # Context
    "ContextBuilder",
    "ContextConfig",
]
