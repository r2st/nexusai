"""
File Reader Tool

Read file contents from repositories.
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


class FileReaderTool(Tool):
    """
    Read file contents from a repository.
    
    Supports:
    - Full file read
    - Line range read
    - Multiple files
    """
    
    @classmethod
    def get_metadata(cls) -> ToolMetadata:
        return ToolMetadata(
            name="read_file",
            description="Read the contents of a file from a repository. Can read full files or specific line ranges.",
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
                    name="path",
                    type=ParameterType.STRING,
                    description="Path to the file in the repository",
                    required=True,
                ),
                ToolParameter(
                    name="branch",
                    type=ParameterType.STRING,
                    description="Branch to read from",
                    required=False,
                    default="main",
                ),
                ToolParameter(
                    name="start_line",
                    type=ParameterType.INTEGER,
                    description="Start line number (1-indexed)",
                    required=False,
                    min_value=1,
                ),
                ToolParameter(
                    name="end_line",
                    type=ParameterType.INTEGER,
                    description="End line number (inclusive)",
                    required=False,
                    min_value=1,
                ),
            ],
            required_permissions=["tools.execute.basic"],
            timeout_seconds=15,
            examples=[
                {
                    "repo": "myorg/backend",
                    "path": "src/main.py",
                },
                {
                    "repo": "myorg/backend",
                    "path": "src/api/users.py",
                    "start_line": 10,
                    "end_line": 50,
                },
            ],
        )
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """Read file contents."""
        repo = params["repo"]
        path = params["path"]
        branch = params.get("branch", "main")
        start_line = params.get("start_line")
        end_line = params.get("end_line")
        
        try:
            content = await self._read_file(
                repo=repo,
                path=path,
                branch=branch,
                start_line=start_line,
                end_line=end_line,
                tenant_id=context.tenant_id,
            )
            
            return ToolResult.success(
                tool_name="read_file",
                data={
                    "repo": repo,
                    "path": path,
                    "branch": branch,
                    "content": content["content"],
                    "total_lines": content["total_lines"],
                    "start_line": start_line or 1,
                    "end_line": end_line or content["total_lines"],
                    "language": content.get("language"),
                },
            )
            
        except Exception as e:
            return ToolResult.error(
                tool_name="read_file",
                error=str(e),
                error_code="READ_ERROR",
            )
    
    async def _read_file(
        self,
        repo: str,
        path: str,
        branch: str,
        start_line: Optional[int],
        end_line: Optional[int],
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Read the file contents."""
        # Placeholder - would use GitHub/GitLab connector
        return {
            "content": "# Example file content\n...",
            "total_lines": 100,
            "language": "python",
        }
