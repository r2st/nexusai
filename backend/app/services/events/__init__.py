"""Event ingestion service for raw event capture and processing.

This module provides:
- Generic webhook receiver for any source
- Immutable event store (S3-backed)
- Event publishing to message queue
- Schema versioning and replay capability
"""

from app.services.events.models import (
    RawEvent,
    EventEnvelope,
    EventSource,
    EventType,
    WebhookPayload,
    EventQuery,
    EventStats,
)
from app.services.events.store import EventStore, get_event_store
from app.services.events.publisher import EventPublisher, get_event_publisher
from app.services.events.webhooks import WebhookHandler, get_webhook_handler

__all__ = [
    # Models
    "RawEvent",
    "EventEnvelope",
    "EventSource",
    "EventType",
    "WebhookPayload",
    "EventQuery",
    "EventStats",
    # Store
    "EventStore",
    "get_event_store",
    # Publisher
    "EventPublisher",
    "get_event_publisher",
    # Webhooks
    "WebhookHandler",
    "get_webhook_handler",
]
