"""
RAG (Retrieval-Augmented Generation) MCP Tools

Exposes RAG capabilities through MCP:
- Semantic search across code, docs, and tickets
- Hybrid retrieval with keyword + vector search
- Context building for LLM prompts
- Document indexing
"""

from dataclasses import dataclass
from typing import Any, Optional
import structlog

from .server import MCPToolHandler
from .protocol import MCPTool
from .errors import (
    safe_tool_execute,
    service_unavailable_error,
    invalid_input_error,
    not_found_error,
)

logger = structlog.get_logger()


@dataclass
class RAGSearchResult:
    """Search result from RAG."""

    id: str
    content: str
    source: str
    source_type: str  # code, doc, ticket, incident
    score: float
    metadata: dict


class RAGSemanticSearchHandler(MCPToolHandler):
    """
    Perform semantic search across the knowledge base.

    Searches code, documentation, tickets, and incidents using
    vector similarity to find relevant content.
    """

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="rag_semantic_search",
            description="Search the knowledge base using semantic similarity",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query in natural language",
                    },
                    "source_types": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["code", "doc", "ticket", "incident"]},
                        "description": "Types of sources to search (default: all)",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default: 10)",
                        "default": 10,
                    },
                    "min_score": {
                        "type": "number",
                        "description": "Minimum similarity score (0-1, default: 0.5)",
                        "default": 0.5,
                    },
                    "organization_id": {
                        "type": "string",
                        "description": "Organization ID for tenant isolation",
                    },
                    "project_id": {
                        "type": "string",
                        "description": "Optional project ID to scope search",
                    },
                },
                "required": ["query"],
            },
        )

    async def execute(self, arguments: dict, context: dict) -> dict:
        async def _execute():
            from app.services.rag import VectorStore, SearchResult

            query = arguments["query"]
            source_types = arguments.get("source_types", ["code", "doc", "ticket", "incident"])
            top_k = arguments.get("top_k", 10)
            min_score = arguments.get("min_score", 0.5)
            organization_id = arguments.get("organization_id") or context.get("organization_id")

            if not query or len(query) < 3:
                return invalid_input_error(
                    field="query",
                    expected="at least 3 characters",
                    received=query,
                ).to_dict()

            try:
                # Get vector store (would be injected in production)
                vector_store = self._get_vector_store()

                results = await vector_store.search(
                    query=query,
                    top_k=top_k,
                    filter={
                        "source_type": {"$in": source_types},
                        "organization_id": organization_id,
                    },
                    min_score=min_score,
                )

                return {
                    "success": True,
                    "query": query,
                    "total_results": len(results),
                    "results": [
                        {
                            "id": r.id,
                            "content": r.content[:500],  # Truncate for response
                            "source": r.metadata.get("source", "unknown"),
                            "source_type": r.metadata.get("source_type", "unknown"),
                            "score": r.score,
                            "file_path": r.metadata.get("file_path"),
                            "line_start": r.metadata.get("line_start"),
                            "line_end": r.metadata.get("line_end"),
                            "url": r.metadata.get("url"),
                        }
                        for r in results
                    ],
                }

            except Exception as e:
                logger.error("RAG semantic search failed", error=str(e))
                return service_unavailable_error(
                    service_name="RAG",
                    operation="semantic_search",
                    details={"error": str(e)},
                ).to_dict()

        return await safe_tool_execute(
            _execute, operation="rag_semantic_search", service_name="rag"
        )

    def _get_vector_store(self):
        """Get or create vector store instance."""
        from app.services.rag import VectorStore

        # In production, this would be injected or retrieved from a service locator
        return VectorStore()


class RAGHybridSearchHandler(MCPToolHandler):
    """
    Perform hybrid search combining keyword and semantic search.

    Uses both BM25 keyword matching and vector similarity,
    then applies cross-encoder reranking for best results.
    """

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="rag_hybrid_search",
            description="Hybrid search using both keywords and semantic similarity",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional specific keywords to match",
                    },
                    "source_types": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["code", "doc", "ticket", "incident"]},
                        "description": "Types of sources to search",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 10,
                    },
                    "use_reranker": {
                        "type": "boolean",
                        "description": "Whether to apply cross-encoder reranking",
                        "default": True,
                    },
                    "organization_id": {
                        "type": "string",
                        "description": "Organization ID for tenant isolation",
                    },
                },
                "required": ["query"],
            },
        )

    async def execute(self, arguments: dict, context: dict) -> dict:
        async def _execute():
            from app.services.rag import HybridRetriever, RetrievalConfig

            query = arguments["query"]
            keywords = arguments.get("keywords", [])
            source_types = arguments.get("source_types", ["code", "doc", "ticket", "incident"])
            top_k = arguments.get("top_k", 10)
            use_reranker = arguments.get("use_reranker", True)
            organization_id = arguments.get("organization_id") or context.get("organization_id")

            try:
                config = RetrievalConfig(
                    top_k=top_k,
                    use_reranker=use_reranker,
                    keyword_weight=0.3,
                    semantic_weight=0.7,
                )

                retriever = HybridRetriever(config=config)

                results = await retriever.retrieve(
                    query=query,
                    keywords=keywords,
                    filters={
                        "source_type": {"$in": source_types},
                        "organization_id": organization_id,
                    },
                )

                return {
                    "success": True,
                    "query": query,
                    "keywords_used": keywords,
                    "retrieval_config": {
                        "use_reranker": use_reranker,
                        "keyword_weight": config.keyword_weight,
                        "semantic_weight": config.semantic_weight,
                    },
                    "total_results": len(results),
                    "results": [
                        {
                            "id": r.id,
                            "content": r.content[:500],
                            "source": r.metadata.get("source", "unknown"),
                            "source_type": r.metadata.get("source_type", "unknown"),
                            "score": r.score,
                            "keyword_score": r.metadata.get("keyword_score", 0),
                            "semantic_score": r.metadata.get("semantic_score", 0),
                            "rerank_score": r.metadata.get("rerank_score"),
                        }
                        for r in results
                    ],
                }

            except Exception as e:
                logger.error("RAG hybrid search failed", error=str(e))
                return service_unavailable_error(
                    service_name="RAG",
                    operation="hybrid_search",
                    details={"error": str(e)},
                ).to_dict()

        return await safe_tool_execute(
            _execute, operation="rag_hybrid_search", service_name="rag"
        )


class RAGCodeSearchHandler(MCPToolHandler):
    """
    Search specifically for code snippets and definitions.

    Optimized for finding functions, classes, methods, and
    code patterns across repositories.
    """

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="rag_code_search",
            description="Search for code snippets, functions, and definitions",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Code search query (function name, concept, etc.)",
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language filter (python, javascript, go, etc.)",
                    },
                    "code_type": {
                        "type": "string",
                        "enum": ["function", "class", "method", "variable", "import", "any"],
                        "description": "Type of code element to find",
                        "default": "any",
                    },
                    "repository": {
                        "type": "string",
                        "description": "Specific repository to search",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 10,
                    },
                    "include_context": {
                        "type": "boolean",
                        "description": "Include surrounding code context",
                        "default": True,
                    },
                    "organization_id": {
                        "type": "string",
                        "description": "Organization ID",
                    },
                },
                "required": ["query"],
            },
        )

    async def execute(self, arguments: dict, context: dict) -> dict:
        async def _execute():
            from app.services.rag import VectorStore

            query = arguments["query"]
            language = arguments.get("language")
            code_type = arguments.get("code_type", "any")
            repository = arguments.get("repository")
            top_k = arguments.get("top_k", 10)
            include_context = arguments.get("include_context", True)
            organization_id = arguments.get("organization_id") or context.get("organization_id")

            try:
                vector_store = VectorStore()

                # Build filters
                filters = {
                    "source_type": "code",
                    "organization_id": organization_id,
                }

                if language:
                    filters["language"] = language
                if code_type and code_type != "any":
                    filters["code_type"] = code_type
                if repository:
                    filters["repository"] = repository

                results = await vector_store.search(
                    query=query,
                    top_k=top_k,
                    filter=filters,
                )

                formatted_results = []
                for r in results:
                    result = {
                        "id": r.id,
                        "content": r.content,
                        "file_path": r.metadata.get("file_path"),
                        "language": r.metadata.get("language"),
                        "code_type": r.metadata.get("code_type"),
                        "name": r.metadata.get("name"),  # function/class name
                        "line_start": r.metadata.get("line_start"),
                        "line_end": r.metadata.get("line_end"),
                        "repository": r.metadata.get("repository"),
                        "score": r.score,
                    }

                    if include_context:
                        result["context_before"] = r.metadata.get("context_before", "")
                        result["context_after"] = r.metadata.get("context_after", "")

                    formatted_results.append(result)

                return {
                    "success": True,
                    "query": query,
                    "filters_applied": {
                        "language": language,
                        "code_type": code_type,
                        "repository": repository,
                    },
                    "total_results": len(formatted_results),
                    "results": formatted_results,
                }

            except Exception as e:
                logger.error("RAG code search failed", error=str(e))
                return service_unavailable_error(
                    service_name="RAG",
                    operation="code_search",
                    details={"error": str(e)},
                ).to_dict()

        return await safe_tool_execute(
            _execute, operation="rag_code_search", service_name="rag"
        )


class RAGBuildContextHandler(MCPToolHandler):
    """
    Build a context document for LLM prompts from RAG results.

    Takes a query and retrieves relevant context, formatting it
    for inclusion in an LLM prompt with proper citations.
    """

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="rag_build_context",
            description="Build LLM context from relevant retrieved documents",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query to build context for",
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens in context (default: 4000)",
                        "default": 4000,
                    },
                    "source_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Types of sources to include",
                    },
                    "include_citations": {
                        "type": "boolean",
                        "description": "Include source citations",
                        "default": True,
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "xml", "plain"],
                        "description": "Output format",
                        "default": "markdown",
                    },
                    "organization_id": {
                        "type": "string",
                        "description": "Organization ID",
                    },
                },
                "required": ["query"],
            },
        )

    async def execute(self, arguments: dict, context: dict) -> dict:
        async def _execute():
            from app.services.rag import ContextBuilder, ContextConfig

            query = arguments["query"]
            max_tokens = arguments.get("max_tokens", 4000)
            source_types = arguments.get("source_types", ["code", "doc", "ticket"])
            include_citations = arguments.get("include_citations", True)
            output_format = arguments.get("format", "markdown")
            organization_id = arguments.get("organization_id") or context.get("organization_id")

            try:
                config = ContextConfig(
                    max_tokens=max_tokens,
                    include_citations=include_citations,
                    output_format=output_format,
                )

                builder = ContextBuilder(config=config)

                result = await builder.build(
                    query=query,
                    filters={
                        "source_type": {"$in": source_types},
                        "organization_id": organization_id,
                    },
                )

                return {
                    "success": True,
                    "query": query,
                    "context": result.context,
                    "token_count": result.token_count,
                    "sources_used": result.sources_used,
                    "citations": result.citations if include_citations else None,
                    "truncated": result.truncated,
                }

            except Exception as e:
                logger.error("RAG build context failed", error=str(e))
                return service_unavailable_error(
                    service_name="RAG",
                    operation="build_context",
                    details={"error": str(e)},
                ).to_dict()

        return await safe_tool_execute(
            _execute, operation="rag_build_context", service_name="rag"
        )


class RAGIndexDocumentHandler(MCPToolHandler):
    """
    Index a document into the RAG knowledge base.

    Chunks, embeds, and stores a document for future retrieval.
    """

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="rag_index_document",
            description="Index a document into the knowledge base",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Document content to index",
                    },
                    "source_type": {
                        "type": "string",
                        "enum": ["code", "doc", "ticket", "incident"],
                        "description": "Type of document",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Document metadata (title, url, author, etc.)",
                    },
                    "document_id": {
                        "type": "string",
                        "description": "Optional ID for the document (for updates)",
                    },
                    "organization_id": {
                        "type": "string",
                        "description": "Organization ID",
                    },
                },
                "required": ["content", "source_type"],
            },
        )

    async def execute(self, arguments: dict, context: dict) -> dict:
        async def _execute():
            from app.services.rag import DocumentIndexer

            content = arguments["content"]
            source_type = arguments["source_type"]
            metadata = arguments.get("metadata", {})
            document_id = arguments.get("document_id")
            organization_id = arguments.get("organization_id") or context.get("organization_id")

            if not content or len(content) < 10:
                return invalid_input_error(
                    field="content",
                    expected="at least 10 characters",
                    received=f"{len(content)} characters",
                ).to_dict()

            try:
                indexer = DocumentIndexer()

                result = await indexer.index(
                    content=content,
                    source_type=source_type,
                    metadata={
                        **metadata,
                        "organization_id": organization_id,
                    },
                    document_id=document_id,
                )

                return {
                    "success": True,
                    "document_id": result.document_id,
                    "chunks_created": result.chunks_created,
                    "tokens_used": result.tokens_used,
                    "source_type": source_type,
                    "indexed_at": result.indexed_at.isoformat(),
                }

            except Exception as e:
                logger.error("RAG document indexing failed", error=str(e))
                return service_unavailable_error(
                    service_name="RAG",
                    operation="index_document",
                    details={"error": str(e)},
                ).to_dict()

        return await safe_tool_execute(
            _execute, operation="rag_index_document", service_name="rag"
        )


class RAGDeleteDocumentHandler(MCPToolHandler):
    """Delete a document from the RAG knowledge base."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="rag_delete_document",
            description="Delete a document and its chunks from the knowledge base",
            input_schema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "ID of the document to delete",
                    },
                    "organization_id": {
                        "type": "string",
                        "description": "Organization ID",
                    },
                },
                "required": ["document_id"],
            },
        )

    async def execute(self, arguments: dict, context: dict) -> dict:
        async def _execute():
            from app.services.rag import VectorStore

            document_id = arguments["document_id"]
            organization_id = arguments.get("organization_id") or context.get("organization_id")

            try:
                vector_store = VectorStore()

                # Delete all chunks for this document
                deleted_count = await vector_store.delete(
                    filter={
                        "document_id": document_id,
                        "organization_id": organization_id,
                    }
                )

                if deleted_count == 0:
                    return not_found_error(
                        resource_type="document",
                        identifier=document_id,
                    ).to_dict()

                return {
                    "success": True,
                    "document_id": document_id,
                    "chunks_deleted": deleted_count,
                }

            except Exception as e:
                logger.error("RAG document deletion failed", error=str(e))
                return service_unavailable_error(
                    service_name="RAG",
                    operation="delete_document",
                    details={"error": str(e)},
                ).to_dict()

        return await safe_tool_execute(
            _execute, operation="rag_delete_document", service_name="rag"
        )


class RAGGetStatsHandler(MCPToolHandler):
    """Get statistics about the RAG knowledge base."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="rag_get_stats",
            description="Get statistics about the knowledge base",
            input_schema={
                "type": "object",
                "properties": {
                    "organization_id": {
                        "type": "string",
                        "description": "Organization ID",
                    },
                },
            },
        )

    async def execute(self, arguments: dict, context: dict) -> dict:
        async def _execute():
            from app.services.rag import VectorStore

            organization_id = arguments.get("organization_id") or context.get("organization_id")

            try:
                vector_store = VectorStore()

                stats = await vector_store.get_stats(
                    filter={"organization_id": organization_id} if organization_id else None
                )

                return {
                    "success": True,
                    "organization_id": organization_id,
                    "stats": {
                        "total_documents": stats.get("total_documents", 0),
                        "total_chunks": stats.get("total_chunks", 0),
                        "by_source_type": stats.get("by_source_type", {}),
                        "by_language": stats.get("by_language", {}),
                        "storage_bytes": stats.get("storage_bytes", 0),
                        "last_indexed_at": stats.get("last_indexed_at"),
                    },
                }

            except Exception as e:
                logger.error("RAG get stats failed", error=str(e))
                return service_unavailable_error(
                    service_name="RAG",
                    operation="get_stats",
                    details={"error": str(e)},
                ).to_dict()

        return await safe_tool_execute(
            _execute, operation="rag_get_stats", service_name="rag"
        )


def get_all_rag_tool_handlers() -> list[MCPToolHandler]:
    """Get all RAG tool handlers."""
    return [
        RAGSemanticSearchHandler(),
        RAGHybridSearchHandler(),
        RAGCodeSearchHandler(),
        RAGBuildContextHandler(),
        RAGIndexDocumentHandler(),
        RAGDeleteDocumentHandler(),
        RAGGetStatsHandler(),
    ]
