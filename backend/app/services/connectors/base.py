"""Base connector interface for external integrations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class ConnectorStatus(str, Enum):
    """Connector status states."""

    PENDING = "pending"
    ACTIVE = "active"
    ERROR = "error"
    DISCONNECTED = "disconnected"
    RATE_LIMITED = "rate_limited"
    TOKEN_EXPIRED = "token_expired"


class ConnectorConfig(BaseModel):
    """Configuration for a connector instance."""

    id: str = Field(..., description="Unique connector ID")
    tenant_id: str = Field(..., description="Tenant ID")
    source: str = Field(..., description="Source type (github, gitlab, etc)")
    name: str = Field(..., description="Display name")

    # Connection settings
    endpoint: str | None = Field(None, description="API endpoint URL")
    webhook_url: str | None = Field(None, description="Webhook callback URL")

    # Authentication
    auth_type: str = Field(default="token", description="Auth type: token, oauth, app")
    credentials: dict[str, Any] = Field(
        default_factory=dict,
        description="Encrypted credentials (token, client_id, etc)",
    )

    # OAuth
    oauth_access_token: str | None = None
    oauth_refresh_token: str | None = None
    oauth_token_expires_at: datetime | None = None

    # Configuration
    scopes: list[str] = Field(default_factory=list, description="Requested scopes")
    config: dict[str, Any] = Field(default_factory=dict, description="Additional config")

    # Sync settings
    sync_enabled: bool = Field(default=True)
    sync_interval_minutes: int = Field(default=60)
    last_sync_at: datetime | None = None
    next_sync_at: datetime | None = None

    # Status
    status: ConnectorStatus = Field(default=ConnectorStatus.PENDING)
    status_message: str | None = None
    error_count: int = 0


@dataclass
class SyncResult:
    """Result of a connector sync operation."""

    success: bool
    connector_id: str
    source: str

    # Counts
    events_fetched: int = 0
    events_stored: int = 0
    entities_created: int = 0
    entities_updated: int = 0
    errors: int = 0

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    duration_seconds: float = 0

    # Pagination
    has_more: bool = False
    next_cursor: str | None = None

    # Error details
    error_message: str | None = None
    error_details: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.completed_at:
            self.duration_seconds = (
                self.completed_at - self.started_at
            ).total_seconds()


@dataclass
class WebhookEvent:
    """Standard webhook event payload for connectors."""

    source: str
    event_type: str
    payload: dict[str, Any]
    received_at: datetime
    resource_id: str | None = None
    resource_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseConnector(ABC):
    """Abstract base class for all connectors.

    Connectors handle:
    - API communication with external services
    - Webhook signature verification
    - OAuth token refresh
    - Data synchronization
    - Rate limit handling
    """

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self._client = None
        self._rate_limit_remaining: int | None = None
        self._rate_limit_reset: datetime | None = None

    @property
    @abstractmethod
    def source(self) -> str:
        """Return the source identifier."""
        pass

    @property
    def connector_id(self) -> str:
        """Return the connector ID."""
        return self.config.id

    @property
    def tenant_id(self) -> str:
        """Return the tenant ID."""
        return self.config.tenant_id

    # Connection management

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the external service.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the external service."""
        pass

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """Test the connection.

        Returns:
            Tuple of (success, message)
        """
        pass

    # Synchronization

    @abstractmethod
    async def sync(
        self,
        full_sync: bool = False,
        since: datetime | None = None,
    ) -> SyncResult:
        """Synchronize data from the external service.

        Args:
            full_sync: If True, sync all data. If False, incremental sync.
            since: Only sync data modified after this time.

        Returns:
            SyncResult with sync statistics
        """
        pass

    @abstractmethod
    async def sync_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> SyncResult:
        """Sync a specific entity.

        Args:
            entity_type: Type of entity to sync
            entity_id: ID of the entity

        Returns:
            SyncResult
        """
        pass

    # Webhooks

    @abstractmethod
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        headers: dict[str, str],
    ) -> bool:
        """Verify webhook signature.

        Args:
            payload: Raw webhook payload
            signature: Signature from headers
            headers: All webhook headers

        Returns:
            True if signature is valid
        """
        pass

    @abstractmethod
    async def setup_webhooks(
        self,
        webhook_url: str,
        events: list[str] | None = None,
    ) -> dict[str, Any]:
        """Set up webhooks for the connector.

        Args:
            webhook_url: URL to receive webhooks
            events: List of event types to subscribe to

        Returns:
            Webhook configuration details
        """
        pass

    # OAuth

    async def refresh_oauth_token(self) -> bool:
        """Refresh OAuth access token.

        Returns:
            True if refresh successful
        """
        # Default implementation - override in subclass
        logger.warning(
            "OAuth refresh not implemented",
            source=self.source,
            connector_id=self.connector_id,
        )
        return False

    def is_token_expired(self) -> bool:
        """Check if OAuth token is expired."""
        if not self.config.oauth_token_expires_at:
            return False

        # Consider expired 5 minutes before actual expiry
        buffer = 300  # seconds
        return datetime.now(UTC) >= self.config.oauth_token_expires_at

    # Rate limiting

    def check_rate_limit(self) -> bool:
        """Check if rate limited.

        Returns:
            True if requests are allowed
        """
        if self._rate_limit_remaining is None:
            return True

        if self._rate_limit_remaining <= 0:
            if self._rate_limit_reset and datetime.now(UTC) < self._rate_limit_reset:
                return False

        return True

    def update_rate_limit(
        self,
        remaining: int | None,
        reset_at: datetime | None,
    ) -> None:
        """Update rate limit state from API response."""
        self._rate_limit_remaining = remaining
        self._rate_limit_reset = reset_at

    # Helpers

    async def ensure_connected(self) -> None:
        """Ensure connector is connected."""
        if self._client is None:
            await self.connect()

    def get_status(self) -> dict[str, Any]:
        """Get connector status."""
        return {
            "id": self.config.id,
            "source": self.source,
            "status": self.config.status.value,
            "status_message": self.config.status_message,
            "last_sync_at": self.config.last_sync_at,
            "next_sync_at": self.config.next_sync_at,
            "rate_limit_remaining": self._rate_limit_remaining,
            "rate_limit_reset": self._rate_limit_reset,
            "error_count": self.config.error_count,
        }

    def update_status(
        self,
        status: ConnectorStatus,
        message: str | None = None,
    ) -> None:
        """Update connector status."""
        self.config.status = status
        self.config.status_message = message

        if status == ConnectorStatus.ERROR:
            self.config.error_count += 1

        logger.info(
            "Connector status updated",
            connector_id=self.config.id,
            source=self.source,
            status=status.value,
            message=message,
        )
