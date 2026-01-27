"""
Issue Tracker Models

Data models for issue tracker integrations.
"""

from enum import Enum
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class IssueTrackerType(str, Enum):
    """Supported issue tracker types."""
    JIRA = "jira"
    AZURE_BOARDS = "azure_boards"
    LINEAR = "linear"
    GITHUB = "github"
    GITLAB = "gitlab"
    ASANA = "asana"
    TRELLO = "trello"


class IssueStatus(str, Enum):
    """Standard issue statuses."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CLOSED = "closed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class IssuePriority(str, Enum):
    """Standard issue priorities."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRIVIAL = "trivial"


class IssueType(str, Enum):
    """Standard issue types."""
    BUG = "bug"
    FEATURE = "feature"
    TASK = "task"
    STORY = "story"
    EPIC = "epic"
    TECH_DEBT = "tech_debt"
    SECURITY = "security"
    IMPROVEMENT = "improvement"


class IssueComment(BaseModel):
    """A comment on an issue."""
    id: str
    author: str
    body: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class IssueLink(BaseModel):
    """A link between issues."""
    id: str
    source_id: str
    target_id: str
    link_type: str  # blocks, is_blocked_by, relates_to, duplicates, etc.


class Attachment(BaseModel):
    """An attachment on an issue."""
    id: str
    filename: str
    url: str
    size_bytes: int
    content_type: str
    created_at: datetime


class Issue(BaseModel):
    """Unified issue model."""
    # Identification
    id: str
    key: str  # e.g., "PROJ-123"
    url: str
    
    # Core fields
    title: str
    description: Optional[str] = None
    issue_type: IssueType = IssueType.TASK
    status: IssueStatus = IssueStatus.OPEN
    priority: IssuePriority = IssuePriority.MEDIUM
    
    # Assignment
    assignee: Optional[str] = None
    reporter: str = ""
    
    # Project context
    project_id: str = ""
    project_key: str = ""
    
    # Time tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Estimation
    story_points: Optional[float] = None
    estimate_hours: Optional[float] = None
    time_spent_hours: Optional[float] = None
    
    # Categorization
    labels: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    epic_key: Optional[str] = None
    sprint_id: Optional[str] = None
    
    # Relations
    parent_id: Optional[str] = None
    subtask_ids: list[str] = Field(default_factory=list)
    linked_issues: list[IssueLink] = Field(default_factory=list)
    
    # Comments and attachments
    comments: list[IssueComment] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)
    
    # Custom fields
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    
    # Source tracker info
    source_tracker: IssueTrackerType = IssueTrackerType.JIRA
    raw_data: dict[str, Any] = Field(default_factory=dict)


class IssueCreate(BaseModel):
    """Model for creating a new issue."""
    title: str
    description: Optional[str] = None
    issue_type: IssueType = IssueType.TASK
    priority: IssuePriority = IssuePriority.MEDIUM
    
    project_key: str
    assignee: Optional[str] = None
    
    labels: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    epic_key: Optional[str] = None
    sprint_id: Optional[str] = None
    parent_key: Optional[str] = None
    
    due_date: Optional[datetime] = None
    story_points: Optional[float] = None
    estimate_hours: Optional[float] = None
    
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class IssueUpdate(BaseModel):
    """Model for updating an issue."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[IssueStatus] = None
    priority: Optional[IssuePriority] = None
    
    assignee: Optional[str] = None
    labels: Optional[list[str]] = None
    components: Optional[list[str]] = None
    epic_key: Optional[str] = None
    sprint_id: Optional[str] = None
    
    due_date: Optional[datetime] = None
    story_points: Optional[float] = None
    time_spent_hours: Optional[float] = None
    
    custom_fields: Optional[dict[str, Any]] = None


class Sprint(BaseModel):
    """Sprint/Iteration model."""
    id: str
    name: str
    state: str  # active, closed, future
    
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    goal: Optional[str] = None
    board_id: Optional[str] = None
    
    # Metrics
    total_issues: int = 0
    completed_issues: int = 0
    story_points_total: float = 0
    story_points_completed: float = 0


class Board(BaseModel):
    """Kanban/Scrum board model."""
    id: str
    name: str
    board_type: str  # kanban, scrum
    
    project_key: str
    columns: list[str] = Field(default_factory=list)
    
    sprints: list[Sprint] = Field(default_factory=list)


class IssueTrackerConfig(BaseModel):
    """Configuration for an issue tracker connection."""
    tracker_type: IssueTrackerType
    
    # Connection
    base_url: str
    api_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    oauth_token: Optional[str] = None
    
    # Project mapping
    default_project_key: Optional[str] = None
    project_mappings: dict[str, str] = Field(default_factory=dict)
    
    # Status mapping (internal -> tracker)
    status_mappings: dict[str, str] = Field(default_factory=dict)
    
    # Priority mapping
    priority_mappings: dict[str, str] = Field(default_factory=dict)
    
    # Issue type mapping
    type_mappings: dict[str, str] = Field(default_factory=dict)
    
    # Sync settings
    sync_comments: bool = True
    sync_attachments: bool = False
    bidirectional_sync: bool = False
    
    # Webhook URL for real-time updates
    webhook_secret: Optional[str] = None


class IssueSearchQuery(BaseModel):
    """Query for searching issues."""
    project_key: Optional[str] = None
    status: Optional[list[IssueStatus]] = None
    priority: Optional[list[IssuePriority]] = None
    issue_type: Optional[list[IssueType]] = None
    assignee: Optional[str] = None
    labels: Optional[list[str]] = None
    
    text_query: Optional[str] = None
    jql: Optional[str] = None  # For Jira
    wiql: Optional[str] = None  # For Azure Boards
    
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    updated_after: Optional[datetime] = None
    
    sprint_id: Optional[str] = None
    epic_key: Optional[str] = None
    
    max_results: int = 50
    offset: int = 0


class IssueSearchResult(BaseModel):
    """Result of issue search."""
    issues: list[Issue]
    total: int
    offset: int
    max_results: int
    has_more: bool
