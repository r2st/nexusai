"""Event models for the ingestion service.

Defines the raw event schema, envelope, and source types.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventSource(str, Enum):
    """Supported event sources."""

    # Version Control
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    AZURE_DEVOPS = "azure_devops"

    # CI/CD
    JENKINS = "jenkins"
    CIRCLECI = "circleci"
    GITHUB_ACTIONS = "github_actions"
    GITLAB_CI = "gitlab_ci"
    AZURE_PIPELINES = "azure_pipelines"
    ARGOCD = "argocd"

    # Issue Tracking
    JIRA = "jira"
    LINEAR = "linear"
    ASANA = "asana"
    SHORTCUT = "shortcut"

    # Communication
    SLACK = "slack"
    TEAMS = "teams"
    DISCORD = "discord"

    # Incident Management
    PAGERDUTY = "pagerduty"
    OPSGENIE = "opsgenie"
    INCIDENT_IO = "incident_io"
    STATUSPAGE = "statuspage"

    # Observability
    DATADOG = "datadog"
    NEW_RELIC = "newrelic"
    GRAFANA = "grafana"
    PROMETHEUS = "prometheus"
    SENTRY = "sentry"

    # Infrastructure
    KUBERNETES = "kubernetes"
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    TERRAFORM = "terraform"

    # Code Quality
    SONARQUBE = "sonarqube"
    CODECOV = "codecov"
    SNYK = "snyk"

    # Custom
    DEVLAKE = "devlake"
    CUSTOM = "custom"


class EventType(str, Enum):
    """High-level event types for routing."""

    # Repository events
    PUSH = "push"
    BRANCH_CREATE = "branch_create"
    BRANCH_DELETE = "branch_delete"
    TAG_CREATE = "tag_create"
    TAG_DELETE = "tag_delete"

    # Pull Request / Merge Request
    PR_OPENED = "pr_opened"
    PR_CLOSED = "pr_closed"
    PR_MERGED = "pr_merged"
    PR_UPDATED = "pr_updated"
    PR_REVIEW = "pr_review"
    PR_COMMENT = "pr_comment"

    # Issues
    ISSUE_CREATED = "issue_created"
    ISSUE_UPDATED = "issue_updated"
    ISSUE_CLOSED = "issue_closed"
    ISSUE_COMMENT = "issue_comment"

    # CI/CD
    BUILD_STARTED = "build_started"
    BUILD_COMPLETED = "build_completed"
    BUILD_FAILED = "build_failed"
    DEPLOY_STARTED = "deploy_started"
    DEPLOY_COMPLETED = "deploy_completed"
    DEPLOY_FAILED = "deploy_failed"
    DEPLOY_ROLLBACK = "deploy_rollback"

    # Incidents
    INCIDENT_CREATED = "incident_created"
    INCIDENT_UPDATED = "incident_updated"
    INCIDENT_RESOLVED = "incident_resolved"
    INCIDENT_ACKNOWLEDGED = "incident_acknowledged"
    ALERT_TRIGGERED = "alert_triggered"
    ALERT_RESOLVED = "alert_resolved"

    # Communication
    MESSAGE_SENT = "message_sent"
    CHANNEL_CREATED = "channel_created"
    MENTION = "mention"

    # Infrastructure
    RESOURCE_CREATED = "resource_created"
    RESOURCE_UPDATED = "resource_updated"
    RESOURCE_DELETED = "resource_deleted"
    SCALING_EVENT = "scaling_event"

    # Code Quality
    SCAN_COMPLETED = "scan_completed"
    VULNERABILITY_FOUND = "vulnerability_found"
    COVERAGE_REPORT = "coverage_report"

    # Generic
    WEBHOOK = "webhook"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class RawEvent(BaseModel):
    """Raw event as received from a source.

    This is the immutable record of what was received.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(..., description="Organization/tenant ID")
    source: EventSource = Field(..., description="Event source system")
    source_event_type: str = Field(..., description="Original event type from source")
    event_type: EventType = Field(
        default=EventType.UNKNOWN, description="Normalized event type"
    )

    # Raw payload
    payload: dict[str, Any] = Field(..., description="Original event payload")
    headers: dict[str, str] = Field(
        default_factory=dict, description="Original request headers"
    )

    # Source metadata
    source_id: str | None = Field(
        None, description="ID of the event in the source system"
    )
    source_timestamp: datetime | None = Field(
        None, description="Timestamp from the source"
    )

    # Connection info
    connection_id: str | None = Field(
        None, description="Connection/integration ID this event came from"
    )

    # Ingestion metadata
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the event was received",
    )
    schema_version: str = Field(default="1.0", description="Event schema version")

    # Processing state
    processed: bool = Field(default=False, description="Whether event has been processed")
    processing_errors: list[str] = Field(
        default_factory=list, description="Any processing errors"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EventEnvelope(BaseModel):
    """Envelope for publishing events to the message queue.

    Wraps the raw event with routing and delivery metadata.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    event_id: str = Field(..., description="ID of the raw event")
    tenant_id: str = Field(..., description="Tenant ID for routing")

    # Routing
    source: EventSource = Field(..., description="Event source for routing")
    event_type: EventType = Field(..., description="Event type for routing")
    stream: str = Field(default="events", description="Target stream name")

    # Payload reference
    storage_path: str | None = Field(
        None, description="S3 path to full event payload"
    )
    payload_preview: dict[str, Any] = Field(
        default_factory=dict, description="Subset of payload for quick access"
    )

    # Delivery metadata
    published_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When envelope was published",
    )
    attempt: int = Field(default=1, description="Delivery attempt number")
    max_attempts: int = Field(default=3, description="Maximum delivery attempts")

    # Tracing
    trace_id: str | None = Field(None, description="Distributed trace ID")
    parent_span_id: str | None = Field(None, description="Parent span ID")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class WebhookPayload(BaseModel):
    """Incoming webhook payload wrapper."""

    source: EventSource = Field(..., description="Source system")
    event_type: str = Field(..., description="Event type header/field")
    payload: dict[str, Any] = Field(..., description="Raw payload body")
    headers: dict[str, str] = Field(
        default_factory=dict, description="Request headers"
    )
    signature: str | None = Field(None, description="Webhook signature if provided")
    delivery_id: str | None = Field(None, description="Delivery ID from source")

    # Connection context
    connection_id: str | None = Field(
        None, description="Pre-configured connection ID"
    )
    tenant_id: str | None = Field(None, description="Tenant ID from auth/path")


class EventQuery(BaseModel):
    """Query parameters for event retrieval."""

    tenant_id: str = Field(..., description="Tenant ID (required)")
    source: EventSource | None = Field(None, description="Filter by source")
    event_type: EventType | None = Field(None, description="Filter by event type")
    connection_id: str | None = Field(None, description="Filter by connection")

    # Time range
    start_time: datetime | None = Field(None, description="Start of time range")
    end_time: datetime | None = Field(None, description="End of time range")

    # Pagination
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    cursor: str | None = Field(None, description="Pagination cursor")

    # Processing state
    processed: bool | None = Field(None, description="Filter by processing state")


class EventStats(BaseModel):
    """Statistics about stored events."""

    tenant_id: str
    total_events: int = 0
    events_by_source: dict[str, int] = Field(default_factory=dict)
    events_by_type: dict[str, int] = Field(default_factory=dict)
    oldest_event: datetime | None = None
    newest_event: datetime | None = None
    storage_size_bytes: int = 0
