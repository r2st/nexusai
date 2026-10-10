"""SQLAlchemy models for the application."""

from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.document import Document, DocumentChunk
from app.models.organization import Organization, OrganizationMember, OrganizationInvite
from app.models.project import Project, ProjectMember
from app.models.connection import Connection, ConnectionScope
from app.models.ai_analytics import (
    AIUsageLog,
    AIAnalyticsMetric,
    AISummary,
    AIToolConnection,
    AIROIMetric,
)
from app.models.audit_log import (
    AuditLog,
    AuditEventType,
    AuditSeverity,
    ApprovalRecord,
)
from app.models.cost_entry import (
    CostEntry,
    CostBudget,
    CostAlert,
    RequestType,
)
from app.models.hallucination_log import (
    HallucinationLog,
    HallucinationMetric,
    CheckType,
)

__all__ = [
    # User
    "User",
    # Conversations
    "Conversation",
    "Message",
    # Documents
    "Document",
    "DocumentChunk",
    # Multi-tenancy
    "Organization",
    "OrganizationMember",
    "OrganizationInvite",
    "Project",
    "ProjectMember",
    # Connections
    "Connection",
    "ConnectionScope",
    # AI Analytics
    "AIUsageLog",
    "AIAnalyticsMetric",
    "AISummary",
    "AIToolConnection",
    "AIROIMetric",
    # Audit Logs
    "AuditLog",
    "AuditEventType",
    "AuditSeverity",
    "ApprovalRecord",
    # Cost Tracking
    "CostEntry",
    "CostBudget",
    "CostAlert",
    "RequestType",
    # Hallucination Detection
    "HallucinationLog",
    "HallucinationMetric",
    "CheckType",
]
