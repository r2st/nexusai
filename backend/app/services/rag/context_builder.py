"""
Context Builder

Assembles optimal context for LLM prompts from retrieved documents.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

from .vector_store import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class ContextConfig:
    """Configuration for context building."""
    max_tokens: int = 4000
    max_documents: int = 10
    
    # Formatting
    include_source: bool = True
    include_metadata: bool = True
    separator: str = "\n\n---\n\n"
    
    # Prioritization
    prioritize_code: bool = True
    prioritize_recent: bool = True
    
    # Deduplication
    dedupe_threshold: float = 0.9  # Similarity threshold for deduplication


@dataclass
class ContextChunk:
    """A chunk of context to include in the prompt."""
    content: str
    source: str
    source_type: str
    relevance_score: float
    token_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BuiltContext:
    """The assembled context ready for the prompt."""
    text: str
    chunks: List[ContextChunk]
    total_tokens: int
    sources_used: int
    truncated: bool = False


class ContextBuilder:
    """
    Builds optimal context for LLM prompts.
    
    Features:
    - Token-aware truncation
    - Source deduplication
    - Relevance-based ordering
    - Format optimization per source type
    """
    
    def __init__(self, config: Optional[ContextConfig] = None):
        self.config = config or ContextConfig()
    
    def build(
        self,
        results: List[SearchResult],
        query: str,
        config: Optional[ContextConfig] = None,
    ) -> BuiltContext:
        """
        Build context from search results.
        
        Args:
            results: Retrieved documents
            query: Original query (for relevance hints)
            config: Override default config
            
        Returns:
            BuiltContext ready for prompt insertion
        """
        cfg = config or self.config
        
        # Convert to context chunks
        chunks = self._convert_to_chunks(results)
        
        # Deduplicate
        chunks = self._deduplicate(chunks, cfg.dedupe_threshold)
        
        # Prioritize
        chunks = self._prioritize(chunks, cfg)
        
        # Select chunks within token budget
        selected, total_tokens, truncated = self._select_within_budget(
            chunks,
            cfg.max_tokens,
            cfg.max_documents,
        )
        
        # Format into text
        text = self._format_context(selected, cfg)
        
        return BuiltContext(
            text=text,
            chunks=selected,
            total_tokens=total_tokens,
            sources_used=len(selected),
            truncated=truncated,
        )
    
    def _convert_to_chunks(self, results: List[SearchResult]) -> List[ContextChunk]:
        """Convert search results to context chunks."""
        chunks = []
        
        for result in results:
            doc = result.document
            
            # Format source reference
            source = self._format_source_reference(doc)
            
            # Estimate tokens (rough: ~4 chars per token)
            token_count = len(doc.content) // 4
            
            chunks.append(ContextChunk(
                content=doc.content,
                source=source,
                source_type=doc.source_type,
                relevance_score=result.rerank_score or result.score,
                token_count=token_count,
                metadata=doc.metadata,
            ))
        
        return chunks
    
    def _format_source_reference(self, doc: "Document") -> str:
        """Format a source reference for citation."""
        if doc.source_type == "code":
            path = doc.metadata.get("path", "unknown")
            repo = doc.metadata.get("repo", "")
            start = doc.metadata.get("start_line", 1)
            end = doc.metadata.get("end_line", start)
            return f"{repo}/{path}:L{start}-{end}"
        
        elif doc.source_type == "ticket":
            key = doc.metadata.get("key", doc.source_id)
            return f"[{key}]"
        
        elif doc.source_type == "doc":
            path = doc.metadata.get("path", "document")
            return path
        
        elif doc.source_type == "incident":
            inc_id = doc.metadata.get("incident_id", doc.source_id)
            return f"Incident {inc_id}"
        
        return doc.source_id
    
    def _deduplicate(
        self,
        chunks: List[ContextChunk],
        threshold: float,
    ) -> List[ContextChunk]:
        """Remove near-duplicate chunks."""
        if len(chunks) <= 1:
            return chunks
        
        unique: List[ContextChunk] = []
        
        for chunk in chunks:
            is_duplicate = False
            for existing in unique:
                similarity = self._text_similarity(chunk.content, existing.content)
                if similarity >= threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(chunk)
        
        return unique
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity using character overlap."""
        if not text1 or not text2:
            return 0.0
        
        # Jaccard similarity on character trigrams
        def get_trigrams(text: str) -> set:
            text = text.lower()
            return {text[i:i+3] for i in range(len(text) - 2)}
        
        t1 = get_trigrams(text1)
        t2 = get_trigrams(text2)
        
        if not t1 or not t2:
            return 0.0
        
        intersection = len(t1 & t2)
        union = len(t1 | t2)
        
        return intersection / union if union > 0 else 0.0
    
    def _prioritize(
        self,
        chunks: List[ContextChunk],
        config: ContextConfig,
    ) -> List[ContextChunk]:
        """Prioritize chunks based on config."""
        
        def priority_key(chunk: ContextChunk) -> tuple:
            # Higher score = more relevant
            score_priority = -chunk.relevance_score
            
            # Type priority
            type_priority = {
                "code": 0 if config.prioritize_code else 2,
                "doc": 1,
                "ticket": 2,
                "incident": 3,
            }.get(chunk.source_type, 4)
            
            return (type_priority, score_priority)
        
        return sorted(chunks, key=priority_key)
    
    def _select_within_budget(
        self,
        chunks: List[ContextChunk],
        max_tokens: int,
        max_docs: int,
    ) -> tuple[List[ContextChunk], int, bool]:
        """Select chunks within token budget."""
        selected: List[ContextChunk] = []
        total_tokens = 0
        truncated = False
        
        for chunk in chunks:
            if len(selected) >= max_docs:
                truncated = True
                break
            
            if total_tokens + chunk.token_count > max_tokens:
                # Try to fit a truncated version
                remaining = max_tokens - total_tokens
                if remaining > 100:  # Minimum useful size
                    truncated_content = chunk.content[:remaining * 4] + "..."
                    truncated_chunk = ContextChunk(
                        content=truncated_content,
                        source=chunk.source,
                        source_type=chunk.source_type,
                        relevance_score=chunk.relevance_score,
                        token_count=remaining,
                        metadata=chunk.metadata,
                    )
                    selected.append(truncated_chunk)
                    total_tokens += remaining
                truncated = True
                break
            
            selected.append(chunk)
            total_tokens += chunk.token_count
        
        return selected, total_tokens, truncated
    
    def _format_context(
        self,
        chunks: List[ContextChunk],
        config: ContextConfig,
    ) -> str:
        """Format chunks into final context text."""
        if not chunks:
            return ""
        
        parts = []
        
        for chunk in chunks:
            formatted = self._format_chunk(chunk, config)
            parts.append(formatted)
        
        return config.separator.join(parts)
    
    def _format_chunk(self, chunk: ContextChunk, config: ContextConfig) -> str:
        """Format a single chunk."""
        parts = []
        
        # Source header
        if config.include_source:
            if chunk.source_type == "code":
                lang = chunk.metadata.get("language", "")
                parts.append(f"**Source**: `{chunk.source}`")
                if lang:
                    parts.append(f"```{lang}")
                    parts.append(chunk.content)
                    parts.append("```")
                else:
                    parts.append(chunk.content)
            else:
                parts.append(f"**Source**: {chunk.source}")
                parts.append(chunk.content)
        else:
            parts.append(chunk.content)
        
        # Metadata
        if config.include_metadata and chunk.metadata:
            relevant_meta = {
                k: v for k, v in chunk.metadata.items()
                if k in ["status", "severity", "labels", "assignee", "symbol_name"]
            }
            if relevant_meta:
                meta_str = ", ".join(f"{k}: {v}" for k, v in relevant_meta.items())
                parts.append(f"*({meta_str})*")
        
        return "\n".join(parts)
