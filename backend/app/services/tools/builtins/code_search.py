"""
Code Search Tool

Search code across repositories with semantic and keyword search.
"""

from typing import Any, Dict, List, Optional
from ..base import (
    Tool,
    ToolMetadata,
    ToolParameter,
    ToolCategory,
    ToolResult,
    ToolResultStatus,
    ParameterType,
    ExecutionContext,
)


class CodeSearchTool(Tool):
    """
    Search code in repositories.
    
    Supports:
    - Keyword search (grep-like)
    - Semantic search (vector similarity)
    - Symbol search (functions, classes, variables)
    - File path search
    """
    
    @classmethod
    def get_metadata(cls) -> ToolMetadata:
        return ToolMetadata(
            name="search_code",
            description="Search for code across repositories. Supports keyword search, semantic search, and symbol search.",
            category=ToolCategory.SEARCH,
            version="1.0.0",
            parameters=[
                ToolParameter(
                    name="query",
                    type=ParameterType.STRING,
                    description="The search query - can be keywords, code snippet, or natural language",
                    required=True,
                ),
                ToolParameter(
                    name="repo",
                    type=ParameterType.STRING,
                    description="Repository to search in (e.g., 'owner/repo'). If not specified, searches all accessible repos.",
                    required=False,
                ),
                ToolParameter(
                    name="branch",
                    type=ParameterType.STRING,
                    description="Branch to search (default: main/master)",
                    required=False,
                    default="main",
                ),
                ToolParameter(
                    name="search_type",
                    type=ParameterType.STRING,
                    description="Type of search to perform",
                    required=False,
                    default="hybrid",
                    enum=["keyword", "semantic", "symbol", "hybrid"],
                ),
                ToolParameter(
                    name="file_pattern",
                    type=ParameterType.STRING,
                    description="Glob pattern to filter files (e.g., '*.py', 'src/**/*.ts')",
                    required=False,
                ),
                ToolParameter(
                    name="max_results",
                    type=ParameterType.INTEGER,
                    description="Maximum number of results to return",
                    required=False,
                    default=10,
                    min_value=1,
                    max_value=100,
                ),
            ],
            required_permissions=["tools.execute.basic"],
            timeout_seconds=30,
            rate_limit_per_minute=60,
            examples=[
                {
                    "query": "authentication middleware",
                    "repo": "myorg/backend",
                    "search_type": "semantic",
                },
                {
                    "query": "def process_payment",
                    "file_pattern": "*.py",
                    "search_type": "keyword",
                },
            ],
        )
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """Execute code search."""
        query = params["query"]
        repo = params.get("repo")
        branch = params.get("branch", "main")
        search_type = params.get("search_type", "hybrid")
        file_pattern = params.get("file_pattern")
        max_results = params.get("max_results", 10)
        
        try:
            # TODO: Implement actual search using RAG service
            # For now, return mock results
            results = await self._search(
                query=query,
                repo=repo,
                branch=branch,
                search_type=search_type,
                file_pattern=file_pattern,
                max_results=max_results,
                tenant_id=context.tenant_id,
            )
            
            return ToolResult.success(
                tool_name="search_code",
                data={
                    "query": query,
                    "results": results,
                    "total_count": len(results),
                    "search_type": search_type,
                },
            )
            
        except Exception as e:
            return ToolResult.error(
                tool_name="search_code",
                error=str(e),
                error_code="SEARCH_ERROR",
            )
    
    async def _search(
        self,
        query: str,
        repo: Optional[str],
        branch: str,
        search_type: str,
        file_pattern: Optional[str],
        max_results: int,
        tenant_id: str,
    ) -> List[Dict[str, Any]]:
        """Perform the actual search."""
        # This would integrate with the RAG service
        # Placeholder implementation
        return [
            {
                "file": "src/auth/middleware.py",
                "repo": repo or "example/repo",
                "branch": branch,
                "line_start": 45,
                "line_end": 67,
                "content": "def authenticate_request(request):\n    ...",
                "score": 0.95,
                "match_type": search_type,
            }
        ]
