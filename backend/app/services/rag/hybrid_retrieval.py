"""
Hybrid Retrieval Engine

Combines keyword and semantic search with reranking.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import asyncio
import logging
import re

from .embeddings import EmbeddingsService
from .vector_store import VectorStore, SearchQuery, SearchResult, Document

logger = logging.getLogger(__name__)


@dataclass
class RetrievalConfig:
    """Configuration for retrieval."""
    # Search settings
    top_k: int = 10
    rerank_top_k: int = 50  # Retrieve more for reranking
    score_threshold: float = 0.5
    
    # Hybrid weights
    keyword_weight: float = 0.3
    semantic_weight: float = 0.7
    
    # Reranking
    enable_reranking: bool = True
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # Diversity
    enable_mmr: bool = False  # Maximum Marginal Relevance
    mmr_diversity: float = 0.3
    
    # Filters
    source_types: Optional[List[str]] = None


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""
    results: List[SearchResult]
    query: str
    total_found: int
    retrieval_time_ms: int
    reranked: bool = False


class KeywordSearcher:
    """Simple keyword/BM25-like search."""
    
    def __init__(self, documents: Optional[List[Document]] = None):
        self.documents = documents or []
        self._index: Dict[str, List[str]] = {}  # term -> doc_ids
    
    def index_documents(self, documents: List[Document]) -> None:
        """Build inverted index."""
        self.documents.extend(documents)
        
        for doc in documents:
            terms = self._tokenize(doc.content)
            for term in terms:
                if term not in self._index:
                    self._index[term] = []
                self._index[term].append(doc.id)
    
    def search(
        self,
        query: str,
        tenant_id: str,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """Search using keyword matching."""
        query_terms = self._tokenize(query)
        
        # Score documents
        scores: Dict[str, float] = {}
        
        for term in query_terms:
            if term in self._index:
                for doc_id in self._index[term]:
                    if doc_id not in scores:
                        scores[doc_id] = 0
                    scores[doc_id] += 1
        
        # Normalize and filter by tenant
        results = []
        for doc in self.documents:
            if doc.id in scores and doc.tenant_id == tenant_id:
                score = scores[doc.id] / len(query_terms)
                results.append(SearchResult(
                    document=doc,
                    score=score,
                ))
        
        # Sort and limit
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        # Lowercase and split on non-alphanumeric
        tokens = re.findall(r"\w+", text.lower())
        # Remove stopwords (simplified)
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being"}
        return [t for t in tokens if t not in stopwords and len(t) > 2]


class CrossEncoderReranker:
    """
    Rerank results using a cross-encoder model.
    
    Cross-encoders compare query and document together for more accurate scoring.
    """
    
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
                logger.warning("sentence-transformers not installed, reranking disabled")
                return None
        return self._model
    
    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 10,
    ) -> List[SearchResult]:
        """Rerank results using cross-encoder."""
        if not results:
            return results
        
        model = self._load_model()
        if model is None:
            return results[:top_k]
        
        # Prepare pairs
        pairs = [(query, r.document.content) for r in results]
        
        # Score in thread pool (model is sync)
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(
            None,
            lambda: model.predict(pairs),
        )
        
        # Update scores and sort
        for result, score in zip(results, scores):
            result.rerank_score = float(score)
        
        results.sort(key=lambda x: x.rerank_score or 0, reverse=True)
        
        return results[:top_k]


class HybridRetriever:
    """
    Hybrid retrieval combining keyword and semantic search.
    
    Features:
    - BM25/keyword search
    - Vector similarity search
    - Score fusion
    - Cross-encoder reranking
    - MMR for diversity
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        embeddings: EmbeddingsService,
        config: Optional[RetrievalConfig] = None,
    ):
        self.vector_store = vector_store
        self.embeddings = embeddings
        self.config = config or RetrievalConfig()
        
        self.keyword_searcher = KeywordSearcher()
        self.reranker = CrossEncoderReranker(self.config.rerank_model)
    
    async def retrieve(
        self,
        query: str,
        tenant_id: str,
        config: Optional[RetrievalConfig] = None,
        collection: Optional[str] = None,
    ) -> RetrievalResult:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: Natural language query
            tenant_id: Tenant to search within
            config: Override default config
            collection: Vector store collection
            
        Returns:
            RetrievalResult with ranked documents
        """
        import time
        start_time = time.time()
        
        cfg = config or self.config
        
        # Generate query embedding
        query_embedding = await self.embeddings.embed_single(query)
        
        # Run searches in parallel
        semantic_results, keyword_results = await asyncio.gather(
            self._semantic_search(
                query_embedding.embedding,
                tenant_id,
                cfg,
                collection,
            ),
            self._keyword_search(query, tenant_id, cfg),
        )
        
        # Fuse results
        fused = self._fuse_results(
            semantic_results,
            keyword_results,
            cfg,
        )
        
        # Rerank if enabled
        reranked = False
        if cfg.enable_reranking and len(fused) > cfg.top_k:
            fused = await self.reranker.rerank(query, fused, cfg.rerank_top_k)
            reranked = True
        
        # Apply MMR for diversity
        if cfg.enable_mmr:
            fused = self._apply_mmr(fused, query_embedding.embedding, cfg)
        
        # Final top-k
        final_results = fused[:cfg.top_k]
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return RetrievalResult(
            results=final_results,
            query=query,
            total_found=len(fused),
            retrieval_time_ms=elapsed_ms,
            reranked=reranked,
        )
    
    async def _semantic_search(
        self,
        embedding: List[float],
        tenant_id: str,
        config: RetrievalConfig,
        collection: Optional[str],
    ) -> List[SearchResult]:
        """Perform semantic (vector) search."""
        query = SearchQuery(
            query="",
            embedding=embedding,
            top_k=config.rerank_top_k if config.enable_reranking else config.top_k,
            tenant_id=tenant_id,
            source_types=config.source_types,
            use_semantic=True,
            use_keyword=False,
        )
        
        return await self.vector_store.search(query, collection)
    
    async def _keyword_search(
        self,
        query: str,
        tenant_id: str,
        config: RetrievalConfig,
    ) -> List[SearchResult]:
        """Perform keyword (BM25-like) search."""
        # This would ideally use Elasticsearch or similar
        return self.keyword_searcher.search(
            query,
            tenant_id,
            config.rerank_top_k if config.enable_reranking else config.top_k,
        )
    
    def _fuse_results(
        self,
        semantic: List[SearchResult],
        keyword: List[SearchResult],
        config: RetrievalConfig,
    ) -> List[SearchResult]:
        """Fuse semantic and keyword results using RRF."""
        # Reciprocal Rank Fusion
        k = 60  # RRF constant
        scores: Dict[str, float] = {}
        docs: Dict[str, SearchResult] = {}
        
        # Score semantic results
        for rank, result in enumerate(semantic):
            doc_id = result.document.id
            rrf_score = config.semantic_weight / (k + rank + 1)
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score
            docs[doc_id] = result
        
        # Score keyword results
        for rank, result in enumerate(keyword):
            doc_id = result.document.id
            rrf_score = config.keyword_weight / (k + rank + 1)
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score
            if doc_id not in docs:
                docs[doc_id] = result
        
        # Sort by fused score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        return [
            SearchResult(
                document=docs[doc_id].document,
                score=scores[doc_id],
                highlights=docs[doc_id].highlights,
            )
            for doc_id in sorted_ids
        ]
    
    def _apply_mmr(
        self,
        results: List[SearchResult],
        query_embedding: List[float],
        config: RetrievalConfig,
    ) -> List[SearchResult]:
        """Apply Maximum Marginal Relevance for diversity."""
        if len(results) <= config.top_k:
            return results
        
        # Simplified MMR - would need document embeddings for full implementation
        # For now, just return results as-is
        return results
    
    def index_documents(self, documents: List[Document]) -> None:
        """Index documents for keyword search."""
        self.keyword_searcher.index_documents(documents)
