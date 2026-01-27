"""
Issue Tracker Integrations

Native integrations with popular issue tracking systems.
"""

from .service import (
    IssueTrackerService,
    get_issue_tracker_service,
)
from .models import (
    IssueTrackerType,
    Issue,
    IssueCreate,
    IssueUpdate,
    IssueStatus,
    IssuePriority,
    IssueComment,
    IssueLink,
    Sprint,
    Board,
    IssueTrackerConfig,
)
from .providers import (
    BaseIssueTracker,
    JiraProvider,
    AzureBoardsProvider,
    LinearProvider,
    GitHubIssuesProvider,
)

__all__ = [
    # Service
    "IssueTrackerService",
    "get_issue_tracker_service",
    # Models
    "IssueTrackerType",
    "Issue",
    "IssueCreate",
    "IssueUpdate",
    "IssueStatus",
    "IssuePriority",
    "IssueComment",
    "IssueLink",
    "Sprint",
    "Board",
    "IssueTrackerConfig",
    # Providers
    "BaseIssueTracker",
    "JiraProvider",
    "AzureBoardsProvider",
    "LinearProvider",
    "GitHubIssuesProvider",
]
