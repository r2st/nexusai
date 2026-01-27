"""
Jira Tools

Integration with Jira for issue tracking.
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


class JiraSearchTool(Tool):
    """
    Search Jira issues.
    
    Supports:
    - JQL queries
    - Project filtering
    - Status filtering
    """
    
    @classmethod
    def get_metadata(cls) -> ToolMetadata:
        return ToolMetadata(
            name="jira_search",
            description="Search for Jira issues using JQL or filters. Returns matching tickets with details.",
            category=ToolCategory.INTEGRATION,
            version="1.0.0",
            parameters=[
                ToolParameter(
                    name="jql",
                    type=ParameterType.STRING,
                    description="JQL query string",
                    required=False,
                ),
                ToolParameter(
                    name="project",
                    type=ParameterType.STRING,
                    description="Project key (e.g., 'PROJ')",
                    required=False,
                ),
                ToolParameter(
                    name="status",
                    type=ParameterType.STRING,
                    description="Filter by status",
                    required=False,
                    enum=["Open", "In Progress", "In Review", "Done", "Closed"],
                ),
                ToolParameter(
                    name="assignee",
                    type=ParameterType.STRING,
                    description="Filter by assignee (email or 'unassigned')",
                    required=False,
                ),
                ToolParameter(
                    name="labels",
                    type=ParameterType.ARRAY,
                    description="Filter by labels",
                    required=False,
                ),
                ToolParameter(
                    name="max_results",
                    type=ParameterType.INTEGER,
                    description="Maximum results to return",
                    required=False,
                    default=20,
                    max_value=100,
                ),
            ],
            required_permissions=["tools.execute.integration"],
            timeout_seconds=15,
            examples=[
                {
                    "project": "BACKEND",
                    "status": "Open",
                },
                {
                    "jql": "project = BACKEND AND labels = bug AND status != Done",
                },
            ],
        )
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """Search Jira issues."""
        jql = params.get("jql")
        project = params.get("project")
        status = params.get("status")
        assignee = params.get("assignee")
        labels = params.get("labels")
        max_results = params.get("max_results", 20)
        
        try:
            issues = await self._search(
                jql=jql,
                project=project,
                status=status,
                assignee=assignee,
                labels=labels,
                max_results=max_results,
                tenant_id=context.tenant_id,
            )
            
            return ToolResult.success(
                tool_name="jira_search",
                data={
                    "issues": issues,
                    "total": len(issues),
                },
            )
            
        except Exception as e:
            return ToolResult.error(
                tool_name="jira_search",
                error=str(e),
                error_code="JIRA_ERROR",
            )
    
    async def _search(
        self,
        jql: Optional[str],
        project: Optional[str],
        status: Optional[str],
        assignee: Optional[str],
        labels: Optional[List[str]],
        max_results: int,
        tenant_id: str,
    ) -> List[Dict[str, Any]]:
        """Search Jira."""
        # Placeholder - would use Jira API
        return [
            {
                "key": "PROJ-123",
                "summary": "Fix login bug",
                "status": "Open",
                "priority": "High",
                "assignee": "john@example.com",
                "created": "2024-01-15",
                "labels": ["bug", "auth"],
            }
        ]


class JiraCreateTicketTool(Tool):
    """Create a Jira ticket."""
    
    @classmethod
    def get_metadata(cls) -> ToolMetadata:
        return ToolMetadata(
            name="jira_create_ticket",
            description="Create a new Jira ticket/issue with specified details.",
            category=ToolCategory.INTEGRATION,
            version="1.0.0",
            parameters=[
                ToolParameter(
                    name="project",
                    type=ParameterType.STRING,
                    description="Project key",
                    required=True,
                ),
                ToolParameter(
                    name="summary",
                    type=ParameterType.STRING,
                    description="Ticket title/summary",
                    required=True,
                ),
                ToolParameter(
                    name="description",
                    type=ParameterType.STRING,
                    description="Detailed description",
                    required=True,
                ),
                ToolParameter(
                    name="issue_type",
                    type=ParameterType.STRING,
                    description="Type of issue",
                    required=False,
                    default="Task",
                    enum=["Bug", "Task", "Story", "Epic", "Subtask"],
                ),
                ToolParameter(
                    name="priority",
                    type=ParameterType.STRING,
                    description="Priority level",
                    required=False,
                    default="Medium",
                    enum=["Lowest", "Low", "Medium", "High", "Highest"],
                ),
                ToolParameter(
                    name="assignee",
                    type=ParameterType.STRING,
                    description="Assignee email",
                    required=False,
                ),
                ToolParameter(
                    name="labels",
                    type=ParameterType.ARRAY,
                    description="Labels to add",
                    required=False,
                ),
                ToolParameter(
                    name="components",
                    type=ParameterType.ARRAY,
                    description="Components to associate",
                    required=False,
                ),
                ToolParameter(
                    name="parent_key",
                    type=ParameterType.STRING,
                    description="Parent issue key (for subtasks)",
                    required=False,
                ),
            ],
            required_permissions=["tools.execute.integration"],
            requires_confirmation=True,
            timeout_seconds=15,
            rate_limit_per_hour=50,
            examples=[
                {
                    "project": "BACKEND",
                    "summary": "Implement user authentication",
                    "description": "Add JWT-based authentication...",
                    "issue_type": "Story",
                    "priority": "High",
                },
            ],
        )
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """Create Jira ticket."""
        try:
            ticket = await self._create_ticket(
                project=params["project"],
                summary=params["summary"],
                description=params["description"],
                issue_type=params.get("issue_type", "Task"),
                priority=params.get("priority", "Medium"),
                assignee=params.get("assignee"),
                labels=params.get("labels"),
                components=params.get("components"),
                parent_key=params.get("parent_key"),
                tenant_id=context.tenant_id,
            )
            
            return ToolResult.success(
                tool_name="jira_create_ticket",
                data=ticket,
            )
            
        except Exception as e:
            return ToolResult.error(
                tool_name="jira_create_ticket",
                error=str(e),
                error_code="JIRA_ERROR",
            )
    
    async def _create_ticket(
        self,
        project: str,
        summary: str,
        description: str,
        issue_type: str,
        priority: str,
        assignee: Optional[str],
        labels: Optional[List[str]],
        components: Optional[List[str]],
        parent_key: Optional[str],
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Create the ticket."""
        # Placeholder
        return {
            "key": "PROJ-456",
            "self": "https://jira.example.com/rest/api/2/issue/PROJ-456",
            "url": "https://jira.example.com/browse/PROJ-456",
        }


class JiraUpdateTicketTool(Tool):
    """Update an existing Jira ticket."""
    
    @classmethod
    def get_metadata(cls) -> ToolMetadata:
        return ToolMetadata(
            name="jira_update_ticket",
            description="Update an existing Jira ticket - change status, add comments, update fields.",
            category=ToolCategory.INTEGRATION,
            version="1.0.0",
            parameters=[
                ToolParameter(
                    name="ticket_key",
                    type=ParameterType.STRING,
                    description="Ticket key (e.g., 'PROJ-123')",
                    required=True,
                ),
                ToolParameter(
                    name="status",
                    type=ParameterType.STRING,
                    description="New status (transition)",
                    required=False,
                ),
                ToolParameter(
                    name="comment",
                    type=ParameterType.STRING,
                    description="Comment to add",
                    required=False,
                ),
                ToolParameter(
                    name="assignee",
                    type=ParameterType.STRING,
                    description="New assignee",
                    required=False,
                ),
                ToolParameter(
                    name="priority",
                    type=ParameterType.STRING,
                    description="New priority",
                    required=False,
                ),
                ToolParameter(
                    name="labels_add",
                    type=ParameterType.ARRAY,
                    description="Labels to add",
                    required=False,
                ),
                ToolParameter(
                    name="labels_remove",
                    type=ParameterType.ARRAY,
                    description="Labels to remove",
                    required=False,
                ),
                ToolParameter(
                    name="link_to",
                    type=ParameterType.STRING,
                    description="Issue key to link to",
                    required=False,
                ),
                ToolParameter(
                    name="link_type",
                    type=ParameterType.STRING,
                    description="Type of link",
                    required=False,
                    enum=["blocks", "is blocked by", "relates to", "duplicates"],
                ),
            ],
            required_permissions=["tools.execute.integration"],
            timeout_seconds=15,
            examples=[
                {
                    "ticket_key": "PROJ-123",
                    "status": "In Progress",
                    "comment": "Starting work on this issue",
                },
                {
                    "ticket_key": "PROJ-123",
                    "link_to": "PROJ-456",
                    "link_type": "blocks",
                },
            ],
        )
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """Update Jira ticket."""
        try:
            result = await self._update_ticket(
                ticket_key=params["ticket_key"],
                status=params.get("status"),
                comment=params.get("comment"),
                assignee=params.get("assignee"),
                priority=params.get("priority"),
                labels_add=params.get("labels_add"),
                labels_remove=params.get("labels_remove"),
                link_to=params.get("link_to"),
                link_type=params.get("link_type"),
                tenant_id=context.tenant_id,
            )
            
            return ToolResult.success(
                tool_name="jira_update_ticket",
                data=result,
            )
            
        except Exception as e:
            return ToolResult.error(
                tool_name="jira_update_ticket",
                error=str(e),
                error_code="JIRA_ERROR",
            )
    
    async def _update_ticket(
        self,
        ticket_key: str,
        status: Optional[str],
        comment: Optional[str],
        assignee: Optional[str],
        priority: Optional[str],
        labels_add: Optional[List[str]],
        labels_remove: Optional[List[str]],
        link_to: Optional[str],
        link_type: Optional[str],
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Update the ticket."""
        # Placeholder
        return {
            "key": ticket_key,
            "updated": True,
            "changes": [],
        }
