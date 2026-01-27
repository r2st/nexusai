"""Canonical entity models for software intelligence platform.

Defines the domain model that all source-specific data is normalized into.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Types of domain entities."""

    REPOSITORY = "repository"
    COMMIT = "commit"
    PULL_REQUEST = "pull_request"
    BUILD = "build"
    DEPLOYMENT = "deployment"
    INCIDENT = "incident"
    SERVICE = "service"
    TEAM = "team"
    DEVELOPER = "developer"
    ENVIRONMENT = "environment"
    ISSUE = "issue"
    RELEASE = "release"


class RelationType(str, Enum):
    """Types of entity relationships."""

    # Repository relations
    CONTAINS = "contains"  # repo contains commits/PRs
    BELONGS_TO = "belongs_to"  # entity belongs to repo/team

    # Developer relations
    AUTHORED = "authored"  # developer authored commit/PR
    REVIEWED = "reviewed"  # developer reviewed PR
    ASSIGNED_TO = "assigned_to"  # issue/incident assigned to developer
    MEMBER_OF = "member_of"  # developer member of team

    # Build/Deploy relations
    TRIGGERED_BY = "triggered_by"  # build triggered by commit/PR
    DEPLOYS = "deploys"  # deployment deploys commit/build
    DEPLOYED_TO = "deployed_to"  # deployment to environment

    # Incident relations
    CAUSED_BY = "caused_by"  # incident caused by deployment
    AFFECTS = "affects"  # incident affects service

    # Service relations
    DEPENDS_ON = "depends_on"  # service depends on service
    OWNED_BY = "owned_by"  # service owned by team

    # Generic
    RELATED_TO = "related_to"


class Entity(BaseModel):
    """Base class for all domain entities."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(..., description="Organization/tenant ID")
    entity_type: EntityType

    # Source tracking
    source: str = Field(..., description="Source system (github, gitlab, etc)")
    source_id: str = Field(..., description="ID in source system")
    connection_id: str | None = Field(None, description="Connection ID")

    # Domain ID for cross-source identity
    domain_id: str | None = Field(
        None,
        description="5-segment domain ID: tenant:source:connection:type:source_id",
    )

    # Timestamps
    source_created_at: datetime | None = Field(None, description="Created in source")
    source_updated_at: datetime | None = Field(None, description="Updated in source")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Raw data reference
    raw_event_ids: list[str] = Field(
        default_factory=list,
        description="IDs of raw events that created/updated this entity",
    )

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    def generate_domain_id(self) -> str:
        """Generate 5-segment domain ID."""
        return f"{self.tenant_id}:{self.source}:{self.connection_id or 'default'}:{self.entity_type.value}:{self.source_id}"


class EntityRelation(BaseModel):
    """Relationship between two entities."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str

    # Entities
    from_entity_id: str
    from_entity_type: EntityType
    to_entity_id: str
    to_entity_type: EntityType

    # Relation
    relation_type: RelationType
    properties: dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid_from: datetime | None = None
    valid_to: datetime | None = None


# Domain Entity Models

class Repository(Entity):
    """Git repository entity."""

    entity_type: EntityType = EntityType.REPOSITORY

    name: str
    full_name: str  # org/repo format
    description: str | None = None
    url: str | None = None
    clone_url: str | None = None

    # Settings
    default_branch: str = "main"
    is_private: bool = False
    is_archived: bool = False
    is_fork: bool = False

    # Stats
    star_count: int = 0
    fork_count: int = 0
    open_issues_count: int = 0
    size_kb: int = 0

    # Languages
    primary_language: str | None = None
    languages: dict[str, int] = Field(default_factory=dict)  # language -> bytes

    # Owner
    owner_id: str | None = None
    owner_type: str | None = None  # user, org, team


class Commit(Entity):
    """Git commit entity."""

    entity_type: EntityType = EntityType.COMMIT

    sha: str
    message: str
    short_message: str | None = None

    # Author
    author_id: str | None = None
    author_name: str | None = None
    author_email: str | None = None
    authored_at: datetime | None = None

    # Committer
    committer_id: str | None = None
    committer_name: str | None = None
    committer_email: str | None = None
    committed_at: datetime | None = None

    # Repository
    repository_id: str | None = None
    branch: str | None = None

    # Stats
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0
    files: list[str] = Field(default_factory=list)

    # Parents
    parent_shas: list[str] = Field(default_factory=list)
    is_merge: bool = False


class PullRequest(Entity):
    """Pull request / merge request entity."""

    entity_type: EntityType = EntityType.PULL_REQUEST

    number: int
    title: str
    body: str | None = None
    url: str | None = None

    # State
    state: str = "open"  # open, closed, merged
    is_draft: bool = False
    merged: bool = False
    merged_at: datetime | None = None
    closed_at: datetime | None = None

    # Branches
    source_branch: str | None = None
    target_branch: str | None = None
    head_sha: str | None = None
    base_sha: str | None = None

    # Repository
    repository_id: str | None = None

    # People
    author_id: str | None = None
    merged_by_id: str | None = None
    assignee_ids: list[str] = Field(default_factory=list)
    reviewer_ids: list[str] = Field(default_factory=list)

    # Stats
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0
    commits_count: int = 0
    comments_count: int = 0
    review_comments_count: int = 0

    # Labels
    labels: list[str] = Field(default_factory=list)

    # Cycle time metrics
    first_commit_at: datetime | None = None
    first_review_at: datetime | None = None
    approved_at: datetime | None = None
    time_to_first_review_hours: float | None = None
    time_to_merge_hours: float | None = None


class Build(Entity):
    """CI build / pipeline entity."""

    entity_type: EntityType = EntityType.BUILD

    number: int | str
    name: str | None = None
    url: str | None = None

    # State
    status: str = "pending"  # pending, running, success, failed, cancelled
    conclusion: str | None = None  # success, failure, cancelled, skipped
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: int | None = None

    # Trigger
    trigger: str | None = None  # push, pr, schedule, manual
    triggered_by_id: str | None = None
    commit_sha: str | None = None
    branch: str | None = None
    pull_request_id: str | None = None

    # Repository
    repository_id: str | None = None

    # Jobs
    jobs_count: int = 0
    jobs_succeeded: int = 0
    jobs_failed: int = 0

    # Artifacts
    has_artifacts: bool = False
    artifact_size_bytes: int = 0


class Deployment(Entity):
    """Deployment entity."""

    entity_type: EntityType = EntityType.DEPLOYMENT

    name: str | None = None
    url: str | None = None

    # State
    status: str = "pending"  # pending, in_progress, success, failed, rollback
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: int | None = None

    # What was deployed
    commit_sha: str | None = None
    build_id: str | None = None
    release_id: str | None = None
    version: str | None = None

    # Where
    environment_id: str | None = None
    environment_name: str | None = None
    service_id: str | None = None

    # Who
    deployed_by_id: str | None = None

    # Repository
    repository_id: str | None = None

    # Rollback info
    is_rollback: bool = False
    previous_deployment_id: str | None = None


class Incident(Entity):
    """Incident entity."""

    entity_type: EntityType = EntityType.INCIDENT

    number: int | str | None = None
    title: str
    description: str | None = None
    url: str | None = None

    # State
    status: str = "triggered"  # triggered, acknowledged, resolved
    severity: str | None = None  # critical, high, medium, low
    priority: str | None = None  # P1, P2, P3, P4, P5

    # Timeline
    triggered_at: datetime | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    time_to_acknowledge_minutes: float | None = None
    time_to_resolve_minutes: float | None = None

    # Impact
    affected_service_ids: list[str] = Field(default_factory=list)
    affected_environment_ids: list[str] = Field(default_factory=list)

    # Cause
    caused_by_deployment_id: str | None = None
    caused_by_change_id: str | None = None
    root_cause: str | None = None

    # People
    assigned_to_ids: list[str] = Field(default_factory=list)
    acknowledged_by_id: str | None = None
    resolved_by_id: str | None = None

    # External
    external_url: str | None = None
    external_id: str | None = None


class Service(Entity):
    """Service / microservice entity."""

    entity_type: EntityType = EntityType.SERVICE

    name: str
    description: str | None = None
    url: str | None = None

    # Classification
    type: str | None = None  # api, worker, frontend, database, etc
    tier: str | None = None  # critical, standard, low

    # Ownership
    team_id: str | None = None
    owner_ids: list[str] = Field(default_factory=list)

    # Repository
    repository_ids: list[str] = Field(default_factory=list)

    # Dependencies
    depends_on_ids: list[str] = Field(default_factory=list)
    depended_by_ids: list[str] = Field(default_factory=list)

    # Status
    status: str = "active"  # active, deprecated, archived


class Team(Entity):
    """Team entity."""

    entity_type: EntityType = EntityType.TEAM

    name: str
    description: str | None = None
    slug: str | None = None

    # Members
    member_ids: list[str] = Field(default_factory=list)
    lead_id: str | None = None

    # Organization
    parent_team_id: str | None = None

    # Ownership
    owned_service_ids: list[str] = Field(default_factory=list)
    owned_repository_ids: list[str] = Field(default_factory=list)


class Developer(Entity):
    """Developer / user entity."""

    entity_type: EntityType = EntityType.DEVELOPER

    username: str
    display_name: str | None = None
    email: str | None = None
    avatar_url: str | None = None

    # Identity
    emails: list[str] = Field(default_factory=list)
    usernames: list[str] = Field(default_factory=list)  # Across sources

    # Teams
    team_ids: list[str] = Field(default_factory=list)

    # Status
    is_active: bool = True
    is_bot: bool = False


class Environment(Entity):
    """Deployment environment entity."""

    entity_type: EntityType = EntityType.ENVIRONMENT

    name: str
    description: str | None = None
    url: str | None = None

    # Classification
    type: str = "development"  # development, staging, production
    tier: str | None = None

    # Protection
    is_protected: bool = False
    requires_approval: bool = False
    approver_ids: list[str] = Field(default_factory=list)


# Supporting Models

class IdentityMapping(BaseModel):
    """Mapping between identities across sources."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str

    # Canonical identity
    canonical_id: str
    entity_type: EntityType

    # Source identity
    source: str
    source_id: str
    source_username: str | None = None
    source_email: str | None = None

    # Confidence
    confidence: float = 1.0  # 0.0 to 1.0
    verified: bool = False
    verified_by: str | None = None
    verified_at: datetime | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EntityQuery(BaseModel):
    """Query parameters for entity retrieval."""

    tenant_id: str
    entity_type: EntityType | None = None
    source: str | None = None
    source_id: str | None = None
    domain_id: str | None = None

    # Filters
    ids: list[str] | None = None
    tags: list[str] | None = None

    # Time range
    created_after: datetime | None = None
    created_before: datetime | None = None
    updated_after: datetime | None = None

    # Relations
    related_to: str | None = None  # Find entities related to this ID
    relation_type: RelationType | None = None

    # Pagination
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    cursor: str | None = None

    # Sorting
    sort_by: str = "updated_at"
    sort_order: str = "desc"
