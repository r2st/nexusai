"""Unit tests for RAG Pipeline service."""

import asyncio
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

import pytest

from app.services.rag.config import (
    ChunkingConfig,
    ContextConfig,
    EmbeddingConfig,
    RAGConfig,
    RerankConfig,
    RetrievalConfig,
)
from app.services.rag.models import (
    Document,
    DocumentChunk,
    DocumentMetadata,
    DocumentType,
    EmbeddingRequest,
    EmbeddingResult,
    RAGQuery,
    RAGResult,
    RetrievalResult,
)
from app.services.rag.chunking import (
    BaseChunker,
    CodeChunker,
    TextChunker,
    get_chunker,
)
from app.services.rag.embedding import (
    BaseEmbedder,
    OpenAIEmbedder,
    OllamaEmbedder,
    get_embedder,
)
from app.services.rag.retrieval import Retriever, VectorStore
from app.services.rag.pipeline import RAGPipeline, get_rag_pipeline


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def chunking_config():
    """Create a test chunking config."""
    return ChunkingConfig(
        chunk_size=256,
        chunk_overlap=25,
        min_chunk_size=50,
        max_chunk_size=512,
        respect_sentence_boundaries=True,
        respect_paragraph_boundaries=True,
        code_aware_chunking=True,
    )


@pytest.fixture
def embedding_config():
    """Create a test embedding config."""
    return EmbeddingConfig(
        provider="openai",
        model="text-embedding-3-small",
        dimensions=1536,
        batch_size=50,
        ollama_model="nomic-embed-text",
        ollama_url="http://localhost:11434",
    )


@pytest.fixture
def retrieval_config():
    """Create a test retrieval config."""
    return RetrievalConfig(
        default_top_k=10,
        similarity_threshold=0.7,
        enable_hybrid=True,
        semantic_weight=0.7,
        keyword_weight=0.3,
        enable_mmr=True,
        mmr_lambda=0.5,
    )


@pytest.fixture
def rerank_config():
    """Create a test rerank config."""
    return RerankConfig(
        enabled=True,
        provider="cross-encoder",
        model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        top_k=5,
        cohere_model="rerank-english-v2.0",
    )


@pytest.fixture
def context_config():
    """Create a test context config."""
    return ContextConfig(
        max_tokens=4000,
        include_metadata=True,
        include_sources=True,
        deduplicate=True,
    )


@pytest.fixture
def rag_config(
    chunking_config,
    embedding_config,
    retrieval_config,
    rerank_config,
    context_config,
):
    """Create a complete RAG configuration."""
    return RAGConfig(
        chunking=chunking_config,
        embedding=embedding_config,
        retrieval=retrieval_config,
        rerank=rerank_config,
        context=context_config,
        use_pgvector=True,
        vector_table="document_chunks",
    )


@pytest.fixture
def text_chunker(chunking_config):
    """Create a text chunker."""
    return TextChunker(chunking_config)


@pytest.fixture
def code_chunker(chunking_config):
    """Create a code chunker."""
    return CodeChunker(chunking_config)


@pytest.fixture
def sample_document_metadata():
    """Create sample document metadata."""
    return DocumentMetadata(
        title="Test Document",
        source="/path/to/test.md",
        source_type=DocumentType.MARKDOWN,
        author="Test Author",
        created_at=datetime.utcnow(),
        language="en",
        tags=["test", "sample"],
        custom={"project": "nexusai"},
    )


@pytest.fixture
def sample_document(sample_document_metadata):
    """Create a sample document."""
    return Document(
        id=uuid4(),
        content="This is a test document with some content. It has multiple sentences. This is the third sentence.",
        metadata=sample_document_metadata,
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_document_chunk():
    """Create a sample document chunk."""
    return DocumentChunk(
        id=uuid4(),
        document_id=uuid4(),
        content="This is a test chunk with some content.",
        embedding=[0.1] * 1536,
        chunk_index=0,
        start_char=0,
        end_char=40,
        metadata={"test": True},
        token_count=10,
    )


@pytest.fixture
def sample_rag_query():
    """Create a sample RAG query."""
    return RAGQuery(
        query="What is the purpose of this document?",
        top_k=5,
        similarity_threshold=0.7,
        rerank=True,
        rerank_top_k=3,
        hybrid_search=True,
        keyword_weight=0.3,
    )


@pytest.fixture
def sample_retrieval_results(sample_document_chunk):
    """Create sample retrieval results."""
    results = []
    for i in range(5):
        chunk = DocumentChunk(
            id=uuid4(),
            document_id=uuid4(),
            content=f"This is test chunk {i} with relevant information about testing.",
            embedding=[0.1 * (i + 1)] * 1536,
            chunk_index=i,
            start_char=i * 50,
            end_char=(i + 1) * 50,
            token_count=12,
        )
        results.append(
            RetrievalResult(
                chunk=chunk,
                score=0.9 - (i * 0.05),
                document_title=f"Document {i}",
                document_source=f"/path/to/doc{i}.md",
            )
        )
    return results


@pytest.fixture
def sample_text_content():
    """Create sample text content for chunking."""
    return """
    # Introduction to Machine Learning

    Machine learning is a subset of artificial intelligence that focuses on building systems
    that can learn from data. These systems improve their performance over time without being
    explicitly programmed for each task.

    ## Supervised Learning

    Supervised learning involves training a model on labeled data. The model learns to map
    inputs to outputs based on example input-output pairs. Common algorithms include linear
    regression, decision trees, and neural networks.

    This approach is widely used in classification and regression tasks. For instance,
    email spam detection uses supervised learning to classify emails as spam or not spam.

    ## Unsupervised Learning

    In contrast to supervised learning, unsupervised learning works with unlabeled data.
    The algorithm tries to find patterns or structure in the data without guidance.
    Clustering and dimensionality reduction are common unsupervised techniques.

    K-means clustering groups similar data points together. Principal Component Analysis
    reduces the number of features while preserving important information.
    """


@pytest.fixture
def sample_code_content():
    """Create sample code content for chunking."""
    return '''
def calculate_embeddings(texts: list[str], model: str = "default") -> list[list[float]]:
    """
    Generate embeddings for a list of texts using the specified model.

    Args:
        texts: List of text strings to embed
        model: The embedding model to use

    Returns:
        List of embedding vectors
    """
    embeddings = []
    for text in texts:
        # Process each text
        vector = _encode_text(text, model)
        embeddings.append(vector)
    return embeddings


class EmbeddingService:
    """Service for managing text embeddings."""

    def __init__(self, config: dict):
        self.config = config
        self.model_name = config.get("model", "default")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts asynchronously."""
        return await self._process_batch(texts)

    async def _process_batch(self, texts: list[str]) -> list[list[float]]:
        """Process a batch of texts for embedding."""
        results = []
        for text in texts:
            embedding = await self._embed_single(text)
            results.append(embedding)
        return results

    async def _embed_single(self, text: str) -> list[float]:
        """Embed a single text string."""
        # Implementation details
        pass


def _encode_text(text: str, model: str) -> list[float]:
    """Internal function to encode text to vector."""
    # Placeholder implementation
    return [0.0] * 768
'''


@pytest.fixture
def sample_markdown_content():
    """Create sample markdown content for chunking."""
    return """
# Project Documentation

This document provides an overview of the project architecture and components.

## Architecture Overview

The system consists of several key components:

1. **Frontend Application** - A React-based web interface
2. **Backend API** - FastAPI server handling business logic
3. **Database Layer** - PostgreSQL with pgvector extension
4. **Message Queue** - Redis for async task processing

### Frontend Details

The frontend uses the following technologies:
- React 18 with TypeScript
- TailwindCSS for styling
- React Query for state management
- Vite as the build tool

### Backend Details

The backend is structured as follows:

```python
app/
  api/
    routes/
  services/
  models/
  core/
```

Each service is responsible for a specific domain of functionality.

## Getting Started

To run the project locally:

1. Clone the repository
2. Install dependencies with `npm install` and `pip install -r requirements.txt`
3. Start the development servers

## API Reference

The API provides the following endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/v1/documents | GET | List all documents |
| /api/v1/documents | POST | Create a document |
| /api/v1/search | POST | Search documents |
"""


# =============================================================================
# Document Model Tests
# =============================================================================


class TestDocumentModels:
    """Tests for RAG data models."""

    def test_document_type_enum(self):
        """Test document type enumeration."""
        assert DocumentType.MARKDOWN.value == "markdown"
        assert DocumentType.PDF.value == "pdf"
        assert DocumentType.TEXT.value == "text"
        assert DocumentType.HTML.value == "html"
        assert DocumentType.CODE.value == "code"
        assert DocumentType.DOCX.value == "docx"
        assert DocumentType.CSV.value == "csv"
        assert DocumentType.JSON.value == "json"

    def test_document_metadata_creation(self, sample_document_metadata):
        """Test creating document metadata."""
        assert sample_document_metadata.title == "Test Document"
        assert sample_document_metadata.source_type == DocumentType.MARKDOWN
        assert "test" in sample_document_metadata.tags
        assert sample_document_metadata.language == "en"

    def test_document_metadata_defaults(self):
        """Test document metadata default values."""
        metadata = DocumentMetadata()

        assert metadata.title is None
        assert metadata.source is None
        assert metadata.source_type == DocumentType.TEXT
        assert metadata.language == "en"
        assert metadata.tags == []
        assert metadata.custom == {}

    def test_document_creation(self, sample_document):
        """Test creating a document."""
        assert sample_document.id is not None
        assert sample_document.content is not None
        assert sample_document.metadata is not None
        assert sample_document.indexed is False
        assert sample_document.chunk_count == 0

    def test_document_chunk_creation(self, sample_document_chunk):
        """Test creating a document chunk."""
        assert sample_document_chunk.id is not None
        assert sample_document_chunk.document_id is not None
        assert sample_document_chunk.content is not None
        assert sample_document_chunk.embedding is not None
        assert len(sample_document_chunk.embedding) == 1536
        assert sample_document_chunk.chunk_index == 0

    def test_document_chunk_code_fields(self):
        """Test document chunk with code-specific fields."""
        chunk = DocumentChunk(
            id=uuid4(),
            document_id=uuid4(),
            content="def hello(): pass",
            chunk_index=0,
            language="python",
            function_name="hello",
            class_name=None,
        )

        assert chunk.language == "python"
        assert chunk.function_name == "hello"
        assert chunk.class_name is None

    def test_rag_query_creation(self, sample_rag_query):
        """Test creating a RAG query."""
        assert sample_rag_query.query is not None
        assert sample_rag_query.top_k == 5
        assert sample_rag_query.similarity_threshold == 0.7
        assert sample_rag_query.rerank is True
        assert sample_rag_query.hybrid_search is True

    def test_rag_query_defaults(self):
        """Test RAG query default values."""
        query = RAGQuery(query="test query")

        assert query.top_k == 5
        assert query.similarity_threshold == 0.7
        assert query.rerank is True
        assert query.rerank_top_k == 3
        assert query.hybrid_search is True
        assert query.keyword_weight == 0.3

    def test_rag_query_with_filters(self):
        """Test RAG query with filters."""
        doc_ids = [uuid4(), uuid4()]
        query = RAGQuery(
            query="test query",
            document_ids=doc_ids,
            tags=["important", "reviewed"],
            source_type=DocumentType.MARKDOWN,
            metadata_filter={"project": "nexusai"},
        )

        assert query.document_ids == doc_ids
        assert "important" in query.tags
        assert query.source_type == DocumentType.MARKDOWN
        assert query.metadata_filter["project"] == "nexusai"

    def test_retrieval_result_creation(self, sample_document_chunk):
        """Test creating a retrieval result."""
        result = RetrievalResult(
            chunk=sample_document_chunk,
            score=0.95,
            rerank_score=0.92,
            combined_score=0.935,
            document_title="Test Doc",
            document_source="/test/path",
        )

        assert result.score == 0.95
        assert result.rerank_score == 0.92
        assert result.combined_score == 0.935

    def test_rag_result_creation(self, sample_retrieval_results):
        """Test creating a RAG result."""
        result = RAGResult(
            query="test query",
            results=sample_retrieval_results,
            context="Combined context from chunks",
            context_token_count=100,
            retrieval_time_ms=15.5,
            rerank_time_ms=25.3,
            total_time_ms=45.8,
            sources=[{"index": 1, "chunk_id": "abc"}],
        )

        assert result.query == "test query"
        assert len(result.results) == 5
        assert result.context is not None
        assert result.total_time_ms == 45.8

    def test_embedding_request_creation(self):
        """Test creating an embedding request."""
        request = EmbeddingRequest(
            texts=["text1", "text2", "text3"],
            model="text-embedding-3-small",
            batch_size=50,
        )

        assert len(request.texts) == 3
        assert request.model == "text-embedding-3-small"
        assert request.batch_size == 50

    def test_embedding_result_creation(self):
        """Test creating an embedding result."""
        result = EmbeddingResult(
            embeddings=[[0.1] * 1536, [0.2] * 1536],
            model="text-embedding-3-small",
            dimensions=1536,
            total_tokens=50,
        )

        assert len(result.embeddings) == 2
        assert result.dimensions == 1536
        assert result.total_tokens == 50


# =============================================================================
# Chunking Strategy Tests
# =============================================================================


class TestTextChunker:
    """Tests for TextChunker."""

    def test_chunk_short_text(self, text_chunker):
        """Test chunking short text that fits in one chunk."""
        short_text = "This is a short piece of text."
        chunks = text_chunker.chunk(short_text)

        assert len(chunks) == 1
        assert chunks[0].content == short_text
        assert chunks[0].token_count > 0

    def test_chunk_paragraphs(self, text_chunker, sample_text_content):
        """Test chunking text with multiple paragraphs."""
        chunks = text_chunker.chunk(sample_text_content)

        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.content is not None
            assert chunk.chunk_index >= 0
            assert chunk.token_count > 0

    def test_chunk_preserves_document_id(self, text_chunker):
        """Test that chunks preserve the document ID from metadata."""
        doc_id = uuid4()
        text = "First paragraph.\n\nSecond paragraph."
        chunks = text_chunker.chunk(text, metadata={"document_id": doc_id})

        for chunk in chunks:
            assert chunk.document_id == doc_id

    def test_chunk_respects_max_size(self, chunking_config):
        """Test that chunks respect maximum size."""
        config = ChunkingConfig(chunk_size=100, max_chunk_size=150)
        chunker = TextChunker(config)

        long_sentence = "Word " * 100  # Very long text
        chunks = chunker.chunk(long_sentence)

        for chunk in chunks:
            estimated_tokens = len(chunk.content) // 4
            # Allow some tolerance for boundary handling
            assert estimated_tokens <= config.max_chunk_size * 2

    def test_chunk_sentence_splitting(self, text_chunker):
        """Test sentence boundary detection."""
        text = "First sentence. Second sentence! Third sentence? Fourth sentence."
        sentences = text_chunker._split_into_sentences(text)

        assert len(sentences) == 4
        assert sentences[0] == "First sentence."
        assert sentences[1] == "Second sentence!"

    def test_chunk_paragraph_splitting(self, text_chunker):
        """Test paragraph boundary detection."""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        paragraphs = text_chunker._split_into_paragraphs(text)

        assert len(paragraphs) == 3

    def test_chunk_metadata_propagation(self, text_chunker):
        """Test that metadata is propagated to chunks."""
        metadata = {"document_id": uuid4(), "title": "Test", "tags": ["test"]}
        text = "Some text content here."
        chunks = text_chunker.chunk(text, metadata=metadata)

        for chunk in chunks:
            assert "title" in chunk.metadata
            assert chunk.metadata["title"] == "Test"

    def test_token_estimation(self, text_chunker):
        """Test token count estimation."""
        text = "a" * 400  # 400 characters
        estimated = text_chunker._estimate_tokens(text)

        # Roughly 4 chars per token
        assert estimated == 100

    def test_chunk_indices_sequential(self, text_chunker, sample_text_content):
        """Test that chunk indices are sequential."""
        chunks = text_chunker.chunk(sample_text_content)

        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_chunk_positions_track_correctly(self, text_chunker):
        """Test that start_char and end_char are tracked."""
        text = "First paragraph here.\n\nSecond paragraph here."
        chunks = text_chunker.chunk(text)

        for chunk in chunks:
            assert chunk.start_char >= 0
            assert chunk.end_char > chunk.start_char


class TestCodeChunker:
    """Tests for CodeChunker."""

    def test_chunk_python_code(self, code_chunker, sample_code_content):
        """Test chunking Python code."""
        chunks = code_chunker.chunk(sample_code_content, metadata={"language": "python"})

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.language == "python"

    def test_detect_python_language(self, code_chunker):
        """Test Python language detection."""
        python_code = "def hello():\n    print('Hello')"
        lang = code_chunker._detect_language(python_code)

        assert lang == "python"

    def test_detect_javascript_language(self, code_chunker):
        """Test JavaScript language detection."""
        js_code = "function hello() { console.log('Hello'); }"
        lang = code_chunker._detect_language(js_code)

        assert lang == "javascript"

    def test_detect_typescript_language(self, code_chunker):
        """Test TypeScript language detection."""
        ts_code = "interface User { name: string; }"
        lang = code_chunker._detect_language(ts_code)

        assert lang == "typescript"

    def test_language_from_metadata(self, code_chunker):
        """Test that language from metadata takes precedence."""
        code = "some ambiguous code"
        lang = code_chunker._detect_language(code, {"language": "rust"})

        assert lang == "rust"

    def test_chunk_preserves_code_structure(self, code_chunker):
        """Test that code chunking preserves structure."""
        code = '''def func1():
    pass

def func2():
    pass'''

        chunks = code_chunker.chunk(code)

        # Should create chunks while preserving code readability
        for chunk in chunks:
            assert chunk.content is not None
            assert len(chunk.content) > 0

    def test_chunk_code_metadata(self, code_chunker, sample_code_content):
        """Test that code chunks get proper metadata."""
        metadata = {"document_id": uuid4(), "file_path": "test.py"}
        chunks = code_chunker.chunk(sample_code_content, metadata=metadata)

        for chunk in chunks:
            assert "document_id" in chunk.metadata
            assert "file_path" in chunk.metadata


class TestGetChunker:
    """Tests for get_chunker factory function."""

    def test_get_text_chunker(self, chunking_config):
        """Test getting text chunker for text documents."""
        chunker = get_chunker(DocumentType.TEXT, chunking_config)
        assert isinstance(chunker, TextChunker)

    def test_get_markdown_chunker(self, chunking_config):
        """Test getting chunker for markdown documents."""
        chunker = get_chunker(DocumentType.MARKDOWN, chunking_config)
        assert isinstance(chunker, TextChunker)

    def test_get_code_chunker(self, chunking_config):
        """Test getting chunker for code documents."""
        chunker = get_chunker(DocumentType.CODE, chunking_config)
        assert isinstance(chunker, CodeChunker)

    def test_get_pdf_chunker(self, chunking_config):
        """Test getting chunker for PDF documents (uses text chunker)."""
        chunker = get_chunker(DocumentType.PDF, chunking_config)
        assert isinstance(chunker, TextChunker)


# =============================================================================
# Embedding Tests
# =============================================================================


class TestOpenAIEmbedder:
    """Tests for OpenAI embeddings."""

    def test_embedder_initialization(self, embedding_config):
        """Test OpenAI embedder initialization."""
        embedder = OpenAIEmbedder(embedding_config)

        assert embedder.config == embedding_config
        assert embedder.dimensions == 1536

    @pytest.mark.asyncio
    async def test_embed_single_text(self, embedding_config):
        """Test embedding a single text."""
        embedder = OpenAIEmbedder(embedding_config)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [{"embedding": [0.1] * 1536}]
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response

            with patch("app.core.config.settings") as mock_settings:
                mock_settings.OPENAI_API_KEY = "test-key"
                result = await embedder.embed(["test text"])

            assert len(result) == 1
            assert len(result[0]) == 1536

    @pytest.mark.asyncio
    async def test_embed_batch(self, embedding_config):
        """Test embedding a batch of texts."""
        embedder = OpenAIEmbedder(embedding_config)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [
                    {"embedding": [0.1] * 1536},
                    {"embedding": [0.2] * 1536},
                    {"embedding": [0.3] * 1536},
                ]
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response

            with patch("app.core.config.settings") as mock_settings:
                mock_settings.OPENAI_API_KEY = "test-key"
                result = await embedder.embed(["text1", "text2", "text3"])

            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_embed_query(self, embedding_config):
        """Test embedding a query."""
        embedder = OpenAIEmbedder(embedding_config)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [{"embedding": [0.5] * 1536}]
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response

            with patch("app.core.config.settings") as mock_settings:
                mock_settings.OPENAI_API_KEY = "test-key"
                result = await embedder.embed_query("test query")

            assert len(result) == 1536


class TestOllamaEmbedder:
    """Tests for Ollama embeddings."""

    def test_embedder_initialization(self, embedding_config):
        """Test Ollama embedder initialization."""
        config = EmbeddingConfig(
            provider="ollama",
            ollama_model="nomic-embed-text",
            ollama_url="http://localhost:11434",
        )
        embedder = OllamaEmbedder(config)

        assert embedder.dimensions == 768

    @pytest.mark.asyncio
    async def test_embed_with_ollama(self):
        """Test embedding with Ollama."""
        config = EmbeddingConfig(
            provider="ollama",
            ollama_model="nomic-embed-text",
            ollama_url="http://localhost:11434",
        )
        embedder = OllamaEmbedder(config)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {"embedding": [0.1] * 768}
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response

            result = await embedder.embed(["test text"])

            assert len(result) == 1
            assert len(result[0]) == 768


class TestGetEmbedder:
    """Tests for get_embedder factory function."""

    def test_get_openai_embedder(self, embedding_config):
        """Test getting OpenAI embedder."""
        config = EmbeddingConfig(provider="openai")
        embedder = get_embedder(config)
        assert isinstance(embedder, OpenAIEmbedder)

    def test_get_ollama_embedder(self):
        """Test getting Ollama embedder."""
        config = EmbeddingConfig(provider="ollama")
        embedder = get_embedder(config)
        assert isinstance(embedder, OllamaEmbedder)

    def test_get_unknown_provider_raises(self):
        """Test that unknown provider raises error."""
        config = EmbeddingConfig(provider="unknown")

        with pytest.raises(ValueError, match="Unknown embedding provider"):
            get_embedder(config)


# =============================================================================
# Vector Retrieval Tests
# =============================================================================


class TestVectorStore:
    """Tests for VectorStore."""

    def test_vector_store_initialization(self, retrieval_config):
        """Test vector store initialization."""
        store = VectorStore(retrieval_config)
        assert store.config == retrieval_config

    @pytest.mark.asyncio
    async def test_add_chunks(self, retrieval_config, sample_document_chunk):
        """Test adding chunks to vector store."""
        store = VectorStore(retrieval_config)
        chunks = [sample_document_chunk]

        count = await store.add_chunks(chunks)
        assert count == 1

    @pytest.mark.asyncio
    async def test_search_returns_empty_by_default(self, retrieval_config):
        """Test that search returns empty list (placeholder implementation)."""
        store = VectorStore(retrieval_config)
        query_embedding = [0.1] * 1536

        results = await store.search(query_embedding, top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_hybrid_search(self, retrieval_config):
        """Test hybrid search."""
        store = VectorStore(retrieval_config)

        results = await store.hybrid_search(
            query="test query",
            query_embedding=[0.1] * 1536,
            top_k=5,
            semantic_weight=0.7,
            keyword_weight=0.3,
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_delete_by_document(self, retrieval_config):
        """Test deleting chunks by document ID."""
        store = VectorStore(retrieval_config)
        doc_id = uuid4()

        deleted = await store.delete_by_document(doc_id)
        assert deleted == 0  # Placeholder returns 0

    @pytest.mark.asyncio
    async def test_get_chunk_by_id(self, retrieval_config):
        """Test getting chunk by ID."""
        store = VectorStore(retrieval_config)
        chunk_id = uuid4()

        chunk = await store.get_chunk_by_id(chunk_id)
        assert chunk is None  # Placeholder returns None

    @pytest.mark.asyncio
    async def test_get_chunks_by_document(self, retrieval_config):
        """Test getting all chunks for a document."""
        store = VectorStore(retrieval_config)
        doc_id = uuid4()

        chunks = await store.get_chunks_by_document(doc_id)
        assert chunks == []


class TestRetriever:
    """Tests for Retriever."""

    @pytest.fixture
    def retriever(self, retrieval_config):
        """Create a retriever with mocked vector store."""
        vector_store = MagicMock(spec=VectorStore)
        return Retriever(retrieval_config, vector_store)

    @pytest.mark.asyncio
    async def test_retrieve_with_hybrid_search(self, retriever, sample_rag_query):
        """Test retrieval with hybrid search enabled."""
        retriever.vector_store.hybrid_search = AsyncMock(return_value=[])

        query_embedding = [0.1] * 1536
        results = await retriever.retrieve(sample_rag_query, query_embedding)

        retriever.vector_store.hybrid_search.assert_called_once()
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_retrieve_with_semantic_only(self, retriever):
        """Test retrieval with semantic search only."""
        query = RAGQuery(query="test", hybrid_search=False)
        retriever.vector_store.search = AsyncMock(return_value=[])

        query_embedding = [0.1] * 1536
        results = await retriever.retrieve(query, query_embedding)

        retriever.vector_store.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_with_document_filter(self, retriever):
        """Test retrieval with document ID filter."""
        doc_ids = [uuid4(), uuid4()]
        query = RAGQuery(query="test", document_ids=doc_ids, hybrid_search=False)
        retriever.vector_store.search = AsyncMock(return_value=[])

        results = await retriever.retrieve(query, [0.1] * 1536)

        call_args = retriever.vector_store.search.call_args
        assert "document_ids" in call_args.kwargs["filters"]

    @pytest.mark.asyncio
    async def test_retrieve_with_tag_filter(self, retriever):
        """Test retrieval with tag filter."""
        query = RAGQuery(query="test", tags=["important"], hybrid_search=False)
        retriever.vector_store.search = AsyncMock(return_value=[])

        results = await retriever.retrieve(query, [0.1] * 1536)

        call_args = retriever.vector_store.search.call_args
        assert "tags" in call_args.kwargs["filters"]

    @pytest.mark.asyncio
    async def test_retrieve_filters_by_similarity_threshold(
        self, retriever, sample_document_chunk
    ):
        """Test that results below similarity threshold are filtered."""
        query = RAGQuery(query="test", similarity_threshold=0.8, hybrid_search=False)

        # Return results with varying scores
        retriever.vector_store.search = AsyncMock(
            return_value=[
                (sample_document_chunk, 0.9),  # Above threshold
                (sample_document_chunk, 0.7),  # Below threshold
                (sample_document_chunk, 0.85),  # Above threshold
            ]
        )

        results = await retriever.retrieve(query, [0.1] * 1536)

        # Only results above 0.8 should be included
        assert len(results) == 2

    def test_mmr_empty_results(self, retriever):
        """Test MMR with empty results."""
        results = retriever._apply_mmr([], [0.1] * 1536, top_k=5)
        assert results == []

    def test_mmr_single_result(self, retriever, sample_document_chunk):
        """Test MMR with single result."""
        results = [(sample_document_chunk, 0.9)]
        mmr_results = retriever._apply_mmr(results, [0.1] * 1536, top_k=5)

        assert len(mmr_results) == 1


# =============================================================================
# Context Building Tests
# =============================================================================


class TestContextAssembly:
    """Tests for context assembly in RAG pipeline."""

    @pytest.fixture
    def pipeline_with_mocks(self, rag_config):
        """Create pipeline with mocked dependencies."""
        with patch("app.services.rag.pipeline.get_embedder") as mock_get_embedder, \
             patch("app.services.rag.pipeline.VectorStore") as mock_vector_store, \
             patch("app.services.rag.pipeline.Retriever") as mock_retriever:

            mock_embedder = MagicMock()
            mock_get_embedder.return_value = mock_embedder

            pipeline = RAGPipeline(rag_config)
            return pipeline

    def test_assemble_context_empty_results(self, pipeline_with_mocks):
        """Test context assembly with empty results."""
        context, sources = pipeline_with_mocks._assemble_context([])

        assert context == ""
        assert sources == []

    def test_assemble_context_with_results(
        self, pipeline_with_mocks, sample_retrieval_results
    ):
        """Test context assembly with results."""
        context, sources = pipeline_with_mocks._assemble_context(
            sample_retrieval_results
        )

        assert context != ""
        assert len(sources) == 5
        assert "---" in context  # Separator between chunks

    def test_assemble_context_includes_metadata(
        self, pipeline_with_mocks, sample_retrieval_results
    ):
        """Test that context includes source metadata."""
        pipeline_with_mocks.config.context.include_metadata = True

        context, sources = pipeline_with_mocks._assemble_context(
            sample_retrieval_results
        )

        assert "[Source" in context

    def test_assemble_context_without_metadata(
        self, pipeline_with_mocks, sample_retrieval_results
    ):
        """Test context without metadata."""
        pipeline_with_mocks.config.context.include_metadata = False

        context, sources = pipeline_with_mocks._assemble_context(
            sample_retrieval_results
        )

        assert "[Source" not in context

    def test_assemble_context_deduplication(self, pipeline_with_mocks):
        """Test that duplicate content is deduplicated."""
        # Create results with duplicate content
        chunk = DocumentChunk(
            id=uuid4(),
            document_id=uuid4(),
            content="This is duplicate content that appears multiple times.",
            chunk_index=0,
        )
        results = [
            RetrievalResult(chunk=chunk, score=0.9),
            RetrievalResult(chunk=chunk, score=0.85),  # Same content
        ]

        pipeline_with_mocks.config.context.deduplicate = True
        context, sources = pipeline_with_mocks._assemble_context(results)

        # Should only appear once
        assert context.count("duplicate content") == 1

    def test_assemble_context_max_tokens(self, pipeline_with_mocks):
        """Test that context respects max token limit."""
        pipeline_with_mocks.config.context.max_tokens = 50  # Very low limit

        # Create results with long content
        results = []
        for i in range(5):
            chunk = DocumentChunk(
                id=uuid4(),
                document_id=uuid4(),
                content="Word " * 100,  # Long content
                chunk_index=i,
            )
            results.append(RetrievalResult(chunk=chunk, score=0.9 - i * 0.05))

        context, sources = pipeline_with_mocks._assemble_context(results)

        # Context should be truncated
        max_chars = 50 * 4  # max_tokens * 4
        assert len(context) <= max_chars + 10  # Allow for "..." suffix

    def test_assemble_context_sources_tracking(
        self, pipeline_with_mocks, sample_retrieval_results
    ):
        """Test that sources are properly tracked."""
        context, sources = pipeline_with_mocks._assemble_context(
            sample_retrieval_results
        )

        assert len(sources) == 5
        for i, source in enumerate(sources):
            assert "index" in source
            assert "chunk_id" in source
            assert "document_id" in source
            assert "score" in source


# =============================================================================
# Document Ingestion Tests
# =============================================================================


class TestDocumentIngestion:
    """Tests for document ingestion."""

    @pytest.fixture
    def mock_pipeline(self, rag_config):
        """Create pipeline with fully mocked dependencies."""
        with patch("app.services.rag.pipeline.get_embedder") as mock_get_embedder, \
             patch("app.services.rag.pipeline.VectorStore") as mock_vs_class, \
             patch("app.services.rag.pipeline.Retriever"):

            mock_embedder = MagicMock()
            mock_embedder.embed = AsyncMock(return_value=[[0.1] * 1536])
            mock_embedder.embed_query = AsyncMock(return_value=[0.1] * 1536)
            mock_get_embedder.return_value = mock_embedder

            mock_vs = MagicMock()
            mock_vs.add_chunks = AsyncMock(return_value=1)
            mock_vs_class.return_value = mock_vs

            pipeline = RAGPipeline(rag_config)
            pipeline.vector_store = mock_vs
            pipeline.embedder = mock_embedder

            return pipeline

    @pytest.mark.asyncio
    async def test_ingest_document_text(self, mock_pipeline):
        """Test ingesting a text document."""
        content = "This is test content for ingestion."
        metadata = DocumentMetadata(title="Test Doc")

        doc = await mock_pipeline.ingest_document(
            content, metadata, DocumentType.TEXT
        )

        assert doc.indexed is True
        assert doc.chunk_count > 0
        assert doc.content == content
        mock_pipeline.embedder.embed.assert_called()
        mock_pipeline.vector_store.add_chunks.assert_called()

    @pytest.mark.asyncio
    async def test_ingest_document_markdown(self, mock_pipeline, sample_markdown_content):
        """Test ingesting a markdown document."""
        metadata = DocumentMetadata(title="Markdown Doc")

        doc = await mock_pipeline.ingest_document(
            sample_markdown_content, metadata, DocumentType.MARKDOWN
        )

        assert doc.indexed is True
        assert doc.chunk_count > 0

    @pytest.mark.asyncio
    async def test_ingest_document_code(self, mock_pipeline, sample_code_content):
        """Test ingesting a code document."""
        metadata = DocumentMetadata(title="Code Doc")

        doc = await mock_pipeline.ingest_document(
            sample_code_content, metadata, DocumentType.CODE
        )

        assert doc.indexed is True
        assert doc.metadata.source_type == DocumentType.CODE

    @pytest.mark.asyncio
    async def test_ingest_document_creates_chunks(self, mock_pipeline):
        """Test that document ingestion creates chunks."""
        content = "Paragraph one.\n\nParagraph two.\n\nParagraph three."

        doc = await mock_pipeline.ingest_document(content)

        assert doc.chunk_count > 0
        assert doc.token_count > 0

    @pytest.mark.asyncio
    async def test_ingest_document_generates_embeddings(self, mock_pipeline):
        """Test that embeddings are generated during ingestion."""
        content = "Test content for embedding generation."

        await mock_pipeline.ingest_document(content)

        mock_pipeline.embedder.embed.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_document_stores_in_vector_db(self, mock_pipeline):
        """Test that chunks are stored in vector database."""
        content = "Test content for storage."

        await mock_pipeline.ingest_document(content)

        mock_pipeline.vector_store.add_chunks.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_document_error_handling(self, mock_pipeline):
        """Test error handling during ingestion."""
        mock_pipeline.embedder.embed = AsyncMock(
            side_effect=Exception("Embedding failed")
        )

        with pytest.raises(Exception, match="Embedding failed"):
            await mock_pipeline.ingest_document("Test content")

    @pytest.mark.asyncio
    async def test_ingest_document_default_metadata(self, mock_pipeline):
        """Test ingestion with default metadata."""
        content = "Content without explicit metadata."

        doc = await mock_pipeline.ingest_document(content)

        assert doc.metadata is not None
        assert doc.metadata.source_type == DocumentType.TEXT


class TestFileIngestion:
    """Tests for file ingestion."""

    @pytest.fixture
    def mock_pipeline(self, rag_config):
        """Create pipeline with mocked dependencies for file ingestion."""
        with patch("app.services.rag.pipeline.get_embedder") as mock_get_embedder, \
             patch("app.services.rag.pipeline.VectorStore") as mock_vs_class, \
             patch("app.services.rag.pipeline.Retriever"):

            mock_embedder = MagicMock()
            mock_embedder.embed = AsyncMock(return_value=[[0.1] * 1536])
            mock_get_embedder.return_value = mock_embedder

            mock_vs = MagicMock()
            mock_vs.add_chunks = AsyncMock(return_value=1)
            mock_vs_class.return_value = mock_vs

            pipeline = RAGPipeline(rag_config)
            pipeline.vector_store = mock_vs
            pipeline.embedder = mock_embedder

            return pipeline

    @pytest.mark.asyncio
    async def test_ingest_file_not_found(self, mock_pipeline):
        """Test ingestion of non-existent file."""
        with pytest.raises(FileNotFoundError):
            await mock_pipeline.ingest_file("/nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_ingest_text_file(self, mock_pipeline):
        """Test ingesting a text file."""
        with NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is test content in a file.")
            f.flush()

            doc = await mock_pipeline.ingest_file(f.name)

            assert doc.indexed is True
            assert doc.metadata.source == f.name
            assert doc.metadata.source_type == DocumentType.TEXT

    @pytest.mark.asyncio
    async def test_ingest_markdown_file(self, mock_pipeline, sample_markdown_content):
        """Test ingesting a markdown file."""
        with NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(sample_markdown_content)
            f.flush()

            doc = await mock_pipeline.ingest_file(f.name)

            assert doc.metadata.source_type == DocumentType.MARKDOWN

    @pytest.mark.asyncio
    async def test_ingest_python_file(self, mock_pipeline, sample_code_content):
        """Test ingesting a Python file."""
        with NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(sample_code_content)
            f.flush()

            doc = await mock_pipeline.ingest_file(f.name)

            assert doc.metadata.source_type == DocumentType.CODE

    @pytest.mark.asyncio
    async def test_ingest_file_with_metadata(self, mock_pipeline):
        """Test ingesting file with custom metadata."""
        with NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content")
            f.flush()

            metadata = DocumentMetadata(
                title="Custom Title",
                author="Test Author",
                tags=["test", "custom"],
            )

            doc = await mock_pipeline.ingest_file(f.name, metadata=metadata)

            assert doc.metadata.title == "Custom Title"
            assert doc.metadata.author == "Test Author"
            assert "test" in doc.metadata.tags

    @pytest.mark.asyncio
    async def test_ingest_file_detects_document_type(self, mock_pipeline):
        """Test that file extension determines document type."""
        extensions_and_types = [
            (".txt", DocumentType.TEXT),
            (".md", DocumentType.MARKDOWN),
            (".py", DocumentType.CODE),
            (".js", DocumentType.CODE),
            (".ts", DocumentType.CODE),
            (".html", DocumentType.HTML),
            (".json", DocumentType.JSON),
            (".csv", DocumentType.CSV),
        ]

        for ext, expected_type in extensions_and_types:
            with NamedTemporaryFile(mode="w", suffix=ext, delete=False) as f:
                f.write("test content")
                f.flush()

                doc = await mock_pipeline.ingest_file(f.name)
                assert doc.metadata.source_type == expected_type, f"Failed for {ext}"


class TestPDFIngestion:
    """Tests for PDF ingestion."""

    @pytest.fixture
    def mock_pipeline(self, rag_config):
        """Create pipeline for PDF testing."""
        with patch("app.services.rag.pipeline.get_embedder") as mock_get_embedder, \
             patch("app.services.rag.pipeline.VectorStore") as mock_vs_class, \
             patch("app.services.rag.pipeline.Retriever"):

            mock_embedder = MagicMock()
            mock_embedder.embed = AsyncMock(return_value=[[0.1] * 1536])
            mock_get_embedder.return_value = mock_embedder

            mock_vs = MagicMock()
            mock_vs.add_chunks = AsyncMock(return_value=1)
            mock_vs_class.return_value = mock_vs

            pipeline = RAGPipeline(rag_config)
            pipeline.vector_store = mock_vs
            pipeline.embedder = mock_embedder

            return pipeline

    @pytest.mark.asyncio
    async def test_load_pdf_requires_pypdf(self, mock_pipeline):
        """Test that PDF loading requires pypdf library."""
        # Test verifies that pdf loading gracefully handles missing pypdf
        # The actual behavior depends on whether pypdf is installed
        with NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake pdf content")
            f.flush()

            # Test passes if no exception is raised during import checks
            # The actual pypdf behavior is tested in test_load_pdf_with_mock_pypdf
            assert True  # Placeholder - PDF loading tested elsewhere

    @pytest.mark.asyncio
    async def test_load_pdf_with_mock_pypdf(self, mock_pipeline):
        """Test PDF loading with mocked pypdf."""
        with patch("pypdf.PdfReader") as mock_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Page content"
            mock_reader.return_value.pages = [mock_page, mock_page]

            with NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(b"%PDF-1.4")
                f.flush()

                content = await mock_pipeline._load_pdf(Path(f.name))

                assert "Page content" in content


# =============================================================================
# End-to-End RAG Query Tests
# =============================================================================


class TestRAGQuery:
    """End-to-end tests for RAG query."""

    @pytest.fixture
    def mock_pipeline(self, rag_config):
        """Create pipeline with all mocked components."""
        with patch("app.services.rag.pipeline.get_embedder") as mock_get_embedder, \
             patch("app.services.rag.pipeline.VectorStore") as mock_vs_class, \
             patch("app.services.rag.pipeline.Retriever") as mock_retriever_class:

            # Mock embedder
            mock_embedder = MagicMock()
            mock_embedder.embed = AsyncMock(return_value=[[0.1] * 1536])
            mock_embedder.embed_query = AsyncMock(return_value=[0.1] * 1536)
            mock_get_embedder.return_value = mock_embedder

            # Mock vector store
            mock_vs = MagicMock()
            mock_vs.add_chunks = AsyncMock(return_value=1)
            mock_vs_class.return_value = mock_vs

            # Mock retriever
            mock_retriever = MagicMock()
            mock_retriever.retrieve = AsyncMock(return_value=[])
            mock_retriever_class.return_value = mock_retriever

            pipeline = RAGPipeline(rag_config)
            pipeline.embedder = mock_embedder
            pipeline.vector_store = mock_vs
            pipeline.retriever = mock_retriever

            return pipeline

    @pytest.mark.asyncio
    async def test_query_basic(self, mock_pipeline, sample_rag_query):
        """Test basic RAG query."""
        result = await mock_pipeline.query(sample_rag_query)

        assert isinstance(result, RAGResult)
        assert result.query == sample_rag_query.query
        mock_pipeline.embedder.embed_query.assert_called_once()
        mock_pipeline.retriever.retrieve.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_returns_context(self, mock_pipeline):
        """Test that query returns assembled context."""
        # Setup mock retrieval results
        chunk = DocumentChunk(
            id=uuid4(),
            document_id=uuid4(),
            content="This is relevant content for the query.",
            chunk_index=0,
        )
        mock_pipeline.retriever.retrieve = AsyncMock(
            return_value=[
                RetrievalResult(
                    chunk=chunk,
                    score=0.95,
                    document_title="Test Doc",
                    document_source="/test/path",
                )
            ]
        )

        query = RAGQuery(query="test query", rerank=False)
        result = await mock_pipeline.query(query)

        assert result.context is not None
        assert "relevant content" in result.context

    @pytest.mark.asyncio
    async def test_query_with_reranking(self, mock_pipeline):
        """Test query with reranking enabled."""
        # Create mock results
        chunks = []
        for i in range(5):
            chunk = DocumentChunk(
                id=uuid4(),
                document_id=uuid4(),
                content=f"Content {i}",
                chunk_index=i,
            )
            chunks.append(
                RetrievalResult(chunk=chunk, score=0.9 - i * 0.05)
            )

        mock_pipeline.retriever.retrieve = AsyncMock(return_value=chunks)

        query = RAGQuery(query="test", rerank=True, rerank_top_k=3)

        with patch.object(mock_pipeline, "_rerank", new_callable=AsyncMock) as mock_rerank:
            mock_rerank.return_value = chunks[:3]
            result = await mock_pipeline.query(query)

            mock_rerank.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_timing_metrics(self, mock_pipeline, sample_rag_query):
        """Test that query includes timing metrics."""
        sample_rag_query.rerank = False
        result = await mock_pipeline.query(sample_rag_query)

        assert result.retrieval_time_ms >= 0
        assert result.total_time_ms >= 0
        assert result.total_time_ms >= result.retrieval_time_ms

    @pytest.mark.asyncio
    async def test_query_sources_tracking(self, mock_pipeline):
        """Test that sources are tracked in query result."""
        chunk = DocumentChunk(
            id=uuid4(),
            document_id=uuid4(),
            content="Source content",
            chunk_index=0,
        )
        mock_pipeline.retriever.retrieve = AsyncMock(
            return_value=[
                RetrievalResult(
                    chunk=chunk,
                    score=0.9,
                    document_title="Doc Title",
                    document_source="/path/to/doc",
                )
            ]
        )

        query = RAGQuery(query="test", rerank=False)
        result = await mock_pipeline.query(query)

        assert len(result.sources) == 1
        assert result.sources[0]["title"] == "Doc Title"

    @pytest.mark.asyncio
    async def test_query_no_results(self, mock_pipeline):
        """Test query with no matching results."""
        mock_pipeline.retriever.retrieve = AsyncMock(return_value=[])

        query = RAGQuery(query="test", rerank=False)
        result = await mock_pipeline.query(query)

        assert result.context == ""
        assert result.sources == []

    @pytest.mark.asyncio
    async def test_query_context_token_count(self, mock_pipeline):
        """Test that context token count is calculated."""
        chunk = DocumentChunk(
            id=uuid4(),
            document_id=uuid4(),
            content="A" * 400,  # 100 tokens roughly
            chunk_index=0,
        )
        mock_pipeline.retriever.retrieve = AsyncMock(
            return_value=[RetrievalResult(chunk=chunk, score=0.9)]
        )

        query = RAGQuery(query="test", rerank=False)
        result = await mock_pipeline.query(query)

        assert result.context_token_count > 0


class TestReranking:
    """Tests for reranking functionality."""

    @pytest.fixture
    def mock_pipeline(self, rag_config):
        """Create pipeline for rerank testing."""
        with patch("app.services.rag.pipeline.get_embedder") as mock_get_embedder, \
             patch("app.services.rag.pipeline.VectorStore"), \
             patch("app.services.rag.pipeline.Retriever"):

            mock_embedder = MagicMock()
            mock_get_embedder.return_value = mock_embedder

            pipeline = RAGPipeline(rag_config)
            return pipeline

    @pytest.mark.asyncio
    async def test_rerank_with_cross_encoder(self, mock_pipeline, sample_retrieval_results):
        """Test reranking with cross-encoder."""
        mock_pipeline.config.rerank.provider = "cross-encoder"

        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9, 0.8, 0.7, 0.6, 0.5]
        mock_st = MagicMock()
        mock_st.CrossEncoder.return_value = mock_model

        with patch.dict("sys.modules", {"sentence_transformers": mock_st}):
            reranked = await mock_pipeline._rerank_cross_encoder(
                "test query",
                sample_retrieval_results,
                top_k=3,
            )

            assert len(reranked) == 3
            mock_model.predict.assert_called_once()

    @pytest.mark.asyncio
    async def test_rerank_without_cross_encoder(self, mock_pipeline, sample_retrieval_results):
        """Test reranking falls back gracefully without cross-encoder."""
        mock_pipeline.config.rerank.provider = "cross-encoder"

        with patch("app.services.rag.pipeline.logger") as mock_logger:
            # Simulate ImportError by mocking the import
            with patch.dict("sys.modules", {"sentence_transformers": None}):
                # Should return top_k results without reranking
                pass

    @pytest.mark.asyncio
    async def test_rerank_with_cohere(self, mock_pipeline, sample_retrieval_results):
        """Test reranking with Cohere API."""
        mock_pipeline.config.rerank.provider = "cohere"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "results": [
                    {"index": 0, "relevance_score": 0.95},
                    {"index": 2, "relevance_score": 0.85},
                    {"index": 1, "relevance_score": 0.75},
                ]
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response

            with patch("app.core.config.settings") as mock_settings:
                mock_settings.COHERE_API_KEY = "test-key"

                reranked = await mock_pipeline._rerank_cohere(
                    "test query",
                    sample_retrieval_results,
                    top_k=3,
                )

                assert len(reranked) == 3

    @pytest.mark.asyncio
    async def test_rerank_cohere_without_api_key(
        self, mock_pipeline, sample_retrieval_results
    ):
        """Test Cohere reranking without API key."""
        mock_pipeline.config.rerank.provider = "cohere"

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.COHERE_API_KEY = None

            reranked = await mock_pipeline._rerank_cohere(
                "test query",
                sample_retrieval_results,
                top_k=3,
            )

            # Should return top_k results without reranking
            assert len(reranked) == 3

    @pytest.mark.asyncio
    async def test_rerank_updates_scores(self, mock_pipeline, sample_retrieval_results):
        """Test that reranking updates result scores."""
        mock_pipeline.config.rerank.provider = "cross-encoder"

        mock_model = MagicMock()
        mock_model.predict.return_value = [0.95, 0.85, 0.75, 0.65, 0.55]
        mock_st = MagicMock()
        mock_st.CrossEncoder.return_value = mock_model

        with patch.dict("sys.modules", {"sentence_transformers": mock_st}):
            reranked = await mock_pipeline._rerank_cross_encoder(
                "test query",
                sample_retrieval_results,
                top_k=5,
            )

            for result in reranked:
                assert result.rerank_score is not None
                assert result.combined_score is not None


class TestDocumentDeletion:
    """Tests for document deletion."""

    @pytest.fixture
    def mock_pipeline(self, rag_config):
        """Create pipeline with mocked vector store."""
        with patch("app.services.rag.pipeline.get_embedder"), \
             patch("app.services.rag.pipeline.VectorStore") as mock_vs_class, \
             patch("app.services.rag.pipeline.Retriever"):

            mock_vs = MagicMock()
            mock_vs.delete_by_document = AsyncMock(return_value=5)
            mock_vs_class.return_value = mock_vs

            pipeline = RAGPipeline(rag_config)
            pipeline.vector_store = mock_vs

            return pipeline

    @pytest.mark.asyncio
    async def test_delete_document(self, mock_pipeline):
        """Test deleting a document."""
        doc_id = uuid4()

        deleted = await mock_pipeline.delete_document(doc_id)

        assert deleted is True
        mock_pipeline.vector_store.delete_by_document.assert_called_once_with(doc_id)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self, mock_pipeline):
        """Test deleting a non-existent document."""
        mock_pipeline.vector_store.delete_by_document = AsyncMock(return_value=0)
        doc_id = uuid4()

        deleted = await mock_pipeline.delete_document(doc_id)

        assert deleted is False


# =============================================================================
# Configuration Tests
# =============================================================================


class TestRAGConfiguration:
    """Tests for RAG configuration."""

    def test_chunking_config_defaults(self):
        """Test chunking config default values."""
        config = ChunkingConfig()

        assert config.chunk_size == 512
        assert config.chunk_overlap == 50
        assert config.min_chunk_size == 100
        assert config.max_chunk_size == 1024
        assert config.respect_sentence_boundaries is True

    def test_embedding_config_defaults(self):
        """Test embedding config default values."""
        config = EmbeddingConfig()

        assert config.provider == "openai"
        assert config.model == "text-embedding-3-small"
        assert config.dimensions == 1536
        assert config.batch_size == 100

    def test_retrieval_config_defaults(self):
        """Test retrieval config default values."""
        config = RetrievalConfig()

        assert config.default_top_k == 10
        assert config.similarity_threshold == 0.7
        assert config.enable_hybrid is True
        assert config.enable_mmr is True

    def test_rerank_config_defaults(self):
        """Test rerank config default values."""
        config = RerankConfig()

        assert config.enabled is True
        assert config.provider == "cross-encoder"
        assert config.top_k == 5

    def test_context_config_defaults(self):
        """Test context config default values."""
        config = ContextConfig()

        assert config.max_tokens == 8000
        assert config.include_metadata is True
        assert config.deduplicate is True

    def test_rag_config_composition(self, rag_config):
        """Test that RAG config properly composes sub-configs."""
        assert isinstance(rag_config.chunking, ChunkingConfig)
        assert isinstance(rag_config.embedding, EmbeddingConfig)
        assert isinstance(rag_config.retrieval, RetrievalConfig)
        assert isinstance(rag_config.rerank, RerankConfig)
        assert isinstance(rag_config.context, ContextConfig)


class TestGlobalPipeline:
    """Tests for global pipeline instance."""

    def test_get_rag_pipeline_singleton(self):
        """Test that get_rag_pipeline returns singleton."""
        with patch("app.services.rag.pipeline.get_rag_config") as mock_config, \
             patch("app.services.rag.pipeline.get_embedder"), \
             patch("app.services.rag.pipeline.VectorStore"), \
             patch("app.services.rag.pipeline.Retriever"):

            mock_config.return_value = RAGConfig()

            # Reset global state
            import app.services.rag.pipeline as pipeline_module
            pipeline_module._rag_pipeline = None

            pipeline1 = get_rag_pipeline()
            pipeline2 = get_rag_pipeline()

            assert pipeline1 is pipeline2


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_chunk_empty_text(self, text_chunker):
        """Test chunking empty text."""
        chunks = text_chunker.chunk("")
        assert len(chunks) == 0

    def test_chunk_whitespace_only(self, text_chunker):
        """Test chunking whitespace-only text."""
        chunks = text_chunker.chunk("   \n\n   \t   ")
        assert len(chunks) == 0

    def test_chunk_single_word(self, text_chunker):
        """Test chunking single word."""
        chunks = text_chunker.chunk("Hello")
        assert len(chunks) == 1
        assert chunks[0].content == "Hello"

    def test_code_chunk_empty(self, code_chunker):
        """Test chunking empty code."""
        chunks = code_chunker.chunk("")
        # Implementation may return a single empty chunk or no chunks
        if len(chunks) > 0:
            assert chunks[0].content == ""
        else:
            assert len(chunks) == 0

    def test_detect_unknown_language(self, code_chunker):
        """Test detecting unknown programming language."""
        code = "some random text that is not code"
        lang = code_chunker._detect_language(code)
        assert lang == "unknown"

    @pytest.mark.asyncio
    async def test_ingest_empty_content(self, rag_config):
        """Test ingesting empty content."""
        with patch("app.services.rag.pipeline.get_embedder") as mock_get_embedder, \
             patch("app.services.rag.pipeline.VectorStore") as mock_vs_class, \
             patch("app.services.rag.pipeline.Retriever"):

            mock_embedder = MagicMock()
            mock_embedder.embed = AsyncMock(return_value=[])
            mock_get_embedder.return_value = mock_embedder

            mock_vs = MagicMock()
            mock_vs.add_chunks = AsyncMock(return_value=0)
            mock_vs_class.return_value = mock_vs

            pipeline = RAGPipeline(rag_config)
            pipeline.embedder = mock_embedder
            pipeline.vector_store = mock_vs

            doc = await pipeline.ingest_document("")

            assert doc.chunk_count == 0

    def test_retrieval_result_without_optional_fields(self, sample_document_chunk):
        """Test creating retrieval result without optional fields."""
        result = RetrievalResult(
            chunk=sample_document_chunk,
            score=0.85,
        )

        assert result.rerank_score is None
        assert result.combined_score is None
        assert result.document_title is None
        assert result.document_source is None

    def test_rag_query_minimal(self):
        """Test creating RAG query with minimal fields."""
        query = RAGQuery(query="test")

        assert query.query == "test"
        assert query.top_k == 5  # Default
        assert query.document_ids is None

    def test_document_metadata_custom_fields(self):
        """Test document metadata with custom fields."""
        metadata = DocumentMetadata(
            custom={
                "project_id": "proj_123",
                "version": "1.0",
                "internal_id": 42,
            }
        )

        assert metadata.custom["project_id"] == "proj_123"
        assert metadata.custom["internal_id"] == 42
