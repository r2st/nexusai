"""
Diff Viewer Tool

Get and analyze diffs from PRs and commits.
"""

from typing import Any, Dict, Optional
from ..base import (
    Tool,
    ToolMetadata,
    ToolParameter,
    ToolCategory,
    ToolResult,
    ParameterType,
    ExecutionContext,
)


class DiffViewerTool(Tool):
    """
    View diffs from pull requests or commits.
    
    Supports:
    - PR diffs
    - Commit diffs
    - File-specific diffs
    - Diff statistics
    """
    
    @classmethod
    def get_metadata(cls) -> ToolMetadata:
        return ToolMetadata(
            name="get_diff",
            description="Get the diff (code changes) from a pull request or commit. Returns file changes, additions, and deletions.",
            category=ToolCategory.CODE,
            version="1.0.0",
            parameters=[
                ToolParameter(
                    name="repo",
                    type=ParameterType.STRING,
                    description="Repository (e.g., 'owner/repo')",
                    required=True,
                ),
                ToolParameter(
                    name="pr_number",
                    type=ParameterType.INTEGER,
                    description="Pull request number",
                    required=False,
                ),
                ToolParameter(
                    name="commit_sha",
                    type=ParameterType.STRING,
                    description="Commit SHA (if not using PR)",
                    required=False,
                ),
                ToolParameter(
                    name="file_path",
                    type=ParameterType.STRING,
                    description="Specific file to get diff for (optional)",
                    required=False,
                ),
                ToolParameter(
                    name="context_lines",
                    type=ParameterType.INTEGER,
                    description="Number of context lines around changes",
                    required=False,
                    default=3,
                    min_value=0,
                    max_value=20,
                ),
            ],
            required_permissions=["tools.execute.basic"],
            timeout_seconds=30,
            examples=[
                {
                    "repo": "myorg/backend",
                    "pr_number": 123,
                },
                {
                    "repo": "myorg/backend",
                    "commit_sha": "abc123",
                    "file_path": "src/api/users.py",
                },
            ],
        )
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """Get diff for PR or commit."""
        repo = params["repo"]
        pr_number = params.get("pr_number")
        commit_sha = params.get("commit_sha")
        file_path = params.get("file_path")
        context_lines = params.get("context_lines", 3)
        
        if not pr_number and not commit_sha:
            return ToolResult.error(
                tool_name="get_diff",
                error="Either pr_number or commit_sha is required",
                error_code="MISSING_PARAM",
            )
        
        try:
            # TODO: Implement actual diff retrieval via GitHub/GitLab API
            diff_data = await self._get_diff(
                repo=repo,
                pr_number=pr_number,
                commit_sha=commit_sha,
                file_path=file_path,
                context_lines=context_lines,
                tenant_id=context.tenant_id,
            )
            
            return ToolResult.success(
                tool_name="get_diff",
                data=diff_data,
            )
            
        except Exception as e:
            return ToolResult.error(
                tool_name="get_diff",
                error=str(e),
                error_code="DIFF_ERROR",
            )
    
    async def _get_diff(
        self,
        repo: str,
        pr_number: Optional[int],
        commit_sha: Optional[str],
        file_path: Optional[str],
        context_lines: int,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Retrieve the diff via the appropriate VCS connector."""
        try:
            from app.services.connectors.github import GitHubConnector

            connector = GitHubConnector(tenant_id=tenant_id)
            if pr_number:
                return await connector.get_pr_diff(
                    repo=repo,
                    pr_number=pr_number,
                    file_path=file_path,
                    context_lines=context_lines,
                )
            elif commit_sha:
                return await connector.get_commit_diff(
                    repo=repo,
                    commit_sha=commit_sha,
                    file_path=file_path,
                    context_lines=context_lines,
                )
            else:
                return {"error": "Either pr_number or commit_sha is required", "files": []}
        except (ImportError, Exception) as e:
            return {
                "repo": repo,
                "error": f"VCS connector unavailable: {e}",
                "files": [],
            }
