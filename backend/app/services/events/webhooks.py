"""Webhook handler for receiving events from external sources.

Provides:
- Generic webhook receiver
- Source-specific signature verification
- Event type normalization
- Automatic event storage and publishing
"""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.events.models import (
    EventSource,
    EventType,
    RawEvent,
    WebhookPayload,
)
from app.services.events.store import EventStore, get_event_store

logger = structlog.get_logger()


# Event type mappings for each source
GITHUB_EVENT_MAP: dict[str, EventType] = {
    "push": EventType.PUSH,
    "create": EventType.BRANCH_CREATE,
    "delete": EventType.BRANCH_DELETE,
    "pull_request": EventType.PR_OPENED,  # Will refine based on action
    "pull_request_review": EventType.PR_REVIEW,
    "pull_request_review_comment": EventType.PR_COMMENT,
    "issue_comment": EventType.PR_COMMENT,
    "issues": EventType.ISSUE_CREATED,
    "deployment": EventType.DEPLOY_STARTED,
    "deployment_status": EventType.DEPLOY_COMPLETED,
    "check_run": EventType.BUILD_COMPLETED,
    "check_suite": EventType.BUILD_COMPLETED,
    "workflow_run": EventType.BUILD_COMPLETED,
    "workflow_job": EventType.BUILD_STARTED,
}

GITLAB_EVENT_MAP: dict[str, EventType] = {
    "Push Hook": EventType.PUSH,
    "Tag Push Hook": EventType.TAG_CREATE,
    "Merge Request Hook": EventType.PR_OPENED,
    "Issue Hook": EventType.ISSUE_CREATED,
    "Note Hook": EventType.PR_COMMENT,
    "Pipeline Hook": EventType.BUILD_COMPLETED,
    "Job Hook": EventType.BUILD_STARTED,
    "Deployment Hook": EventType.DEPLOY_COMPLETED,
}

JIRA_EVENT_MAP: dict[str, EventType] = {
    "jira:issue_created": EventType.ISSUE_CREATED,
    "jira:issue_updated": EventType.ISSUE_UPDATED,
    "jira:issue_deleted": EventType.ISSUE_CLOSED,
    "comment_created": EventType.ISSUE_COMMENT,
    "comment_updated": EventType.ISSUE_COMMENT,
}

PAGERDUTY_EVENT_MAP: dict[str, EventType] = {
    "incident.triggered": EventType.INCIDENT_CREATED,
    "incident.acknowledged": EventType.INCIDENT_ACKNOWLEDGED,
    "incident.resolved": EventType.INCIDENT_RESOLVED,
    "incident.escalated": EventType.INCIDENT_UPDATED,
    "incident.reassigned": EventType.INCIDENT_UPDATED,
}

SLACK_EVENT_MAP: dict[str, EventType] = {
    "message": EventType.MESSAGE_SENT,
    "channel_created": EventType.CHANNEL_CREATED,
    "app_mention": EventType.MENTION,
}


class WebhookHandler:
    """Handler for incoming webhooks from various sources."""

    def __init__(self, event_store: EventStore | None = None):
        self.event_store = event_store or get_event_store()
        self._publisher = None  # Lazy load to avoid circular imports

    @property
    def publisher(self):
        """Lazy load publisher."""
        if self._publisher is None:
            from app.services.events.publisher import get_event_publisher
            self._publisher = get_event_publisher()
        return self._publisher

    async def handle_webhook(
        self,
        payload: WebhookPayload,
        session: AsyncSession | None = None,
        publish: bool = True,
    ) -> RawEvent:
        """Handle an incoming webhook.

        1. Verify signature (if applicable)
        2. Normalize event type
        3. Create RawEvent
        4. Store in event store
        5. Publish to message queue

        Args:
            payload: The webhook payload
            session: Optional database session for indexing
            publish: Whether to publish to message queue

        Returns:
            The created RawEvent
        """
        # Verify signature
        if not self._verify_signature(payload):
            raise ValueError("Invalid webhook signature")

        # Normalize event type
        event_type = self._normalize_event_type(
            payload.source,
            payload.event_type,
            payload.payload,
        )

        # Extract source ID and timestamp
        source_id, source_timestamp = self._extract_source_metadata(
            payload.source,
            payload.payload,
        )

        # Create raw event
        event = RawEvent(
            tenant_id=payload.tenant_id or "unknown",
            source=payload.source,
            source_event_type=payload.event_type,
            event_type=event_type,
            payload=payload.payload,
            headers=payload.headers,
            source_id=source_id,
            source_timestamp=source_timestamp,
            connection_id=payload.connection_id,
        )

        # Store event
        storage_path = await self.event_store.store(event, session)

        logger.info(
            "Webhook processed",
            event_id=event.id,
            source=event.source.value,
            event_type=event.event_type.value,
            storage_path=storage_path,
        )

        # Publish to queue
        if publish and self.publisher:
            await self.publisher.publish(event, storage_path)

        return event

    def _verify_signature(self, payload: WebhookPayload) -> bool:
        """Verify webhook signature based on source.

        Args:
            payload: The webhook payload with signature

        Returns:
            True if signature is valid or not required
        """
        if not payload.signature:
            # No signature provided - allow in dev, require in prod
            # For now, return True
            return True

        try:
            if payload.source == EventSource.GITHUB:
                return self._verify_github_signature(payload)
            elif payload.source == EventSource.GITLAB:
                return self._verify_gitlab_signature(payload)
            elif payload.source == EventSource.SLACK:
                return self._verify_slack_signature(payload)
            elif payload.source == EventSource.JIRA:
                return self._verify_jira_signature(payload)
            else:
                # Unknown source - accept without verification
                return True
        except Exception as e:
            logger.warning(
                "Signature verification failed",
                source=payload.source.value,
                error=str(e),
            )
            return False

    def _verify_github_signature(self, payload: WebhookPayload) -> bool:
        """Verify GitHub webhook signature (HMAC-SHA256)."""
        from app.core.config import settings

        secret = getattr(settings, "GITHUB_WEBHOOK_SECRET", None)
        if not secret:
            return True  # No secret configured

        signature = payload.signature
        if not signature or not signature.startswith("sha256="):
            return False

        expected_sig = signature[7:]  # Remove "sha256=" prefix
        payload_bytes = json.dumps(payload.payload, separators=(",", ":")).encode()

        computed = hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed, expected_sig)

    def _verify_gitlab_signature(self, payload: WebhookPayload) -> bool:
        """Verify GitLab webhook token."""
        from app.core.config import settings

        secret = getattr(settings, "GITLAB_WEBHOOK_SECRET", None)
        if not secret:
            return True

        token = payload.headers.get("X-Gitlab-Token", "")
        return hmac.compare_digest(token, secret)

    def _verify_slack_signature(self, payload: WebhookPayload) -> bool:
        """Verify Slack request signature."""
        from app.core.config import settings

        secret = getattr(settings, "SLACK_SIGNING_SECRET", None)
        if not secret:
            return True

        # Slack uses timestamp + body for signature
        timestamp = payload.headers.get("X-Slack-Request-Timestamp", "")
        signature = payload.headers.get("X-Slack-Signature", "")

        if not timestamp or not signature:
            return False

        # Check timestamp is recent (within 5 minutes)
        try:
            ts = int(timestamp)
            now = int(datetime.now(UTC).timestamp())
            if abs(now - ts) > 300:
                return False
        except ValueError:
            return False

        # Compute signature
        sig_basestring = f"v0:{timestamp}:{json.dumps(payload.payload)}"
        computed = "v0=" + hmac.new(
            secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed, signature)

    def _verify_jira_signature(self, payload: WebhookPayload) -> bool:
        """Verify Jira webhook (token-based)."""
        # Jira uses shared secrets - verify connection has valid token
        return True  # Implement based on your Jira setup

    def _normalize_event_type(
        self,
        source: EventSource,
        source_event_type: str,
        payload: dict[str, Any],
    ) -> EventType:
        """Normalize source-specific event type to canonical type.

        Args:
            source: Event source
            source_event_type: Original event type string
            payload: Event payload (for action-based refinement)

        Returns:
            Normalized EventType
        """
        if source == EventSource.GITHUB:
            event_type = GITHUB_EVENT_MAP.get(source_event_type, EventType.UNKNOWN)

            # Refine based on action
            action = payload.get("action", "")
            if source_event_type == "pull_request":
                if action == "opened":
                    event_type = EventType.PR_OPENED
                elif action == "closed":
                    if payload.get("pull_request", {}).get("merged"):
                        event_type = EventType.PR_MERGED
                    else:
                        event_type = EventType.PR_CLOSED
                elif action in ("synchronize", "edited"):
                    event_type = EventType.PR_UPDATED
            elif source_event_type == "issues":
                if action == "opened":
                    event_type = EventType.ISSUE_CREATED
                elif action == "closed":
                    event_type = EventType.ISSUE_CLOSED
                elif action in ("edited", "assigned", "labeled"):
                    event_type = EventType.ISSUE_UPDATED
            elif source_event_type == "deployment_status":
                state = payload.get("deployment_status", {}).get("state", "")
                if state == "success":
                    event_type = EventType.DEPLOY_COMPLETED
                elif state == "failure":
                    event_type = EventType.DEPLOY_FAILED

            return event_type

        elif source == EventSource.GITLAB:
            event_type = GITLAB_EVENT_MAP.get(source_event_type, EventType.UNKNOWN)

            # Refine MR events
            if source_event_type == "Merge Request Hook":
                action = payload.get("object_attributes", {}).get("action", "")
                state = payload.get("object_attributes", {}).get("state", "")
                if action == "open":
                    event_type = EventType.PR_OPENED
                elif action == "merge":
                    event_type = EventType.PR_MERGED
                elif action == "close":
                    event_type = EventType.PR_CLOSED
                elif action == "update":
                    event_type = EventType.PR_UPDATED

            return event_type

        elif source == EventSource.JIRA:
            return JIRA_EVENT_MAP.get(source_event_type, EventType.UNKNOWN)

        elif source == EventSource.PAGERDUTY:
            return PAGERDUTY_EVENT_MAP.get(source_event_type, EventType.UNKNOWN)

        elif source == EventSource.SLACK:
            event_type_str = payload.get("event", {}).get("type", source_event_type)
            return SLACK_EVENT_MAP.get(event_type_str, EventType.UNKNOWN)

        else:
            return EventType.WEBHOOK

    def _extract_source_metadata(
        self,
        source: EventSource,
        payload: dict[str, Any],
    ) -> tuple[str | None, datetime | None]:
        """Extract source ID and timestamp from payload.

        Args:
            source: Event source
            payload: Event payload

        Returns:
            Tuple of (source_id, source_timestamp)
        """
        source_id = None
        source_timestamp = None

        try:
            if source == EventSource.GITHUB:
                # GitHub uses various ID fields
                if "pull_request" in payload:
                    source_id = str(payload["pull_request"].get("id"))
                elif "issue" in payload:
                    source_id = str(payload["issue"].get("id"))
                elif "deployment" in payload:
                    source_id = str(payload["deployment"].get("id"))
                elif "head_commit" in payload:
                    source_id = payload["head_commit"].get("id")

                # Timestamp from various fields
                timestamp_str = None
                for field in ["created_at", "updated_at", "timestamp"]:
                    if field in payload:
                        timestamp_str = payload[field]
                        break
                    for obj in ["pull_request", "issue", "deployment", "head_commit"]:
                        if obj in payload and field in payload[obj]:
                            timestamp_str = payload[obj][field]
                            break

                if timestamp_str:
                    source_timestamp = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )

            elif source == EventSource.GITLAB:
                obj_attrs = payload.get("object_attributes", {})
                source_id = str(obj_attrs.get("id") or obj_attrs.get("iid"))

                timestamp_str = obj_attrs.get("created_at") or obj_attrs.get("updated_at")
                if timestamp_str:
                    source_timestamp = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )

            elif source == EventSource.JIRA:
                source_id = payload.get("issue", {}).get("id")
                timestamp_str = payload.get("timestamp")
                if timestamp_str:
                    # Jira uses milliseconds
                    source_timestamp = datetime.fromtimestamp(
                        int(timestamp_str) / 1000, tz=UTC
                    )

            elif source == EventSource.PAGERDUTY:
                event_data = payload.get("event", {})
                source_id = event_data.get("id")
                timestamp_str = event_data.get("occurred_at")
                if timestamp_str:
                    source_timestamp = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )

            elif source == EventSource.SLACK:
                source_id = payload.get("event_id")
                event_time = payload.get("event_time")
                if event_time:
                    source_timestamp = datetime.fromtimestamp(int(event_time), tz=UTC)

        except Exception as e:
            logger.warning(
                "Failed to extract source metadata",
                source=source.value,
                error=str(e),
            )

        return source_id, source_timestamp

    async def handle_github(
        self,
        event_type: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        tenant_id: str,
        connection_id: str | None = None,
        session: AsyncSession | None = None,
    ) -> RawEvent:
        """Convenience method for handling GitHub webhooks."""
        webhook = WebhookPayload(
            source=EventSource.GITHUB,
            event_type=event_type,
            payload=payload,
            headers=headers,
            signature=headers.get("X-Hub-Signature-256"),
            delivery_id=headers.get("X-GitHub-Delivery"),
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        return await self.handle_webhook(webhook, session)

    async def handle_gitlab(
        self,
        event_type: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        tenant_id: str,
        connection_id: str | None = None,
        session: AsyncSession | None = None,
    ) -> RawEvent:
        """Convenience method for handling GitLab webhooks."""
        webhook = WebhookPayload(
            source=EventSource.GITLAB,
            event_type=event_type,
            payload=payload,
            headers=headers,
            signature=headers.get("X-Gitlab-Token"),
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        return await self.handle_webhook(webhook, session)

    async def handle_jira(
        self,
        event_type: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        tenant_id: str,
        connection_id: str | None = None,
        session: AsyncSession | None = None,
    ) -> RawEvent:
        """Convenience method for handling Jira webhooks."""
        webhook = WebhookPayload(
            source=EventSource.JIRA,
            event_type=event_type,
            payload=payload,
            headers=headers,
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        return await self.handle_webhook(webhook, session)


# Global handler instance
_webhook_handler: WebhookHandler | None = None


def get_webhook_handler() -> WebhookHandler:
    """Get the global webhook handler instance."""
    global _webhook_handler
    if _webhook_handler is None:
        _webhook_handler = WebhookHandler()
    return _webhook_handler
