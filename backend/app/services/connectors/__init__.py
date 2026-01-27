"""Connector framework for external integrations.

This module provides:
- Base connector interface for all integrations
- Connector registry for managing multiple connectors
- Built-in connectors for common sources (GitHub, GitLab, Jira, etc.)
- OAuth token refresh and webhook signature verification
"""

from app.services.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorStatus,
    SyncResult,
    WebhookEvent,
)
from app.services.connectors.registry import ConnectorRegistry, get_connector_registry
from app.services.connectors.github import GitHubConnector
from app.services.connectors.gitlab import GitLabConnector
from app.services.connectors.jira import JiraConnector, JiraConfig
from app.services.connectors.slack import SlackConnector, SlackConfig
from app.services.connectors.pagerduty import PagerDutyConnector, PagerDutyConfig
from app.services.connectors.kubernetes import KubernetesConnector, KubernetesConfig

__all__ = [
    # Base
    "BaseConnector",
    "ConnectorConfig",
    "ConnectorStatus",
    "SyncResult",
    "WebhookEvent",
    # Registry
    "ConnectorRegistry",
    "get_connector_registry",
    # Connectors
    "GitHubConnector",
    "GitLabConnector",
    "JiraConnector",
    "JiraConfig",
    "SlackConnector",
    "SlackConfig",
    "PagerDutyConnector",
    "PagerDutyConfig",
    "KubernetesConnector",
    "KubernetesConfig",
]
