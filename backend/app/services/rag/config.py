"""RAG pipeline configuration."""

from pydantic import BaseModel, Field


class ChunkingConfig(BaseModel):
    """Configuration for document chunking."""

    chunk_size: int = 512  # Target tokens per chunk
    chunk_overlap: int = 50  # Overlap between chunks
    min_chunk_size: int = 100  # Minimum chunk size
    max_chunk_size: int = 1024  # Maximum chunk size

    # Chunking strategies
    respect_sentence_boundaries: bool = True
    respect_paragraph_boundaries: bool = True
    code_aware_chunking: bool = True  # For code files


class EmbeddingConfig(BaseModel):
    """Configuration for embeddings."""

    provider: str = "openai"  # openai, ollama
    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    batch_size: int = 100

    # Ollama settings - URL should come from environment
    ollama_model: str = "nomic-embed-text"
    ollama_url: str = ""  # Set via settings.OLLAMA_BASE_URL


class RetrievalConfig(BaseModel):
    """Configuration for retrieval."""

    default_top_k: int = 10
    similarity_threshold: float = 0.7

    # Hybrid search
    enable_hybrid: bool = True
    semantic_weight: float = 0.7
    keyword_weight: float = 0.3

    # Diversity
    enable_mmr: bool = True  # Maximal Marginal Relevance
    mmr_lambda: float = 0.5


class RerankConfig(BaseModel):
    """Configuration for reranking."""

    enabled: bool = True
    provider: str = "cross-encoder"  # cross-encoder, cohere
    model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_k: int = 5

    # Cohere settings
    cohere_model: str = "rerank-english-v2.0"


class ContextConfig(BaseModel):
    """Configuration for context assembly."""

    max_tokens: int = 8000  # Max tokens for context
    include_metadata: bool = True
    include_sources: bool = True
    deduplicate: bool = True


class RAGConfig(BaseModel):
    """Complete RAG configuration."""

    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    rerank: RerankConfig = Field(default_factory=RerankConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)

    # Database
    use_pgvector: bool = True
    vector_table: str = "document_chunks"


def get_rag_config() -> RAGConfig:
    """Get RAG configuration."""
    from app.core.config import settings

    config = RAGConfig()

    # Configure embedding provider based on available API keys
    if getattr(settings, "OPENAI_API_KEY", None):
        config.embedding.provider = "openai"
        config.embedding.model = "text-embedding-3-small"
    else:
        # Fall back to Ollama
        config.embedding.provider = "ollama"
        config.embedding.model = "nomic-embed-text"
        config.embedding.ollama_url = settings.OLLAMA_BASE_URL

    return config
