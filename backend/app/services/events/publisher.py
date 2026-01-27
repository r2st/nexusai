"""Event publisher for message queue integration.

Publishes events to NATS JetStream for async processing.
Supports fallback to in-memory queue for local development.
"""

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog

from app.core.config import settings
from app.services.events.models import (
    EventEnvelope,
    EventSource,
    EventType,
    RawEvent,
)

logger = structlog.get_logger()


class EventPublisher:
    """Publisher for events to message queue.

    Supports NATS JetStream in production and in-memory queue for development.
    """

    # Stream configuration
    STREAM_NAME = "EVENTS"
    SUBJECTS = {
        "all": "events.>",
        "by_source": "events.{source}.>",
        "by_type": "events.{source}.{event_type}",
    }

    def __init__(self):
        self._nc = None  # NATS connection
        self._js = None  # JetStream context
        self._connected = False

        # In-memory fallback
        self._memory_queue: asyncio.Queue[EventEnvelope] = asyncio.Queue()
        self._subscribers: list[Callable] = []

        # Configuration
        self._nats_url = getattr(settings, "NATS_URL", "nats://localhost:4222")
        self._use_nats = getattr(settings, "USE_NATS", False)

    async def connect(self) -> None:
        """Connect to NATS JetStream."""
        if not self._use_nats:
            logger.info("NATS disabled, using in-memory queue")
            return

        try:
            import nats
            from nats.js.api import StreamConfig, RetentionPolicy, StorageType

            self._nc = await nats.connect(
                self._nats_url,
                name="nexusai-publisher",
                reconnect_time_wait=2,
                max_reconnect_attempts=5,
            )

            # Get JetStream context
            self._js = self._nc.jetstream()

            # Create or update stream
            try:
                await self._js.add_stream(
                    StreamConfig(
                        name=self.STREAM_NAME,
                        subjects=["events.>"],
                        retention=RetentionPolicy.LIMITS,
                        storage=StorageType.FILE,
                        max_age=7 * 24 * 60 * 60,  # 7 days retention
                        max_msgs=10_000_000,
                        max_bytes=10 * 1024 * 1024 * 1024,  # 10GB
                        duplicate_window=60,  # 60 second dedup window
                    )
                )
                logger.info("Created NATS stream", stream=self.STREAM_NAME)
            except Exception as e:
                if "already in use" in str(e).lower():
                    logger.info("NATS stream exists", stream=self.STREAM_NAME)
                else:
                    raise

            self._connected = True
            logger.info("Connected to NATS", url=self._nats_url)

        except ImportError:
            logger.warning("nats-py not installed, using in-memory queue")
            self._use_nats = False
        except Exception as e:
            logger.error("Failed to connect to NATS", error=str(e))
            self._use_nats = False

    async def disconnect(self) -> None:
        """Disconnect from NATS."""
        if self._nc and self._connected:
            await self._nc.drain()
            await self._nc.close()
            self._connected = False
            logger.info("Disconnected from NATS")

    async def publish(
        self,
        event: RawEvent,
        storage_path: str | None = None,
        trace_id: str | None = None,
    ) -> str:
        """Publish an event to the message queue.

        Args:
            event: The raw event to publish
            storage_path: S3 path to the full event
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Message ID
        """
        # Create envelope
        envelope = EventEnvelope(
            event_id=event.id,
            tenant_id=event.tenant_id,
            source=event.source,
            event_type=event.event_type,
            stream=self.STREAM_NAME,
            storage_path=storage_path,
            payload_preview=self._create_payload_preview(event.payload),
            trace_id=trace_id or str(uuid4()),
        )

        # Build subject
        subject = f"events.{event.source.value}.{event.event_type.value}"

        if self._use_nats and self._js:
            return await self._publish_nats(envelope, subject)
        else:
            return await self._publish_memory(envelope)

    async def _publish_nats(
        self,
        envelope: EventEnvelope,
        subject: str,
    ) -> str:
        """Publish to NATS JetStream."""
        try:
            payload = envelope.model_dump_json().encode()

            # Publish with message ID for deduplication
            ack = await self._js.publish(
                subject,
                payload,
                headers={
                    "Nats-Msg-Id": envelope.id,
                    "tenant-id": envelope.tenant_id,
                    "source": envelope.source.value,
                    "event-type": envelope.event_type.value,
                },
            )

            logger.debug(
                "Published to NATS",
                subject=subject,
                msg_id=envelope.id,
                stream=ack.stream,
                seq=ack.seq,
            )

            return envelope.id

        except Exception as e:
            logger.error(
                "Failed to publish to NATS",
                subject=subject,
                error=str(e),
            )
            # Fallback to memory queue
            return await self._publish_memory(envelope)

    async def _publish_memory(self, envelope: EventEnvelope) -> str:
        """Publish to in-memory queue (development fallback)."""
        await self._memory_queue.put(envelope)

        # Notify subscribers
        for subscriber in self._subscribers:
            try:
                await subscriber(envelope)
            except Exception as e:
                logger.error(
                    "Subscriber error",
                    subscriber=subscriber.__name__,
                    error=str(e),
                )

        logger.debug(
            "Published to memory queue",
            msg_id=envelope.id,
            queue_size=self._memory_queue.qsize(),
        )

        return envelope.id

    def _create_payload_preview(
        self,
        payload: dict[str, Any],
        max_keys: int = 10,
    ) -> dict[str, Any]:
        """Create a preview of the payload for quick access.

        Extracts commonly needed fields without storing the full payload.
        """
        preview = {}

        # Common fields to extract
        preview_fields = [
            "action",
            "sender",
            "repository",
            "organization",
            "ref",
            "before",
            "after",
        ]

        for field in preview_fields:
            if field in payload:
                value = payload[field]
                if isinstance(value, dict):
                    # Extract just the name/login for nested objects
                    preview[field] = {
                        k: v
                        for k, v in value.items()
                        if k in ("name", "login", "full_name", "id", "url")
                    }
                elif isinstance(value, (str, int, bool)):
                    preview[field] = value

        # Limit size
        return dict(list(preview.items())[:max_keys])

    async def publish_batch(
        self,
        events: list[tuple[RawEvent, str]],
        trace_id: str | None = None,
    ) -> list[str]:
        """Publish multiple events in a batch.

        Args:
            events: List of (event, storage_path) tuples
            trace_id: Optional shared trace ID

        Returns:
            List of message IDs
        """
        trace_id = trace_id or str(uuid4())
        message_ids = []

        for event, storage_path in events:
            msg_id = await self.publish(event, storage_path, trace_id)
            message_ids.append(msg_id)

        logger.info(
            "Published batch",
            count=len(events),
            trace_id=trace_id,
        )

        return message_ids

    def subscribe_memory(self, callback: Callable) -> None:
        """Subscribe to in-memory queue (for testing/development).

        Args:
            callback: Async function to call for each envelope
        """
        self._subscribers.append(callback)

    def unsubscribe_memory(self, callback: Callable) -> None:
        """Unsubscribe from in-memory queue."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def get_stats(self) -> dict[str, Any]:
        """Get publisher statistics."""
        stats = {
            "connected": self._connected,
            "using_nats": self._use_nats,
            "memory_queue_size": self._memory_queue.qsize(),
            "subscribers": len(self._subscribers),
        }

        if self._js and self._connected:
            try:
                stream_info = await self._js.stream_info(self.STREAM_NAME)
                stats["stream"] = {
                    "name": stream_info.config.name,
                    "messages": stream_info.state.messages,
                    "bytes": stream_info.state.bytes,
                    "first_seq": stream_info.state.first_seq,
                    "last_seq": stream_info.state.last_seq,
                    "consumer_count": stream_info.state.consumer_count,
                }
            except Exception as e:
                stats["stream_error"] = str(e)

        return stats


# Global publisher instance
_event_publisher: EventPublisher | None = None


def get_event_publisher() -> EventPublisher:
    """Get the global event publisher instance."""
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = EventPublisher()
    return _event_publisher


async def init_publisher() -> EventPublisher:
    """Initialize and connect the event publisher."""
    publisher = get_event_publisher()
    await publisher.connect()
    return publisher
