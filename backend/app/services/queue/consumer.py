"""Consumer for processing messages from NATS JetStream."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable

import structlog

from app.services.queue.client import NATSClient, get_nats_client

logger = structlog.get_logger()


@dataclass
class ConsumerConfig:
    """Configuration for a message consumer."""

    name: str
    stream: str
    subject: str | None = None  # Filter subject
    durable: bool = True
    ack_wait_seconds: int = 30
    max_deliver: int = 3
    max_ack_pending: int = 1000
    batch_size: int = 100
    poll_timeout_ms: int = 5000
    retry_delay_seconds: int = 5


@dataclass
class ProcessingResult:
    """Result of message processing."""

    success: bool
    message_id: str
    error: str | None = None
    should_retry: bool = False
    delay_seconds: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class Consumer(ABC):
    """Abstract base class for message consumers.

    Consumers process messages from a NATS JetStream stream.
    Subclasses implement the process_message method.
    """

    def __init__(
        self,
        config: ConsumerConfig,
        client: NATSClient | None = None,
    ):
        self.config = config
        self.client = client or get_nats_client()
        self._subscription = None
        self._running = False
        self._processed_count = 0
        self._error_count = 0
        self._started_at: datetime | None = None

    @abstractmethod
    async def process_message(self, data: bytes, metadata: dict[str, Any]) -> ProcessingResult:
        """Process a single message.

        Args:
            data: Message payload
            metadata: Message metadata (headers, subject, etc.)

        Returns:
            ProcessingResult indicating success/failure
        """
        pass

    async def start(self) -> None:
        """Start consuming messages."""
        if self._running:
            return

        try:
            from nats.js.api import ConsumerConfig as NATSConsumerConfig
            from nats.js.api import AckPolicy, DeliverPolicy

            # Create consumer configuration
            consumer_config = NATSConsumerConfig(
                name=self.config.name,
                durable_name=self.config.name if self.config.durable else None,
                filter_subject=self.config.subject,
                ack_policy=AckPolicy.EXPLICIT,
                ack_wait=self.config.ack_wait_seconds,
                max_deliver=self.config.max_deliver,
                max_ack_pending=self.config.max_ack_pending,
                deliver_policy=DeliverPolicy.ALL,
            )

            # Subscribe with pull-based consumer
            self._subscription = await self.client.js.pull_subscribe(
                self.config.subject or ">",
                durable=self.config.name if self.config.durable else None,
                stream=self.config.stream,
                config=consumer_config,
            )

            self._running = True
            self._started_at = datetime.now(UTC)

            logger.info(
                "Consumer started",
                name=self.config.name,
                stream=self.config.stream,
                subject=self.config.subject,
            )

            # Start processing loop
            await self._process_loop()

        except Exception as e:
            logger.error(
                "Failed to start consumer",
                name=self.config.name,
                error=str(e),
            )
            raise

    async def stop(self) -> None:
        """Stop consuming messages."""
        self._running = False

        if self._subscription:
            await self._subscription.unsubscribe()
            self._subscription = None

        logger.info(
            "Consumer stopped",
            name=self.config.name,
            processed=self._processed_count,
            errors=self._error_count,
        )

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                # Fetch batch of messages
                messages = await self._subscription.fetch(
                    batch=self.config.batch_size,
                    timeout=self.config.poll_timeout_ms / 1000,
                )

                for msg in messages:
                    await self._handle_message(msg)

            except asyncio.TimeoutError:
                # No messages available, continue polling
                continue
            except Exception as e:
                logger.error(
                    "Error in consumer loop",
                    name=self.config.name,
                    error=str(e),
                )
                await asyncio.sleep(self.config.retry_delay_seconds)

    async def _handle_message(self, msg) -> None:
        """Handle a single message.

        Args:
            msg: NATS message
        """
        try:
            # Extract metadata
            metadata = {
                "subject": msg.subject,
                "reply": msg.reply,
                "headers": dict(msg.headers) if msg.headers else {},
                "stream": self.config.stream,
                "consumer": self.config.name,
                "num_delivered": msg.metadata.num_delivered if msg.metadata else 1,
                "timestamp": msg.metadata.timestamp if msg.metadata else None,
                "sequence": {
                    "stream": msg.metadata.sequence.stream if msg.metadata else None,
                    "consumer": msg.metadata.sequence.consumer if msg.metadata else None,
                },
            }

            # Process the message
            result = await self.process_message(msg.data, metadata)

            if result.success:
                # Acknowledge successful processing
                await msg.ack()
                self._processed_count += 1

                logger.debug(
                    "Message processed",
                    consumer=self.config.name,
                    message_id=result.message_id,
                )

            elif result.should_retry:
                # Negative acknowledge for retry
                if result.delay_seconds > 0:
                    await msg.nak(delay=result.delay_seconds)
                else:
                    await msg.nak()

                logger.warning(
                    "Message will retry",
                    consumer=self.config.name,
                    message_id=result.message_id,
                    error=result.error,
                )

            else:
                # Terminal failure - send to dead letter queue
                await self._send_to_dlq(msg, result.error)
                await msg.term()
                self._error_count += 1

                logger.error(
                    "Message failed permanently",
                    consumer=self.config.name,
                    message_id=result.message_id,
                    error=result.error,
                )

        except Exception as e:
            self._error_count += 1
            logger.error(
                "Error handling message",
                consumer=self.config.name,
                error=str(e),
            )

            # Negative acknowledge on unexpected error
            try:
                await msg.nak()
            except Exception:
                pass

    async def _send_to_dlq(self, msg, error: str | None) -> None:
        """Send failed message to dead letter queue.

        Args:
            msg: Original message
            error: Error message
        """
        try:
            dlq_subject = f"dlq.{self.config.stream}.{self.config.name}"

            headers = dict(msg.headers) if msg.headers else {}
            headers["X-Original-Subject"] = msg.subject
            headers["X-Error"] = error or "Unknown error"
            headers["X-Failed-At"] = datetime.now(UTC).isoformat()

            await self.client.js.publish(
                dlq_subject,
                msg.data,
                headers=headers,
            )

            logger.info(
                "Message sent to DLQ",
                subject=dlq_subject,
                original_subject=msg.subject,
            )

        except Exception as e:
            logger.error("Failed to send to DLQ", error=str(e))

    def get_stats(self) -> dict[str, Any]:
        """Get consumer statistics."""
        return {
            "name": self.config.name,
            "stream": self.config.stream,
            "running": self._running,
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "uptime_seconds": (
                (datetime.now(UTC) - self._started_at).total_seconds()
                if self._started_at
                else 0
            ),
        }


class FunctionConsumer(Consumer):
    """Consumer that wraps a processing function.

    Useful for simple consumers that don't need a full class.
    """

    def __init__(
        self,
        config: ConsumerConfig,
        handler: Callable[[bytes, dict[str, Any]], ProcessingResult],
        client: NATSClient | None = None,
    ):
        super().__init__(config, client)
        self._handler = handler

    async def process_message(self, data: bytes, metadata: dict[str, Any]) -> ProcessingResult:
        """Process message using the wrapped function."""
        if asyncio.iscoroutinefunction(self._handler):
            return await self._handler(data, metadata)
        else:
            return self._handler(data, metadata)
