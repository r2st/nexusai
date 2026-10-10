"""IDE Plugin API endpoints with MCP tool integration.

Provides IDE-specific endpoints that leverage MCP tools for:
- Context-aware code search
- RAG-powered documentation lookup
- DORA metrics in IDE
- Code intelligence from repository tools
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_current_user

logger = structlog.get_logger()
from app.core.database import get_db
from app.models.user import User
from app.services.mcp import get_mcp_gateway, MCPGateway

router = APIRouter(prefix="/ide", tags=["ide"])


# ============================================================================
# Request/Response Models
# ============================================================================


class ContextSearchRequest(BaseModel):
    """Request for context-aware code search."""

    query: str
    file_path: str | None = None
    language: str | None = None
    repository: str | None = None
    max_results: int = 10
    include_context: bool = True


class ContextSearchResult(BaseModel):
    """Search result with context."""

    id: str
    content: str
    file_path: str | None
    language: str | None
    score: float
    line_start: int | None
    line_end: int | None
    context_before: str | None = None
    context_after: str | None = None


class DocumentationRequest(BaseModel):
    """Request for documentation lookup."""

    symbol: str
    language: str
    file_path: str | None = None
    context: str | None = None


class DocumentationResult(BaseModel):
    """Documentation lookup result."""

    symbol: str
    documentation: str
    signature: str | None = None
    examples: list[str] = []
    related_links: list[str] = []
    source: str


class QuickMetricsResponse(BaseModel):
    """Quick metrics for IDE status bar."""

    deployment_frequency: str
    lead_time: str
    change_failure_rate: str
    mttr: str
    last_updated: str


class FileHistoryRequest(BaseModel):
    """Request for file history."""

    file_path: str
    repository: str | None = None
    max_commits: int = 10


class CommitInfo(BaseModel):
    """Git commit information."""

    sha: str
    message: str
    author: str
    timestamp: str
    additions: int
    deletions: int


class FileBlameResult(BaseModel):
    """File blame result."""

    file_path: str
    lines: list[dict[str, Any]]


class ExplainCodeRequest(BaseModel):
    """Request to explain code."""

    code: str
    language: str
    context: str | None = None
    detail_level: str = "medium"  # brief, medium, detailed


class RefactorRequest(BaseModel):
    """Request for code refactoring suggestions."""

    code: str
    language: str
    refactor_type: str | None = None  # extract_method, rename, simplify, etc.
    context: str | None = None


class TestGenerationRequest(BaseModel):
    """Request for test generation."""

    code: str
    language: str
    test_framework: str | None = None
    coverage_target: str = "happy_path"  # happy_path, edge_cases, full


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/search/context", response_model=list[ContextSearchResult])
async def context_search(
    request: ContextSearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ContextSearchResult]:
    """
    Search code with context awareness.

    Uses RAG to find relevant code snippets based on semantic similarity
    and includes surrounding context for better understanding.
    """
    gateway = get_mcp_gateway()
    gateway.set_db_session(db)

    context = {
        "user_id": str(user.id),
        "roles": [user.role],
    }

    result = await gateway.invoke_tool(
        tool_name="rag_code_search",
        arguments={
            "query": request.query,
            "language": request.language,
            "repository": request.repository,
            "top_k": request.max_results,
            "include_context": request.include_context,
        },
        context=context,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", {}).get("message", "Search failed"),
        )

    return [
        ContextSearchResult(
            id=r.get("id", ""),
            content=r.get("content", ""),
            file_path=r.get("file_path"),
            language=r.get("language"),
            score=r.get("score", 0),
            line_start=r.get("line_start"),
            line_end=r.get("line_end"),
            context_before=r.get("context_before"),
            context_after=r.get("context_after"),
        )
        for r in result.get("result", {}).get("results", [])
    ]


@router.post("/docs/lookup", response_model=DocumentationResult)
async def lookup_documentation(
    request: DocumentationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentationResult:
    """
    Look up documentation for a symbol.

    Uses RAG to find relevant documentation from indexed docs,
    code comments, and external sources.
    """
    gateway = get_mcp_gateway()
    gateway.set_db_session(db)

    context = {
        "user_id": str(user.id),
        "roles": [user.role],
    }

    # Build a documentation query
    query = f"{request.symbol} {request.language} documentation"
    if request.context:
        query += f" {request.context}"

    result = await gateway.invoke_tool(
        tool_name="rag_semantic_search",
        arguments={
            "query": query,
            "source_types": ["doc", "code"],
            "top_k": 5,
            "min_score": 0.6,
        },
        context=context,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", {}).get("message", "Documentation lookup failed"),
        )

    results = result.get("result", {}).get("results", [])

    # Combine results into documentation
    if results:
        doc_content = results[0].get("content", "No documentation found")
        source = results[0].get("source", "RAG")
    else:
        doc_content = "No documentation found for this symbol"
        source = "none"

    return DocumentationResult(
        symbol=request.symbol,
        documentation=doc_content,
        signature=None,  # Would be extracted from code analysis
        examples=[],
        related_links=[],
        source=source,
    )


@router.get("/metrics/quick", response_model=QuickMetricsResponse)
async def get_quick_metrics(
    repository: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuickMetricsResponse:
    """
    Get quick DORA metrics for IDE status bar.

    Returns condensed metrics suitable for display in the IDE status bar.
    """
    gateway = get_mcp_gateway()
    gateway.set_db_session(db)

    context = {
        "user_id": str(user.id),
        "roles": [user.role],
    }

    result = await gateway.invoke_tool(
        tool_name="devlake_get_dora_metrics",
        arguments={
            "time_range": "30d",
            "repository": repository,
        },
        context=context,
    )

    if not result.get("success"):
        # Return placeholder metrics if DevLake unavailable
        return QuickMetricsResponse(
            deployment_frequency="--",
            lead_time="--",
            change_failure_rate="--",
            mttr="--",
            last_updated="unavailable",
        )

    metrics = result.get("result", {}).get("metrics", {})

    return QuickMetricsResponse(
        deployment_frequency=_format_frequency(metrics.get("deployment_frequency")),
        lead_time=_format_duration(metrics.get("lead_time_for_changes")),
        change_failure_rate=_format_percentage(metrics.get("change_failure_rate")),
        mttr=_format_duration(metrics.get("time_to_restore_service")),
        last_updated=result.get("result", {}).get("last_updated", "unknown"),
    )


@router.post("/history/file", response_model=list[CommitInfo])
async def get_file_history(
    request: FileHistoryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CommitInfo]:
    """
    Get commit history for a file.

    Returns recent commits that modified the specified file.
    """
    gateway = get_mcp_gateway()
    gateway.set_db_session(db)

    context = {
        "user_id": str(user.id),
        "roles": [user.role],
    }

    result = await gateway.invoke_tool(
        tool_name="repo_list_commits",
        arguments={
            "file_path": request.file_path,
            "repository": request.repository,
            "limit": request.max_commits,
        },
        context=context,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", {}).get("message", "Failed to get file history"),
        )

    commits = result.get("result", {}).get("commits", [])

    return [
        CommitInfo(
            sha=c.get("sha", ""),
            message=c.get("message", ""),
            author=c.get("author", ""),
            timestamp=c.get("timestamp", ""),
            additions=c.get("additions", 0),
            deletions=c.get("deletions", 0),
        )
        for c in commits
    ]


@router.get("/blame/{file_path:path}", response_model=FileBlameResult)
async def get_file_blame(
    file_path: str,
    repository: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileBlameResult:
    """
    Get blame information for a file.

    Returns line-by-line attribution showing who last modified each line.
    """
    gateway = get_mcp_gateway()
    gateway.set_db_session(db)

    context = {
        "user_id": str(user.id),
        "roles": [user.role],
    }

    result = await gateway.invoke_tool(
        tool_name="repo_get_blame",
        arguments={
            "file_path": file_path,
            "repository": repository,
        },
        context=context,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", {}).get("message", "Failed to get blame"),
        )

    return FileBlameResult(
        file_path=file_path,
        lines=result.get("result", {}).get("lines", []),
    )


@router.post("/ai/explain")
async def explain_code(
    request: ExplainCodeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get AI explanation for code.

    Provides a natural language explanation of what the code does,
    with varying levels of detail.
    """
    gateway = get_mcp_gateway()
    gateway.set_db_session(db)

    context = {
        "user_id": str(user.id),
        "roles": [user.role],
    }

    # First, get relevant context from RAG
    rag_result = await gateway.invoke_tool(
        tool_name="rag_build_context",
        arguments={
            "query": f"explain {request.language} code: {request.code[:200]}",
            "max_tokens": 2000,
            "source_types": ["code", "doc"],
        },
        context=context,
    )

    rag_context = ""
    if rag_result.get("success"):
        rag_context = rag_result.get("result", {}).get("context", "")

    # Return the explanation prompt for the LLM
    # In production, this would call the LLM with the RAG context
    return {
        "success": True,
        "code": request.code,
        "language": request.language,
        "detail_level": request.detail_level,
        "rag_context": rag_context[:500] if rag_context else None,
        "explanation_prompt": f"""Explain the following {request.language} code at a {request.detail_level} level of detail:

```{request.language}
{request.code}
```

{f'Context from documentation: {rag_context[:500]}' if rag_context else ''}

Provide a clear, concise explanation.""",
    }


@router.post("/ai/refactor")
async def suggest_refactoring(
    request: RefactorRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get AI refactoring suggestions.

    Analyzes code and suggests improvements or refactoring opportunities.
    """
    return {
        "success": True,
        "code": request.code,
        "language": request.language,
        "refactor_type": request.refactor_type,
        "refactoring_prompt": f"""Suggest refactoring improvements for the following {request.language} code:

```{request.language}
{request.code}
```

{f'Refactoring type requested: {request.refactor_type}' if request.refactor_type else 'Suggest any improvements.'}

Provide:
1. Identified issues or areas for improvement
2. Suggested refactored code
3. Explanation of changes""",
    }


@router.post("/ai/generate-tests")
async def generate_tests(
    request: TestGenerationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Generate tests for code.

    Creates test cases based on the provided code and test framework.
    """
    return {
        "success": True,
        "code": request.code,
        "language": request.language,
        "test_framework": request.test_framework,
        "coverage_target": request.coverage_target,
        "test_prompt": f"""Generate {request.coverage_target} tests for the following {request.language} code:

```{request.language}
{request.code}
```

{f'Using test framework: {request.test_framework}' if request.test_framework else ''}

Coverage target: {request.coverage_target}

Provide complete, runnable test code.""",
    }


@router.get("/tools")
async def list_available_tools(
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    List MCP tools available for IDE integration.

    Returns tools that can be invoked through the IDE plugin.
    """
    from app.services.mcp import get_all_tools_summary

    summary = get_all_tools_summary()

    # Filter to IDE-relevant tools
    ide_relevant_services = ["rag", "repo", "ci", "devlake"]

    return {
        "total_tools": sum(
            summary["services"][s]["tool_count"]
            for s in ide_relevant_services
            if s in summary["services"]
        ),
        "services": {
            service: summary["services"][service]
            for service in ide_relevant_services
            if service in summary["services"]
        },
        "service_descriptions": {
            service: summary["service_descriptions"][service]
            for service in ide_relevant_services
            if service in summary["service_descriptions"]
        },
    }


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Check IDE MCP service health."""
    return {"status": "healthy", "service": "ide-mcp"}


# ============================================================================
# Helper Functions
# ============================================================================


def _format_frequency(value: float | None) -> str:
    """Format deployment frequency for display."""
    if value is None:
        return "--"
    if value >= 1:
        return f"{value:.1f}/day"
    if value >= 0.14:  # ~1/week
        return f"{value * 7:.1f}/week"
    return f"{value * 30:.1f}/month"


def _format_duration(value: float | None) -> str:
    """Format duration (in hours) for display."""
    if value is None:
        return "--"
    if value < 1:
        return f"{value * 60:.0f}m"
    if value < 24:
        return f"{value:.1f}h"
    return f"{value / 24:.1f}d"


def _format_percentage(value: float | None) -> str:
    """Format percentage for display."""
    if value is None:
        return "--"
    return f"{value:.1f}%"
