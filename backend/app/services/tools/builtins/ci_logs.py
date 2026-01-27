"""
CI Logs Tool

Access CI/CD build logs and test results.
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


class CILogsTool(Tool):
    """
    Access CI/CD build logs and test results.
    
    Supports:
    - Build logs
    - Test results
    - Failure analysis
    - Flakiness detection
    """
    
    @classmethod
    def get_metadata(cls) -> ToolMetadata:
        return ToolMetadata(
            name="get_ci_logs",
            description="Get CI/CD build logs, test results, and failure information. Useful for debugging failed builds.",
            category=ToolCategory.CI_CD,
            version="1.0.0",
            parameters=[
                ToolParameter(
                    name="repo",
                    type=ParameterType.STRING,
                    description="Repository",
                    required=True,
                ),
                ToolParameter(
                    name="build_id",
                    type=ParameterType.STRING,
                    description="Build/workflow run ID",
                    required=False,
                ),
                ToolParameter(
                    name="pr_number",
                    type=ParameterType.INTEGER,
                    description="PR number (gets latest build)",
                    required=False,
                ),
                ToolParameter(
                    name="branch",
                    type=ParameterType.STRING,
                    description="Branch name (gets latest build)",
                    required=False,
                ),
                ToolParameter(
                    name="log_type",
                    type=ParameterType.STRING,
                    description="Type of logs to retrieve",
                    required=False,
                    default="all",
                    enum=["all", "failed", "tests", "summary"],
                ),
                ToolParameter(
                    name="max_lines",
                    type=ParameterType.INTEGER,
                    description="Maximum log lines to return",
                    required=False,
                    default=500,
                    max_value=5000,
                ),
            ],
            required_permissions=["tools.execute.integration"],
            timeout_seconds=30,
            examples=[
                {
                    "repo": "myorg/backend",
                    "pr_number": 123,
                    "log_type": "failed",
                },
                {
                    "repo": "myorg/backend",
                    "build_id": "12345",
                    "log_type": "tests",
                },
            ],
        )
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """Get CI logs."""
        repo = params["repo"]
        build_id = params.get("build_id")
        pr_number = params.get("pr_number")
        branch = params.get("branch")
        log_type = params.get("log_type", "all")
        max_lines = params.get("max_lines", 500)
        
        if not build_id and not pr_number and not branch:
            return ToolResult.error(
                tool_name="get_ci_logs",
                error="One of build_id, pr_number, or branch is required",
                error_code="MISSING_PARAM",
            )
        
        try:
            logs = await self._get_logs(
                repo=repo,
                build_id=build_id,
                pr_number=pr_number,
                branch=branch,
                log_type=log_type,
                max_lines=max_lines,
                tenant_id=context.tenant_id,
            )
            
            return ToolResult.success(
                tool_name="get_ci_logs",
                data=logs,
            )
            
        except Exception as e:
            return ToolResult.error(
                tool_name="get_ci_logs",
                error=str(e),
                error_code="CI_ERROR",
            )
    
    async def _get_logs(
        self,
        repo: str,
        build_id: Optional[str],
        pr_number: Optional[int],
        branch: Optional[str],
        log_type: str,
        max_lines: int,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Retrieve CI logs."""
        # Placeholder - would use GitHub Actions / Jenkins / etc.
        return {
            "repo": repo,
            "build_id": build_id or "auto-detected",
            "status": "failed",
            "duration_seconds": 342,
            "started_at": "2024-01-19T10:00:00Z",
            "completed_at": "2024-01-19T10:05:42Z",
            "jobs": [
                {
                    "name": "test",
                    "status": "failed",
                    "steps": [
                        {"name": "checkout", "status": "success"},
                        {"name": "install", "status": "success"},
                        {"name": "test", "status": "failed"},
                    ],
                }
            ],
            "failed_tests": [
                {
                    "name": "test_user_login",
                    "file": "tests/test_auth.py",
                    "error": "AssertionError: Expected 200, got 401",
                    "is_flaky": False,
                }
            ],
            "logs": "... truncated build logs ...",
        }
