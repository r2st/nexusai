"""
Jira MCP Tool Handlers

Provides tools for ticket management, sprint tracking, and issue analytics
through MCP for AI assistant integration.
"""

import logging
import re
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from .server import MCPToolHandler
from .protocol import MCPTool
from .errors import (
    service_unavailable_error,
    not_found_error,
    connection_error,
    internal_error,
    invalid_input_error,
    auth_required_error,
    ToolErrorResponse,
    ErrorCategory,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

class IssueType(str, Enum):
    """Jira issue types."""

    EPIC = "Epic"
    STORY = "Story"
    TASK = "Task"
    BUG = "Bug"
    SUBTASK = "Sub-task"
    IMPROVEMENT = "Improvement"


class IssueStatus(str, Enum):
    """Jira issue statuses."""

    BACKLOG = "Backlog"
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    IN_REVIEW = "In Review"
    DONE = "Done"
    CLOSED = "Closed"


class IssuePriority(str, Enum):
    """Jira issue priorities."""

    HIGHEST = "Highest"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    LOWEST = "Lowest"


@dataclass
class JiraUser:
    """Jira user."""

    account_id: str
    display_name: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None


@dataclass
class JiraIssue:
    """Jira issue."""

    key: str
    id: str
    summary: str
    description: Optional[str]
    issue_type: IssueType
    status: IssueStatus
    priority: IssuePriority
    assignee: Optional[JiraUser]
    reporter: JiraUser
    project_key: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    labels: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)
    story_points: Optional[int] = None
    parent_key: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    linked_issues: List[Dict] = field(default_factory=list)
    comments_count: int = 0


@dataclass
class JiraSprint:
    """Jira sprint."""

    id: int
    name: str
    state: str  # active, future, closed
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    goal: Optional[str]
    board_id: int


@dataclass
class JiraProject:
    """Jira project."""

    key: str
    id: str
    name: str
    description: Optional[str]
    lead: JiraUser
    issue_types: List[str]
    url: str


# =============================================================================
# Jira Service (Mock Implementation)
# =============================================================================

class JiraService:
    """Service for Jira ticket management."""

    def __init__(self):
        self._projects: Dict[str, JiraProject] = {}
        self._issues: Dict[str, JiraIssue] = {}
        self._sprints: Dict[int, JiraSprint] = {}
        self._users: Dict[str, JiraUser] = {}
        self._generate_sample_data()

    def _generate_sample_data(self):
        """Generate sample Jira data for demonstration."""
        import random
        from uuid import uuid4

        # Create users
        user_names = ["Alice Smith", "Bob Johnson", "Charlie Brown", "Diana Ross"]
        for name in user_names:
            user_id = str(uuid4())[:8]
            self._users[user_id] = JiraUser(
                account_id=user_id,
                display_name=name,
                email=f"{name.split()[0].lower()}@example.com",
            )

        users = list(self._users.values())

        # Create projects
        projects_data = [
            ("NEXUS", "NexusAI Platform", "Main NexusAI development"),
            ("DEVOPS", "DevOps Tools", "DevOps and infrastructure"),
            ("DOC", "Documentation", "Documentation and guides"),
        ]

        for key, name, desc in projects_data:
            self._projects[key] = JiraProject(
                key=key,
                id=str(uuid4())[:8],
                name=name,
                description=desc,
                lead=random.choice(users),
                issue_types=[t.value for t in IssueType],
                url=f"https://jira.example.com/projects/{key}",
            )

        # Create sprints
        for i, state in enumerate(["closed", "active", "future"]):
            start = datetime.now(UTC) - timedelta(weeks=2-i)
            self._sprints[100 + i] = JiraSprint(
                id=100 + i,
                name=f"Sprint {10 + i}",
                state=state,
                start_date=start if state != "future" else start + timedelta(weeks=2),
                end_date=start + timedelta(weeks=2) if state != "future" else start + timedelta(weeks=4),
                goal="Complete core features" if state == "active" else None,
                board_id=1,
            )

        # Create issues
        issue_summaries = [
            ("NEXUS", IssueType.EPIC, "Implement MCP Integration"),
            ("NEXUS", IssueType.STORY, "Add user authentication"),
            ("NEXUS", IssueType.STORY, "Create dashboard UI"),
            ("NEXUS", IssueType.BUG, "Fix login redirect issue"),
            ("NEXUS", IssueType.TASK, "Update dependencies"),
            ("NEXUS", IssueType.STORY, "Implement DORA metrics"),
            ("NEXUS", IssueType.BUG, "Memory leak in worker"),
            ("DEVOPS", IssueType.TASK, "Set up CI/CD pipeline"),
            ("DEVOPS", IssueType.STORY, "Configure monitoring"),
            ("DOC", IssueType.TASK, "Write API documentation"),
        ]

        statuses = [IssueStatus.DONE, IssueStatus.IN_PROGRESS, IssueStatus.TODO, IssueStatus.IN_REVIEW]
        priorities = [IssuePriority.HIGH, IssuePriority.MEDIUM, IssuePriority.LOW]

        for i, (project, issue_type, summary) in enumerate(issue_summaries):
            key = f"{project}-{100 + i}"
            status = random.choice(statuses)
            created = datetime.now(UTC) - timedelta(days=random.randint(1, 60))

            self._issues[key] = JiraIssue(
                key=key,
                id=str(uuid4())[:8],
                summary=summary,
                description=f"Detailed description for {summary}. This includes requirements, acceptance criteria, and implementation notes.",
                issue_type=issue_type,
                status=status,
                priority=random.choice(priorities),
                assignee=random.choice(users) if status != IssueStatus.BACKLOG else None,
                reporter=random.choice(users),
                project_key=project,
                created_at=created,
                updated_at=created + timedelta(days=random.randint(0, 10)),
                resolved_at=created + timedelta(days=random.randint(5, 15)) if status == IssueStatus.DONE else None,
                labels=random.sample(["backend", "frontend", "api", "urgent", "tech-debt"], k=random.randint(0, 2)),
                story_points=random.choice([1, 2, 3, 5, 8, 13]) if issue_type in [IssueType.STORY, IssueType.BUG] else None,
                comments_count=random.randint(0, 10),
            )

    async def health_check(self) -> bool:
        """Check if Jira service is available."""
        return True

    async def list_projects(self) -> List[JiraProject]:
        """List all Jira projects."""
        return list(self._projects.values())

    async def get_project(self, key: str) -> Optional[JiraProject]:
        """Get a project by key."""
        return self._projects.get(key)

    async def search_issues(
        self,
        jql: Optional[str] = None,
        project: Optional[str] = None,
        status: Optional[IssueStatus] = None,
        issue_type: Optional[IssueType] = None,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[JiraIssue]:
        """Search issues with filters."""
        issues = list(self._issues.values())

        if project:
            issues = [i for i in issues if i.project_key == project]
        if status:
            issues = [i for i in issues if i.status == status]
        if issue_type:
            issues = [i for i in issues if i.issue_type == issue_type]
        if assignee:
            issues = [i for i in issues if i.assignee and assignee.lower() in i.assignee.display_name.lower()]
        if labels:
            issues = [i for i in issues if any(l in i.labels for l in labels)]

        # Sort by updated date
        issues.sort(key=lambda i: i.updated_at, reverse=True)
        return issues[:limit]

    async def get_issue(self, key: str) -> Optional[JiraIssue]:
        """Get an issue by key."""
        return self._issues.get(key)

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: IssueType,
        description: Optional[str] = None,
        priority: IssuePriority = IssuePriority.MEDIUM,
        assignee_id: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> JiraIssue:
        """Create a new issue."""
        from uuid import uuid4

        project = self._projects.get(project_key)
        if not project:
            raise ValueError(f"Project {project_key} not found")

        # Generate next issue number
        project_issues = [i for i in self._issues.values() if i.project_key == project_key]
        next_num = max([int(i.key.split("-")[1]) for i in project_issues], default=99) + 1

        key = f"{project_key}-{next_num}"
        now = datetime.now(UTC)

        assignee = self._users.get(assignee_id) if assignee_id else None
        reporter = list(self._users.values())[0]  # Default reporter

        issue = JiraIssue(
            key=key,
            id=str(uuid4())[:8],
            summary=summary,
            description=description,
            issue_type=issue_type,
            status=IssueStatus.TODO,
            priority=priority,
            assignee=assignee,
            reporter=reporter,
            project_key=project_key,
            created_at=now,
            updated_at=now,
            labels=labels or [],
        )

        self._issues[key] = issue
        return issue

    async def update_issue(
        self,
        key: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[IssueStatus] = None,
        priority: Optional[IssuePriority] = None,
        assignee_id: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Optional[JiraIssue]:
        """Update an existing issue."""
        issue = self._issues.get(key)
        if not issue:
            return None

        if summary:
            issue.summary = summary
        if description:
            issue.description = description
        if status:
            issue.status = status
            if status == IssueStatus.DONE:
                issue.resolved_at = datetime.now(UTC)
        if priority:
            issue.priority = priority
        if assignee_id is not None:
            issue.assignee = self._users.get(assignee_id)
        if labels is not None:
            issue.labels = labels

        issue.updated_at = datetime.now(UTC)
        return issue

    async def get_sprint(self, sprint_id: int) -> Optional[JiraSprint]:
        """Get a sprint by ID."""
        return self._sprints.get(sprint_id)

    async def list_sprints(
        self,
        board_id: int = 1,
        state: Optional[str] = None,
    ) -> List[JiraSprint]:
        """List sprints for a board."""
        sprints = [s for s in self._sprints.values() if s.board_id == board_id]
        if state:
            sprints = [s for s in sprints if s.state == state]
        return sprints

    async def get_sprint_issues(self, sprint_id: int) -> List[JiraIssue]:
        """Get issues in a sprint (mock: returns some issues)."""
        issues = list(self._issues.values())[:5]
        return issues

    async def get_project_stats(self, project_key: str) -> Dict:
        """Get statistics for a project."""
        issues = [i for i in self._issues.values() if i.project_key == project_key]

        if not issues:
            return {"error": "No issues found"}

        status_counts = {}
        type_counts = {}
        priority_counts = {}

        for issue in issues:
            status_counts[issue.status.value] = status_counts.get(issue.status.value, 0) + 1
            type_counts[issue.issue_type.value] = type_counts.get(issue.issue_type.value, 0) + 1
            priority_counts[issue.priority.value] = priority_counts.get(issue.priority.value, 0) + 1

        return {
            "total_issues": len(issues),
            "by_status": status_counts,
            "by_type": type_counts,
            "by_priority": priority_counts,
            "open_issues": sum(1 for i in issues if i.status not in [IssueStatus.DONE, IssueStatus.CLOSED]),
            "closed_issues": sum(1 for i in issues if i.status in [IssueStatus.DONE, IssueStatus.CLOSED]),
        }


# Global Jira service instance
jira_service = JiraService()


# =============================================================================
# Jira Tools
# =============================================================================

class JiraHealthCheckHandler(MCPToolHandler):
    """Check Jira service health."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="jira_health_check",
            description="Check if the Jira service is available and healthy",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        try:
            is_healthy = await jira_service.health_check()
            projects = await jira_service.list_projects()

            return {
                "success": True,
                "healthy": is_healthy,
                "status": "available" if is_healthy else "unavailable",
                "project_count": len(projects),
                "message": "Jira service is running and ready to use.",
                "next_steps": [
                    "Use 'jira_list_projects' to see available projects",
                    "Use 'jira_search_issues' to find issues",
                ],
            }
        except Exception as e:
            return connection_error(
                target="Jira Service",
                original_error=str(e),
            ).to_dict()


class JiraListProjectsHandler(MCPToolHandler):
    """List Jira projects."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="jira_list_projects",
            description="List all Jira projects accessible to the user",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        try:
            projects = await jira_service.list_projects()

            return {
                "success": True,
                "count": len(projects),
                "projects": [
                    {
                        "key": p.key,
                        "name": p.name,
                        "description": p.description,
                        "lead": p.lead.display_name,
                        "url": p.url,
                    }
                    for p in projects
                ],
            }
        except Exception as e:
            return internal_error(
                operation="list_projects",
                error_message=str(e),
            ).to_dict()


class JiraSearchIssuesHandler(MCPToolHandler):
    """Search Jira issues."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="jira_search_issues",
            description="Search for Jira issues using various filters",
            input_schema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project key to filter by",
                    },
                    "status": {
                        "type": "string",
                        "description": "Status to filter by",
                        "enum": [s.value for s in IssueStatus],
                    },
                    "issue_type": {
                        "type": "string",
                        "description": "Issue type to filter by",
                        "enum": [t.value for t in IssueType],
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Assignee name to filter by",
                    },
                    "labels": {
                        "type": "array",
                        "description": "Labels to filter by",
                        "items": {"type": "string"},
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of issues (default: 20)",
                        "default": 20,
                    },
                },
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        project = arguments.get("project")
        status_str = arguments.get("status")
        type_str = arguments.get("issue_type")
        assignee = arguments.get("assignee")
        labels = arguments.get("labels")
        limit = arguments.get("limit", 20)

        status = IssueStatus(status_str) if status_str else None
        issue_type = IssueType(type_str) if type_str else None

        try:
            issues = await jira_service.search_issues(
                project=project,
                status=status,
                issue_type=issue_type,
                assignee=assignee,
                labels=labels,
                limit=limit,
            )

            return {
                "success": True,
                "count": len(issues),
                "filters": {
                    "project": project,
                    "status": status_str,
                    "issue_type": type_str,
                    "assignee": assignee,
                    "labels": labels,
                },
                "issues": [
                    {
                        "key": i.key,
                        "summary": i.summary,
                        "type": i.issue_type.value,
                        "status": i.status.value,
                        "priority": i.priority.value,
                        "assignee": i.assignee.display_name if i.assignee else None,
                        "labels": i.labels,
                        "story_points": i.story_points,
                        "updated": i.updated_at.isoformat(),
                    }
                    for i in issues
                ],
            }
        except Exception as e:
            return internal_error(
                operation="search_issues",
                error_message=str(e),
            ).to_dict()


class JiraGetIssueHandler(MCPToolHandler):
    """Get Jira issue details."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="jira_get_issue",
            description="Get detailed information about a specific Jira issue",
            input_schema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Issue key (e.g., PROJ-123)",
                    },
                },
                "required": ["key"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        key = arguments["key"].upper()

        try:
            issue = await jira_service.get_issue(key)

            if not issue:
                return not_found_error(
                    resource_type="issue",
                    resource_name=key,
                ).to_dict()

            return {
                "success": True,
                "issue": {
                    "key": issue.key,
                    "summary": issue.summary,
                    "description": issue.description,
                    "type": issue.issue_type.value,
                    "status": issue.status.value,
                    "priority": issue.priority.value,
                    "assignee": issue.assignee.display_name if issue.assignee else None,
                    "reporter": issue.reporter.display_name,
                    "project": issue.project_key,
                    "labels": issue.labels,
                    "components": issue.components,
                    "story_points": issue.story_points,
                    "created": issue.created_at.isoformat(),
                    "updated": issue.updated_at.isoformat(),
                    "resolved": issue.resolved_at.isoformat() if issue.resolved_at else None,
                    "due_date": issue.due_date.isoformat() if issue.due_date else None,
                    "comments_count": issue.comments_count,
                    "subtasks": issue.subtasks,
                    "linked_issues": issue.linked_issues,
                },
            }
        except Exception as e:
            return internal_error(
                operation="get_issue",
                error_message=str(e),
            ).to_dict()


class JiraCreateIssueHandler(MCPToolHandler):
    """Create a Jira issue."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="jira_create_issue",
            description="Create a new Jira issue",
            input_schema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project key (e.g., NEXUS)",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Issue summary/title",
                    },
                    "issue_type": {
                        "type": "string",
                        "description": "Issue type",
                        "enum": [t.value for t in IssueType],
                        "default": "Task",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description",
                    },
                    "priority": {
                        "type": "string",
                        "description": "Issue priority",
                        "enum": [p.value for p in IssuePriority],
                        "default": "Medium",
                    },
                    "labels": {
                        "type": "array",
                        "description": "Labels to add",
                        "items": {"type": "string"},
                    },
                },
                "required": ["project", "summary"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        project = arguments["project"].upper()
        summary = arguments["summary"]
        type_str = arguments.get("issue_type", "Task")
        description = arguments.get("description")
        priority_str = arguments.get("priority", "Medium")
        labels = arguments.get("labels")

        try:
            issue = await jira_service.create_issue(
                project_key=project,
                summary=summary,
                issue_type=IssueType(type_str),
                description=description,
                priority=IssuePriority(priority_str),
                labels=labels,
            )

            return {
                "success": True,
                "message": f"Issue {issue.key} created successfully",
                "issue": {
                    "key": issue.key,
                    "summary": issue.summary,
                    "type": issue.issue_type.value,
                    "status": issue.status.value,
                    "url": f"https://jira.example.com/browse/{issue.key}",
                },
            }
        except ValueError as e:
            return not_found_error(
                resource_type="project",
                resource_name=project,
            ).to_dict()
        except Exception as e:
            return internal_error(
                operation="create_issue",
                error_message=str(e),
            ).to_dict()


class JiraUpdateIssueHandler(MCPToolHandler):
    """Update a Jira issue."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="jira_update_issue",
            description="Update an existing Jira issue",
            input_schema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Issue key (e.g., PROJ-123)",
                    },
                    "summary": {
                        "type": "string",
                        "description": "New summary/title",
                    },
                    "description": {
                        "type": "string",
                        "description": "New description",
                    },
                    "status": {
                        "type": "string",
                        "description": "New status",
                        "enum": [s.value for s in IssueStatus],
                    },
                    "priority": {
                        "type": "string",
                        "description": "New priority",
                        "enum": [p.value for p in IssuePriority],
                    },
                    "labels": {
                        "type": "array",
                        "description": "New labels (replaces existing)",
                        "items": {"type": "string"},
                    },
                },
                "required": ["key"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        key = arguments["key"].upper()
        summary = arguments.get("summary")
        description = arguments.get("description")
        status_str = arguments.get("status")
        priority_str = arguments.get("priority")
        labels = arguments.get("labels")

        status = IssueStatus(status_str) if status_str else None
        priority = IssuePriority(priority_str) if priority_str else None

        try:
            issue = await jira_service.update_issue(
                key=key,
                summary=summary,
                description=description,
                status=status,
                priority=priority,
                labels=labels,
            )

            if not issue:
                return not_found_error(
                    resource_type="issue",
                    resource_name=key,
                ).to_dict()

            return {
                "success": True,
                "message": f"Issue {key} updated successfully",
                "issue": {
                    "key": issue.key,
                    "summary": issue.summary,
                    "status": issue.status.value,
                    "priority": issue.priority.value,
                    "updated": issue.updated_at.isoformat(),
                },
            }
        except Exception as e:
            return internal_error(
                operation="update_issue",
                error_message=str(e),
            ).to_dict()


class JiraTransitionIssueHandler(MCPToolHandler):
    """Transition a Jira issue to a new status."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="jira_transition_issue",
            description="Move a Jira issue to a new status (e.g., To Do → In Progress → Done)",
            input_schema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Issue key (e.g., PROJ-123)",
                    },
                    "status": {
                        "type": "string",
                        "description": "Target status",
                        "enum": [s.value for s in IssueStatus],
                    },
                },
                "required": ["key", "status"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        key = arguments["key"].upper()
        status_str = arguments["status"]

        try:
            issue = await jira_service.update_issue(
                key=key,
                status=IssueStatus(status_str),
            )

            if not issue:
                return not_found_error(
                    resource_type="issue",
                    resource_name=key,
                ).to_dict()

            return {
                "success": True,
                "message": f"Issue {key} transitioned to '{status_str}'",
                "issue": {
                    "key": issue.key,
                    "status": issue.status.value,
                    "resolved": issue.resolved_at.isoformat() if issue.resolved_at else None,
                },
            }
        except Exception as e:
            return internal_error(
                operation="transition_issue",
                error_message=str(e),
            ).to_dict()


class JiraListSprintsHandler(MCPToolHandler):
    """List Jira sprints."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="jira_list_sprints",
            description="List sprints for a Jira board",
            input_schema={
                "type": "object",
                "properties": {
                    "board_id": {
                        "type": "integer",
                        "description": "Board ID (default: 1)",
                        "default": 1,
                    },
                    "state": {
                        "type": "string",
                        "description": "Filter by sprint state",
                        "enum": ["active", "future", "closed"],
                    },
                },
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        board_id = arguments.get("board_id", 1)
        state = arguments.get("state")

        try:
            sprints = await jira_service.list_sprints(board_id, state)

            return {
                "success": True,
                "count": len(sprints),
                "board_id": board_id,
                "sprints": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "state": s.state,
                        "goal": s.goal,
                        "start_date": s.start_date.isoformat() if s.start_date else None,
                        "end_date": s.end_date.isoformat() if s.end_date else None,
                    }
                    for s in sprints
                ],
            }
        except Exception as e:
            return internal_error(
                operation="list_sprints",
                error_message=str(e),
            ).to_dict()


class JiraGetSprintIssuesHandler(MCPToolHandler):
    """Get issues in a sprint."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="jira_get_sprint_issues",
            description="Get all issues in a specific sprint",
            input_schema={
                "type": "object",
                "properties": {
                    "sprint_id": {
                        "type": "integer",
                        "description": "Sprint ID",
                    },
                },
                "required": ["sprint_id"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        sprint_id = arguments["sprint_id"]

        try:
            sprint = await jira_service.get_sprint(sprint_id)
            if not sprint:
                return not_found_error(
                    resource_type="sprint",
                    resource_name=str(sprint_id),
                ).to_dict()

            issues = await jira_service.get_sprint_issues(sprint_id)

            return {
                "success": True,
                "sprint": {
                    "id": sprint.id,
                    "name": sprint.name,
                    "state": sprint.state,
                },
                "issue_count": len(issues),
                "issues": [
                    {
                        "key": i.key,
                        "summary": i.summary,
                        "type": i.issue_type.value,
                        "status": i.status.value,
                        "assignee": i.assignee.display_name if i.assignee else None,
                        "story_points": i.story_points,
                    }
                    for i in issues
                ],
            }
        except Exception as e:
            return internal_error(
                operation="get_sprint_issues",
                error_message=str(e),
            ).to_dict()


class JiraGetProjectStatsHandler(MCPToolHandler):
    """Get project statistics."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="jira_get_project_stats",
            description="Get statistics and metrics for a Jira project",
            input_schema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project key",
                    },
                },
                "required": ["project"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        project = arguments["project"].upper()

        try:
            project_info = await jira_service.get_project(project)
            if not project_info:
                return not_found_error(
                    resource_type="project",
                    resource_name=project,
                ).to_dict()

            stats = await jira_service.get_project_stats(project)

            return {
                "success": True,
                "project": {
                    "key": project_info.key,
                    "name": project_info.name,
                },
                "stats": stats,
            }
        except Exception as e:
            return internal_error(
                operation="get_project_stats",
                error_message=str(e),
            ).to_dict()


# =============================================================================
# Helper function to get all Jira tool handlers
# =============================================================================

def get_all_jira_tool_handlers() -> list[MCPToolHandler]:
    """Return all Jira MCP tool handlers."""
    return [
        # Health
        JiraHealthCheckHandler(),

        # Projects
        JiraListProjectsHandler(),
        JiraGetProjectStatsHandler(),

        # Issues
        JiraSearchIssuesHandler(),
        JiraGetIssueHandler(),
        JiraCreateIssueHandler(),
        JiraUpdateIssueHandler(),
        JiraTransitionIssueHandler(),

        # Sprints
        JiraListSprintsHandler(),
        JiraGetSprintIssuesHandler(),
    ]
