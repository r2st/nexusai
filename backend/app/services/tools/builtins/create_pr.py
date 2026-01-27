"""
Create PR Tool

Create pull requests with patches.
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


class CreatePRTool(Tool):
    """
    Create a pull request with code changes.
    
    Supports:
    - Creating PRs with patches
    - Adding reviewers
    - Setting labels
    - Linking to issues
    """
    
    @classmethod
    def get_metadata(cls) -> ToolMetadata:
        return ToolMetadata(
            name="create_pr",
            description="Create a pull request with code changes. Can apply patches, set reviewers, and link to issues.",
            category=ToolCategory.CODE,
            version="1.0.0",
            parameters=[
                ToolParameter(
                    name="repo",
                    type=ParameterType.STRING,
                    description="Target repository",
                    required=True,
                ),
                ToolParameter(
                    name="title",
                    type=ParameterType.STRING,
                    description="PR title",
                    required=True,
                ),
                ToolParameter(
                    name="body",
                    type=ParameterType.STRING,
                    description="PR description",
                    required=True,
                ),
                ToolParameter(
                    name="base_branch",
                    type=ParameterType.STRING,
                    description="Base branch to merge into",
                    required=False,
                    default="main",
                ),
                ToolParameter(
                    name="head_branch",
                    type=ParameterType.STRING,
                    description="Branch with changes (will be created if using patches)",
                    required=True,
                ),
                ToolParameter(
                    name="patches",
                    type=ParameterType.ARRAY,
                    description="Array of patches to apply [{file, content, operation}]",
                    required=False,
                ),
                ToolParameter(
                    name="reviewers",
                    type=ParameterType.ARRAY,
                    description="GitHub usernames to request review from",
                    required=False,
                ),
                ToolParameter(
                    name="labels",
                    type=ParameterType.ARRAY,
                    description="Labels to add to the PR",
                    required=False,
                ),
                ToolParameter(
                    name="linked_issues",
                    type=ParameterType.ARRAY,
                    description="Issue numbers to link",
                    required=False,
                ),
                ToolParameter(
                    name="draft",
                    type=ParameterType.BOOLEAN,
                    description="Create as draft PR",
                    required=False,
                    default=False,
                ),
            ],
            required_permissions=["tools.execute.integration"],
            min_role="member",
            requires_confirmation=True,  # Human-in-the-loop
            timeout_seconds=60,
            rate_limit_per_hour=20,
            examples=[
                {
                    "repo": "myorg/backend",
                    "title": "Fix authentication bug",
                    "body": "This PR fixes the login issue...",
                    "head_branch": "fix/auth-bug",
                    "patches": [
                        {
                            "file": "src/auth/login.py",
                            "content": "...",
                            "operation": "modify",
                        }
                    ],
                    "linked_issues": [123],
                },
            ],
        )
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """Create a pull request."""
        repo = params["repo"]
        title = params["title"]
        body = params["body"]
        base_branch = params.get("base_branch", "main")
        head_branch = params["head_branch"]
        patches = params.get("patches", [])
        reviewers = params.get("reviewers", [])
        labels = params.get("labels", [])
        linked_issues = params.get("linked_issues", [])
        draft = params.get("draft", False)
        
        try:
            # Create branch and apply patches if provided
            if patches:
                await self._apply_patches(
                    repo=repo,
                    branch=head_branch,
                    base=base_branch,
                    patches=patches,
                    tenant_id=context.tenant_id,
                )
            
            # Create the PR
            pr = await self._create_pr(
                repo=repo,
                title=title,
                body=body,
                base_branch=base_branch,
                head_branch=head_branch,
                reviewers=reviewers,
                labels=labels,
                linked_issues=linked_issues,
                draft=draft,
                tenant_id=context.tenant_id,
            )
            
            return ToolResult.success(
                tool_name="create_pr",
                data=pr,
            )
            
        except Exception as e:
            return ToolResult.error(
                tool_name="create_pr",
                error=str(e),
                error_code="PR_ERROR",
            )
    
    async def _apply_patches(
        self,
        repo: str,
        branch: str,
        base: str,
        patches: List[Dict[str, Any]],
        tenant_id: str,
    ) -> None:
        """Apply patches to create/update files."""
        # Placeholder - would use GitHub API
        pass
    
    async def _create_pr(
        self,
        repo: str,
        title: str,
        body: str,
        base_branch: str,
        head_branch: str,
        reviewers: List[str],
        labels: List[str],
        linked_issues: List[int],
        draft: bool,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Create the pull request."""
        # Placeholder - would use GitHub API
        return {
            "number": 456,
            "url": f"https://github.com/{repo}/pull/456",
            "title": title,
            "state": "open",
            "draft": draft,
            "created_at": "2024-01-19T10:00:00Z",
            "head": head_branch,
            "base": base_branch,
        }
