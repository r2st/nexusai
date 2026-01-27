"""
Static Analysis Tool

Run static analysis on code.
"""

from typing import Any, Dict, List, Optional
from ..base import (
    Tool,
    ToolMetadata,
    ToolParameter,
    ToolCategory,
    ToolResult,
    ParameterType,
    ExecutionContext,
)


class StaticAnalysisTool(Tool):
    """
    Run static analysis on code.
    
    Supports:
    - Linting (syntax, style)
    - Security scanning (SAST)
    - Complexity metrics
    - Code smells detection
    """
    
    @classmethod
    def get_metadata(cls) -> ToolMetadata:
        return ToolMetadata(
            name="run_static_analysis",
            description="Run static analysis on code to find issues, security vulnerabilities, and code quality problems.",
            category=ToolCategory.ANALYSIS,
            version="1.0.0",
            parameters=[
                ToolParameter(
                    name="repo",
                    type=ParameterType.STRING,
                    description="Repository to analyze",
                    required=True,
                ),
                ToolParameter(
                    name="scope",
                    type=ParameterType.STRING,
                    description="Scope of analysis",
                    required=False,
                    default="changed",
                    enum=["changed", "file", "directory", "full"],
                ),
                ToolParameter(
                    name="path",
                    type=ParameterType.STRING,
                    description="Specific path to analyze (for file/directory scope)",
                    required=False,
                ),
                ToolParameter(
                    name="pr_number",
                    type=ParameterType.INTEGER,
                    description="PR number (for changed scope)",
                    required=False,
                ),
                ToolParameter(
                    name="analysis_types",
                    type=ParameterType.ARRAY,
                    description="Types of analysis to run",
                    required=False,
                    items_type=ParameterType.STRING,
                ),
                ToolParameter(
                    name="severity_threshold",
                    type=ParameterType.STRING,
                    description="Minimum severity to report",
                    required=False,
                    default="warning",
                    enum=["info", "warning", "error", "critical"],
                ),
            ],
            required_permissions=["tools.execute.integration"],
            timeout_seconds=120,
            rate_limit_per_minute=10,
            examples=[
                {
                    "repo": "myorg/backend",
                    "scope": "changed",
                    "pr_number": 123,
                },
                {
                    "repo": "myorg/backend",
                    "scope": "file",
                    "path": "src/auth/login.py",
                    "analysis_types": ["security", "lint"],
                },
            ],
        )
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """Run static analysis."""
        repo = params["repo"]
        scope = params.get("scope", "changed")
        path = params.get("path")
        pr_number = params.get("pr_number")
        analysis_types = params.get("analysis_types", ["lint", "security", "complexity"])
        severity_threshold = params.get("severity_threshold", "warning")
        
        try:
            results = await self._run_analysis(
                repo=repo,
                scope=scope,
                path=path,
                pr_number=pr_number,
                analysis_types=analysis_types,
                severity_threshold=severity_threshold,
                tenant_id=context.tenant_id,
            )
            
            return ToolResult.success(
                tool_name="run_static_analysis",
                data=results,
            )
            
        except Exception as e:
            return ToolResult.error(
                tool_name="run_static_analysis",
                error=str(e),
                error_code="ANALYSIS_ERROR",
            )
    
    async def _run_analysis(
        self,
        repo: str,
        scope: str,
        path: Optional[str],
        pr_number: Optional[int],
        analysis_types: List[str],
        severity_threshold: str,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Run the analysis."""
        # Placeholder - would use security scanner service
        return {
            "repo": repo,
            "scope": scope,
            "files_analyzed": 15,
            "issues": [
                {
                    "type": "security",
                    "severity": "warning",
                    "file": "src/auth/login.py",
                    "line": 45,
                    "message": "Potential SQL injection vulnerability",
                    "rule": "SEC-001",
                },
            ],
            "summary": {
                "critical": 0,
                "error": 1,
                "warning": 3,
                "info": 5,
            },
        }
