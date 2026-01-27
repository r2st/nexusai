"""Data models for Workflow Automation Engine."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkflowTriggerType(str, Enum):
    """Types of workflow triggers."""

    # Event-based triggers
    WEBHOOK = "webhook"
    SCHEDULE = "schedule"  # Cron-based
    EVENT = "event"  # Internal event bus

    # Code-related triggers
    PR_OPENED = "pr_opened"
    PR_MERGED = "pr_merged"
    PR_UPDATED = "pr_updated"
    COMMIT_PUSHED = "commit_pushed"
    BRANCH_CREATED = "branch_created"
    TAG_CREATED = "tag_created"

    # Quality triggers
    QUALITY_GATE_FAILED = "quality_gate_failed"
    QUALITY_GATE_PASSED = "quality_gate_passed"
    SECURITY_ISSUE_FOUND = "security_issue_found"
    CRITICAL_ISSUE_FOUND = "critical_issue_found"

    # Metrics triggers
    DORA_THRESHOLD_BREACH = "dora_threshold_breach"
    SLA_VIOLATION = "sla_violation"

    # Manual
    MANUAL = "manual"


class WorkflowStepType(str, Enum):
    """Types of workflow steps."""

    # Actions
    NOTIFICATION = "notification"  # Send notification
    WEBHOOK = "webhook"  # Call external webhook
    API_CALL = "api_call"  # Make API call
    SCRIPT = "script"  # Run custom script

    # Analysis
    CODE_ANALYSIS = "code_analysis"
    SECURITY_SCAN = "security_scan"
    CODE_REVIEW = "code_review"

    # Control flow
    CONDITION = "condition"  # If/else branch
    PARALLEL = "parallel"  # Run steps in parallel
    LOOP = "loop"  # Loop over items
    WAIT = "wait"  # Wait for duration or condition
    APPROVAL = "approval"  # Wait for human approval

    # Integration
    JIRA_CREATE = "jira_create"
    JIRA_UPDATE = "jira_update"
    GITHUB_COMMENT = "github_comment"
    GITLAB_COMMENT = "gitlab_comment"
    SLACK_MESSAGE = "slack_message"
    TEAMS_MESSAGE = "teams_message"

    # Data
    TRANSFORM = "transform"  # Transform data
    AGGREGATE = "aggregate"  # Aggregate data
    STORE = "store"  # Store to database


class WorkflowStatus(str, Enum):
    """Workflow definition status."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class WorkflowExecutionStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"  # Waiting for approval or condition
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class StepExecutionStatus(str, Enum):
    """Step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"


class WorkflowCondition(BaseModel):
    """A condition for workflow branching."""

    field: str  # Field path in context
    operator: str  # eq, ne, gt, lt, gte, lte, contains, regex
    value: Any


class WorkflowAction(BaseModel):
    """An action to perform in a step."""

    type: str
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowTrigger(BaseModel):
    """Workflow trigger configuration."""

    id: str
    type: WorkflowTriggerType
    enabled: bool = True

    # Event filters
    filters: dict[str, Any] = Field(default_factory=dict)

    # Schedule (for cron triggers)
    schedule: str | None = None  # Cron expression

    # Webhook config
    webhook_secret: str | None = None


class WorkflowStep(BaseModel):
    """A step in a workflow."""

    id: str
    name: str
    type: WorkflowStepType
    description: str | None = None

    # Step configuration
    config: dict[str, Any] = Field(default_factory=dict)

    # Control flow
    conditions: list[WorkflowCondition] = Field(default_factory=list)
    on_success: str | None = None  # Next step ID
    on_failure: str | None = None  # Step ID on failure
    on_skip: str | None = None  # Step ID if skipped

    # Retry policy
    retry_count: int = 0
    retry_delay_seconds: int = 60

    # Timeout
    timeout_seconds: int = 300

    # For parallel steps
    parallel_steps: list[str] = Field(default_factory=list)

    # For loop steps
    loop_over: str | None = None  # Field path to iterate
    loop_variable: str = "item"


class Workflow(BaseModel):
    """A workflow definition."""

    id: str
    name: str
    description: str | None = None
    organization_id: str

    # Status
    status: WorkflowStatus = WorkflowStatus.DRAFT
    version: int = 1

    # Triggers
    triggers: list[WorkflowTrigger] = Field(default_factory=list)

    # Steps
    steps: list[WorkflowStep] = Field(default_factory=list)
    entry_step_id: str | None = None  # First step to execute

    # Global configuration
    timeout_seconds: int = 3600  # 1 hour default
    max_concurrent_executions: int = 10

    # Input/Output schema
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str | None = None


class StepExecution(BaseModel):
    """Execution record for a workflow step."""

    id: str
    step_id: str
    step_name: str
    step_type: WorkflowStepType

    # Status
    status: StepExecutionStatus = StepExecutionStatus.PENDING

    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None

    # Data
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)

    # Error info
    error: str | None = None
    error_details: dict[str, Any] | None = None

    # Retry info
    attempt: int = 1
    retry_count: int = 0


class WorkflowExecution(BaseModel):
    """A workflow execution instance."""

    id: str
    workflow_id: str
    workflow_name: str
    workflow_version: int

    # Trigger info
    trigger_type: WorkflowTriggerType
    trigger_id: str | None = None

    # Status
    status: WorkflowExecutionStatus = WorkflowExecutionStatus.PENDING

    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None

    # Data
    input_data: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)

    # Steps
    step_executions: list[StepExecution] = Field(default_factory=list)
    current_step_id: str | None = None

    # Error info
    error: str | None = None
    error_step_id: str | None = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    triggered_by: str | None = None


# Pre-built workflow templates
WORKFLOW_TEMPLATES = {
    "pr_quality_check": {
        "name": "PR Quality Check",
        "description": "Automated quality checks on pull requests",
        "triggers": [
            {"type": "pr_opened", "filters": {}},
            {"type": "pr_updated", "filters": {}},
        ],
        "steps": [
            {
                "id": "analyze",
                "name": "Code Analysis",
                "type": "code_analysis",
                "config": {"include_security": True},
                "on_success": "check_quality",
            },
            {
                "id": "check_quality",
                "name": "Quality Gate Check",
                "type": "condition",
                "conditions": [{"field": "analysis.passed", "operator": "eq", "value": True}],
                "on_success": "notify_success",
                "on_failure": "notify_failure",
            },
            {
                "id": "notify_success",
                "name": "Success Notification",
                "type": "github_comment",
                "config": {
                    "body": "✅ Quality gate passed! Ready for review.",
                },
            },
            {
                "id": "notify_failure",
                "name": "Failure Notification",
                "type": "github_comment",
                "config": {
                    "body": "❌ Quality gate failed. Please review the issues.",
                },
            },
        ],
    },
    "security_alert": {
        "name": "Security Alert Response",
        "description": "Automated response to security issues",
        "triggers": [
            {"type": "security_issue_found", "filters": {"severity": "critical"}},
        ],
        "steps": [
            {
                "id": "notify_security",
                "name": "Notify Security Team",
                "type": "notification",
                "config": {
                    "channels": ["slack", "email"],
                    "priority": "critical",
                },
                "on_success": "create_ticket",
            },
            {
                "id": "create_ticket",
                "name": "Create JIRA Ticket",
                "type": "jira_create",
                "config": {
                    "project": "SEC",
                    "issue_type": "Bug",
                    "priority": "Critical",
                },
            },
        ],
    },
    "deployment_tracking": {
        "name": "Deployment Tracking",
        "description": "Track deployments for DORA metrics",
        "triggers": [
            {"type": "webhook", "filters": {"event": "deployment"}},
        ],
        "steps": [
            {
                "id": "record_deployment",
                "name": "Record Deployment",
                "type": "api_call",
                "config": {
                    "endpoint": "/api/events/ingest",
                    "method": "POST",
                },
                "on_success": "calculate_metrics",
            },
            {
                "id": "calculate_metrics",
                "name": "Update DORA Metrics",
                "type": "api_call",
                "config": {
                    "endpoint": "/api/metrics/dora/calculate",
                    "method": "POST",
                },
                "on_success": "check_thresholds",
            },
            {
                "id": "check_thresholds",
                "name": "Check Metric Thresholds",
                "type": "condition",
                "conditions": [
                    {"field": "metrics.deployment_frequency", "operator": "gte", "value": 1},
                ],
                "on_failure": "alert_metrics",
            },
            {
                "id": "alert_metrics",
                "name": "Alert on Metric Threshold",
                "type": "notification",
                "config": {
                    "channels": ["slack"],
                    "message": "DORA metrics below threshold",
                },
            },
        ],
    },
    "weekly_report": {
        "name": "Weekly Engineering Report",
        "description": "Generate and send weekly engineering report",
        "triggers": [
            {"type": "schedule", "schedule": "0 9 * * MON"},  # Monday 9 AM
        ],
        "steps": [
            {
                "id": "gather_metrics",
                "name": "Gather DORA Metrics",
                "type": "api_call",
                "config": {
                    "endpoint": "/api/metrics/dora",
                    "method": "GET",
                },
                "on_success": "gather_space",
            },
            {
                "id": "gather_space",
                "name": "Gather SPACE Metrics",
                "type": "api_call",
                "config": {
                    "endpoint": "/api/metrics/space",
                    "method": "GET",
                },
                "on_success": "generate_report",
            },
            {
                "id": "generate_report",
                "name": "Generate Report",
                "type": "transform",
                "config": {
                    "template": "weekly_report",
                },
                "on_success": "send_report",
            },
            {
                "id": "send_report",
                "name": "Send Report",
                "type": "notification",
                "config": {
                    "channels": ["email", "slack"],
                    "recipients": ["engineering-leads"],
                },
            },
        ],
    },
}
