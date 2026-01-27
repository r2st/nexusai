"""Unit tests for event ingestion service."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.events.models import (
    EventEnvelope,
    EventQuery,
    EventSource,
    EventType,
    RawEvent,
    WebhookPayload,
)
from app.services.events.webhooks import WebhookHandler
from app.services.events.publisher import EventPublisher
from app.services.events.store import EventStore


class TestEventModels:
    """Tests for event models."""

    def test_raw_event_creation(self):
        """Test RawEvent model creation."""
        event = RawEvent(
            tenant_id="tenant-123",
            source=EventSource.GITHUB,
            source_event_type="push",
            event_type=EventType.PUSH,
            payload={"ref": "refs/heads/main"},
        )

        assert event.id is not None
        assert event.tenant_id == "tenant-123"
        assert event.source == EventSource.GITHUB
        assert event.event_type == EventType.PUSH
        assert event.processed is False
        assert event.schema_version == "1.0"

    def test_event_envelope_creation(self):
        """Test EventEnvelope model creation."""
        envelope = EventEnvelope(
            event_id="event-123",
            tenant_id="tenant-123",
            source=EventSource.GITHUB,
            event_type=EventType.PUSH,
            storage_path="tenant-123/events/github/2026/01/19/event-123.json",
        )

        assert envelope.id is not None
        assert envelope.event_id == "event-123"
        assert envelope.stream == "events"
        assert envelope.attempt == 1

    def test_webhook_payload_creation(self):
        """Test WebhookPayload model creation."""
        payload = WebhookPayload(
            source=EventSource.GITHUB,
            event_type="push",
            payload={"ref": "refs/heads/main"},
            headers={"x-github-event": "push"},
            signature="sha256=abc123",
            tenant_id="tenant-123",
        )

        assert payload.source == EventSource.GITHUB
        assert payload.signature == "sha256=abc123"

    def test_event_query_defaults(self):
        """Test EventQuery default values."""
        query = EventQuery(tenant_id="tenant-123")

        assert query.tenant_id == "tenant-123"
        assert query.limit == 100
        assert query.offset == 0
        assert query.source is None


class TestWebhookHandler:
    """Tests for webhook handler."""

    @pytest.fixture
    def handler(self):
        """Create webhook handler with mocked dependencies."""
        handler = WebhookHandler()
        handler.event_store = AsyncMock(spec=EventStore)
        handler.event_store.store.return_value = "path/to/event.json"
        handler._publisher = AsyncMock(spec=EventPublisher)
        return handler

    @pytest.mark.asyncio
    async def test_handle_github_push(self, handler):
        """Test handling GitHub push event."""
        payload = WebhookPayload(
            source=EventSource.GITHUB,
            event_type="push",
            payload={
                "ref": "refs/heads/main",
                "repository": {"name": "test-repo"},
                "head_commit": {"id": "abc123"},
            },
            headers={"x-github-event": "push"},
            tenant_id="tenant-123",
        )

        event = await handler.handle_webhook(payload)

        assert event.source == EventSource.GITHUB
        assert event.event_type == EventType.PUSH
        assert event.tenant_id == "tenant-123"
        handler.event_store.store.assert_called_once()
        handler._publisher.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_github_pr_opened(self, handler):
        """Test handling GitHub PR opened event."""
        payload = WebhookPayload(
            source=EventSource.GITHUB,
            event_type="pull_request",
            payload={
                "action": "opened",
                "pull_request": {"id": 123, "title": "Test PR"},
            },
            headers={},
            tenant_id="tenant-123",
        )

        event = await handler.handle_webhook(payload)

        assert event.event_type == EventType.PR_OPENED

    @pytest.mark.asyncio
    async def test_handle_github_pr_merged(self, handler):
        """Test handling GitHub PR merged event."""
        payload = WebhookPayload(
            source=EventSource.GITHUB,
            event_type="pull_request",
            payload={
                "action": "closed",
                "pull_request": {"id": 123, "merged": True},
            },
            headers={},
            tenant_id="tenant-123",
        )

        event = await handler.handle_webhook(payload)

        assert event.event_type == EventType.PR_MERGED

    @pytest.mark.asyncio
    async def test_handle_gitlab_merge_request(self, handler):
        """Test handling GitLab merge request event."""
        payload = WebhookPayload(
            source=EventSource.GITLAB,
            event_type="Merge Request Hook",
            payload={
                "object_attributes": {
                    "id": 123,
                    "action": "open",
                    "state": "opened",
                },
            },
            headers={},
            tenant_id="tenant-123",
        )

        event = await handler.handle_webhook(payload)

        assert event.source == EventSource.GITLAB
        assert event.event_type == EventType.PR_OPENED

    @pytest.mark.asyncio
    async def test_handle_jira_issue_created(self, handler):
        """Test handling Jira issue created event."""
        payload = WebhookPayload(
            source=EventSource.JIRA,
            event_type="jira:issue_created",
            payload={
                "issue": {"id": "10001", "key": "TEST-1"},
                "timestamp": "1705680000000",
            },
            headers={},
            tenant_id="tenant-123",
        )

        event = await handler.handle_webhook(payload)

        assert event.source == EventSource.JIRA
        assert event.event_type == EventType.ISSUE_CREATED

    @pytest.mark.asyncio
    async def test_handle_pagerduty_incident(self, handler):
        """Test handling PagerDuty incident event."""
        payload = WebhookPayload(
            source=EventSource.PAGERDUTY,
            event_type="incident.triggered",
            payload={
                "event": {
                    "id": "incident-123",
                    "occurred_at": "2026-01-19T12:00:00Z",
                },
            },
            headers={},
            tenant_id="tenant-123",
        )

        event = await handler.handle_webhook(payload)

        assert event.source == EventSource.PAGERDUTY
        assert event.event_type == EventType.INCIDENT_CREATED

    @pytest.mark.asyncio
    async def test_skip_publish_when_disabled(self, handler):
        """Test skipping publish when disabled."""
        payload = WebhookPayload(
            source=EventSource.GITHUB,
            event_type="push",
            payload={"ref": "refs/heads/main"},
            headers={},
            tenant_id="tenant-123",
        )

        await handler.handle_webhook(payload, publish=False)

        handler._publisher.publish.assert_not_called()

    def test_normalize_unknown_event_type(self, handler):
        """Test normalizing unknown event type."""
        event_type = handler._normalize_event_type(
            EventSource.GITHUB,
            "unknown_event",
            {},
        )

        assert event_type == EventType.UNKNOWN

    def test_extract_github_metadata(self, handler):
        """Test extracting metadata from GitHub payload."""
        source_id, source_timestamp = handler._extract_source_metadata(
            EventSource.GITHUB,
            {
                "head_commit": {
                    "id": "abc123",
                    "timestamp": "2026-01-19T12:00:00Z",
                },
            },
        )

        assert source_id == "abc123"
        assert source_timestamp is not None


class TestEventPublisher:
    """Tests for event publisher."""

    @pytest.fixture
    def publisher(self):
        """Create publisher instance."""
        return EventPublisher()

    @pytest.mark.asyncio
    async def test_publish_to_memory_queue(self, publisher):
        """Test publishing to in-memory queue."""
        event = RawEvent(
            tenant_id="tenant-123",
            source=EventSource.GITHUB,
            source_event_type="push",
            event_type=EventType.PUSH,
            payload={"ref": "refs/heads/main"},
        )

        msg_id = await publisher.publish(event, "path/to/event.json")

        assert msg_id is not None
        assert publisher._memory_queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_subscriber_notification(self, publisher):
        """Test in-memory subscriber notification."""
        received_events = []

        async def subscriber(envelope):
            received_events.append(envelope)

        publisher.subscribe_memory(subscriber)

        event = RawEvent(
            tenant_id="tenant-123",
            source=EventSource.GITHUB,
            source_event_type="push",
            event_type=EventType.PUSH,
            payload={},
        )

        await publisher.publish(event)

        assert len(received_events) == 1
        assert received_events[0].event_id == event.id

    @pytest.mark.asyncio
    async def test_unsubscribe(self, publisher):
        """Test unsubscribing from in-memory queue."""
        received_events = []

        async def subscriber(envelope):
            received_events.append(envelope)

        publisher.subscribe_memory(subscriber)
        publisher.unsubscribe_memory(subscriber)

        event = RawEvent(
            tenant_id="tenant-123",
            source=EventSource.GITHUB,
            source_event_type="push",
            event_type=EventType.PUSH,
            payload={},
        )

        await publisher.publish(event)

        assert len(received_events) == 0

    @pytest.mark.asyncio
    async def test_publish_batch(self, publisher):
        """Test batch publishing."""
        events = [
            (
                RawEvent(
                    tenant_id="tenant-123",
                    source=EventSource.GITHUB,
                    source_event_type="push",
                    event_type=EventType.PUSH,
                    payload={},
                ),
                "path/1.json",
            ),
            (
                RawEvent(
                    tenant_id="tenant-123",
                    source=EventSource.GITHUB,
                    source_event_type="push",
                    event_type=EventType.PUSH,
                    payload={},
                ),
                "path/2.json",
            ),
        ]

        msg_ids = await publisher.publish_batch(events)

        assert len(msg_ids) == 2
        assert publisher._memory_queue.qsize() == 2

    @pytest.mark.asyncio
    async def test_get_stats(self, publisher):
        """Test getting publisher stats."""
        stats = await publisher.get_stats()

        assert "connected" in stats
        assert "using_nats" in stats
        assert "memory_queue_size" in stats

    def test_create_payload_preview(self, publisher):
        """Test payload preview creation."""
        payload = {
            "action": "opened",
            "sender": {"login": "user1", "id": 123},
            "repository": {"name": "test-repo", "full_name": "org/test-repo"},
            "extra_field": "should_not_be_included" * 100,
        }

        preview = publisher._create_payload_preview(payload)

        assert "action" in preview
        assert preview["sender"]["login"] == "user1"
        assert "extra_field" not in preview


class TestEventStore:
    """Tests for event store."""

    @pytest.fixture
    def store(self):
        """Create event store with mocked storage."""
        store = EventStore()
        store.storage = AsyncMock()
        return store

    def test_get_storage_path(self, store):
        """Test storage path generation."""
        event = RawEvent(
            tenant_id="tenant-123",
            source=EventSource.GITHUB,
            source_event_type="push",
            event_type=EventType.PUSH,
            payload={},
            received_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
        )

        path = store._get_storage_path(event)

        assert path.startswith("tenant-123/events/github/2026/01/19/")
        assert path.endswith(".json")

    @pytest.mark.asyncio
    async def test_store_event(self, store):
        """Test storing an event."""
        event = RawEvent(
            tenant_id="tenant-123",
            source=EventSource.GITHUB,
            source_event_type="push",
            event_type=EventType.PUSH,
            payload={"ref": "refs/heads/main"},
        )

        path = await store.store(event)

        assert path is not None
        store.storage.upload.assert_called_once()

        # Verify upload call
        call_args = store.storage.upload.call_args
        assert call_args.kwargs["content_type"] == "application/json"
        assert call_args.kwargs["metadata"]["tenant_id"] == "tenant-123"

    @pytest.mark.asyncio
    async def test_get_by_path(self, store):
        """Test retrieving event by path."""
        event_data = RawEvent(
            tenant_id="tenant-123",
            source=EventSource.GITHUB,
            source_event_type="push",
            event_type=EventType.PUSH,
            payload={"ref": "refs/heads/main"},
        )

        store.storage.download.return_value = event_data.model_dump_json().encode()

        result = await store.get_by_path("path/to/event.json")

        assert result is not None
        assert result.tenant_id == "tenant-123"
        assert result.source == EventSource.GITHUB

    @pytest.mark.asyncio
    async def test_get_by_path_not_found(self, store):
        """Test retrieving non-existent event."""
        store.storage.download.return_value = None

        result = await store.get_by_path("path/to/nonexistent.json")

        assert result is None


class TestEventSourceMapping:
    """Tests for event source enumeration."""

    def test_all_sources_have_values(self):
        """Test all event sources have string values."""
        for source in EventSource:
            assert isinstance(source.value, str)
            assert len(source.value) > 0

    def test_all_event_types_have_values(self):
        """Test all event types have string values."""
        for event_type in EventType:
            assert isinstance(event_type.value, str)
            assert len(event_type.value) > 0

    def test_common_sources_exist(self):
        """Test common sources are defined."""
        common_sources = [
            "github", "gitlab", "jira", "slack",
            "pagerduty", "kubernetes", "jenkins",
        ]

        source_values = [s.value for s in EventSource]
        for source in common_sources:
            assert source in source_values

    def test_common_event_types_exist(self):
        """Test common event types are defined."""
        common_types = [
            "push", "pr_opened", "pr_merged", "pr_closed",
            "issue_created", "build_completed", "deploy_completed",
            "incident_created", "incident_resolved",
        ]

        type_values = [t.value for t in EventType]
        for event_type in common_types:
            assert event_type in type_values
