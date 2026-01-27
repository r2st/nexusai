"""Data models for Real-time Collaboration services."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PresenceStatus(str, Enum):
    """User presence status."""

    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"


class UserPresence(BaseModel):
    """User presence information."""

    user_id: str
    username: str
    avatar_url: str | None = None

    # Status
    status: PresenceStatus = PresenceStatus.OFFLINE
    status_message: str | None = None

    # Location
    current_project_id: str | None = None
    current_file_path: str | None = None
    current_line: int | None = None

    # Timestamps
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    session_started: datetime | None = None

    # Metadata
    client_type: str = "web"  # web, ide, mobile
    client_version: str | None = None


class SessionType(str, Enum):
    """Types of collaborative sessions."""

    CHAT = "chat"
    CODE_REVIEW = "code_review"
    PAIR_PROGRAMMING = "pair_programming"
    SCREEN_SHARE = "screen_share"
    WHITEBOARD = "whiteboard"


class SessionParticipant(BaseModel):
    """A participant in a collaborative session."""

    user_id: str
    username: str
    role: str = "participant"  # host, participant, viewer
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    left_at: datetime | None = None
    is_active: bool = True

    # Permissions
    can_edit: bool = True
    can_invite: bool = False
    can_moderate: bool = False


class SharedSession(BaseModel):
    """A collaborative session."""

    id: str
    organization_id: str
    session_type: SessionType

    # Details
    title: str
    description: str | None = None

    # Context
    project_id: str | None = None
    file_path: str | None = None
    pr_id: str | None = None

    # Participants
    host_user_id: str
    participants: list[SessionParticipant] = Field(default_factory=list)
    max_participants: int = 10

    # Status
    is_active: bool = True
    is_public: bool = False  # Visible to all org members

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    ended_at: datetime | None = None

    # Session data
    messages: list[dict[str, Any]] = Field(default_factory=list)
    shared_state: dict[str, Any] = Field(default_factory=dict)


class AnnotationType(str, Enum):
    """Types of code annotations."""

    COMMENT = "comment"
    QUESTION = "question"
    SUGGESTION = "suggestion"
    ISSUE = "issue"
    BOOKMARK = "bookmark"
    HIGHLIGHT = "highlight"


class CodeAnnotation(BaseModel):
    """An annotation on code."""

    id: str
    organization_id: str
    project_id: str
    file_path: str

    # Position
    start_line: int
    end_line: int
    start_column: int | None = None
    end_column: int | None = None

    # Content
    annotation_type: AnnotationType
    title: str | None = None
    content: str
    code_snippet: str | None = None

    # Author
    author_id: str
    author_username: str

    # Mentions
    mentions: list[str] = Field(default_factory=list)  # User IDs

    # Status
    resolved: bool = False
    resolved_by: str | None = None
    resolved_at: datetime | None = None

    # Threading
    parent_id: str | None = None  # For replies
    reply_count: int = 0

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata
    commit_sha: str | None = None
    branch: str | None = None


class ActivityType(str, Enum):
    """Types of team activities."""

    # Code activities
    COMMIT = "commit"
    PUSH = "push"
    PR_OPENED = "pr_opened"
    PR_MERGED = "pr_merged"
    PR_REVIEWED = "pr_reviewed"
    PR_COMMENTED = "pr_commented"

    # Collaboration activities
    SESSION_STARTED = "session_started"
    SESSION_JOINED = "session_joined"
    ANNOTATION_CREATED = "annotation_created"
    ANNOTATION_RESOLVED = "annotation_resolved"
    MENTION = "mention"

    # Analysis activities
    ANALYSIS_COMPLETED = "analysis_completed"
    ISSUE_FOUND = "issue_found"
    ISSUE_FIXED = "issue_fixed"

    # System activities
    DEPLOYMENT = "deployment"
    ALERT = "alert"
    MILESTONE = "milestone"


class ActivityEvent(BaseModel):
    """A team activity event."""

    id: str
    organization_id: str
    project_id: str | None = None

    # Event details
    activity_type: ActivityType
    title: str
    description: str | None = None

    # Actor
    actor_id: str
    actor_username: str
    actor_avatar_url: str | None = None

    # Target
    target_type: str | None = None  # file, pr, issue, session
    target_id: str | None = None
    target_url: str | None = None

    # Context
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Visibility
    is_public: bool = True
    visible_to_user_ids: list[str] | None = None  # If not public

    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CollaborationRoom(BaseModel):
    """A real-time collaboration room (for WebSocket management)."""

    id: str
    room_type: str  # project, file, session, org
    room_key: str  # Unique identifier (e.g., project_id, session_id)

    # Members
    connected_users: list[str] = Field(default_factory=list)

    # State
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
