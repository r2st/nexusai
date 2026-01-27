"""Stream management for NATS JetStream."""

from typing import Any

import structlog

from app.services.queue.config import QueueConfig, StreamConfig, get_queue_config
from app.services.queue.client import NATSClient, get_nats_client

logger = structlog.get_logger()


class StreamManager:
    """Manager for NATS JetStream streams.

    Handles stream creation, configuration, and monitoring.
    """

    def __init__(
        self,
        client: NATSClient | None = None,
        config: QueueConfig | None = None,
    ):
        self.client = client or get_nats_client()
        self.config = config or get_queue_config()

    async def setup_streams(self) -> None:
        """Set up all configured streams.

        Creates streams if they don't exist, updates if config changed.
        """
        # Default streams
        default_streams = [
            self.config.events_stream,
            self.config.entities_stream,
            self.config.tasks_stream,
            self.config.dlq_stream,
        ]

        # Additional configured streams
        all_streams = default_streams + self.config.streams

        for stream_config in all_streams:
            await self.create_or_update_stream(stream_config)

    async def create_or_update_stream(self, config: StreamConfig) -> dict[str, Any]:
        """Create or update a stream.

        Args:
            config: Stream configuration

        Returns:
            Stream info dict
        """
        try:
            from nats.js.api import (
                StreamConfig as NATSStreamConfig,
                RetentionPolicy,
                StorageType,
            )

            # Map retention policy
            retention_map = {
                "limits": RetentionPolicy.LIMITS,
                "interest": RetentionPolicy.INTEREST,
                "workqueue": RetentionPolicy.WORK_QUEUE,
            }
            retention = retention_map.get(config.retention, RetentionPolicy.LIMITS)

            # Map storage type
            storage_map = {
                "file": StorageType.FILE,
                "memory": StorageType.MEMORY,
            }
            storage = storage_map.get(config.storage, StorageType.FILE)

            nats_config = NATSStreamConfig(
                name=config.name,
                subjects=config.subjects,
                retention=retention,
                storage=storage,
                max_age=config.max_age_seconds,
                max_msgs=config.max_msgs,
                max_bytes=config.max_bytes,
                duplicate_window=config.duplicate_window_seconds,
                num_replicas=config.replicas,
            )

            # Try to get existing stream
            try:
                stream_info = await self.client.js.stream_info(config.name)
                # Stream exists - update if needed
                await self.client.js.update_stream(config=nats_config)
                logger.info("Updated stream", stream=config.name)
            except Exception:
                # Stream doesn't exist - create it
                stream_info = await self.client.js.add_stream(config=nats_config)
                logger.info("Created stream", stream=config.name)

            return {
                "name": stream_info.config.name,
                "subjects": stream_info.config.subjects,
                "messages": stream_info.state.messages,
                "bytes": stream_info.state.bytes,
            }

        except ImportError:
            logger.error("nats-py not installed")
            return {"error": "nats-py not installed"}
        except Exception as e:
            logger.error("Failed to setup stream", stream=config.name, error=str(e))
            raise

    async def delete_stream(self, name: str) -> bool:
        """Delete a stream.

        Args:
            name: Stream name

        Returns:
            True if deleted successfully
        """
        try:
            await self.client.js.delete_stream(name)
            logger.info("Deleted stream", stream=name)
            return True
        except Exception as e:
            logger.error("Failed to delete stream", stream=name, error=str(e))
            return False

    async def get_stream_info(self, name: str) -> dict[str, Any]:
        """Get stream information.

        Args:
            name: Stream name

        Returns:
            Stream info dict
        """
        try:
            info = await self.client.js.stream_info(name)
            return {
                "name": info.config.name,
                "subjects": info.config.subjects,
                "retention": info.config.retention.name,
                "storage": info.config.storage.name,
                "state": {
                    "messages": info.state.messages,
                    "bytes": info.state.bytes,
                    "first_seq": info.state.first_seq,
                    "last_seq": info.state.last_seq,
                    "consumer_count": info.state.consumer_count,
                    "first_ts": info.state.first_ts,
                    "last_ts": info.state.last_ts,
                },
            }
        except Exception as e:
            logger.error("Failed to get stream info", stream=name, error=str(e))
            return {"error": str(e)}

    async def list_streams(self) -> list[dict[str, Any]]:
        """List all streams.

        Returns:
            List of stream info dicts
        """
        streams = []
        try:
            async for stream in self.client.js.streams_info():
                streams.append({
                    "name": stream.config.name,
                    "subjects": stream.config.subjects,
                    "messages": stream.state.messages,
                    "bytes": stream.state.bytes,
                })
        except Exception as e:
            logger.error("Failed to list streams", error=str(e))

        return streams

    async def purge_stream(self, name: str, filter_subject: str | None = None) -> int:
        """Purge messages from a stream.

        Args:
            name: Stream name
            filter_subject: Optional subject filter

        Returns:
            Number of messages purged
        """
        try:
            if filter_subject:
                result = await self.client.js.purge_stream(
                    name, subject=filter_subject
                )
            else:
                result = await self.client.js.purge_stream(name)

            logger.info(
                "Purged stream",
                stream=name,
                purged=result.purged,
            )
            return result.purged

        except Exception as e:
            logger.error("Failed to purge stream", stream=name, error=str(e))
            return 0

    async def get_message(
        self,
        stream: str,
        seq: int,
    ) -> dict[str, Any] | None:
        """Get a specific message by sequence number.

        Args:
            stream: Stream name
            seq: Sequence number

        Returns:
            Message dict or None
        """
        try:
            msg = await self.client.js.get_msg(stream, seq)
            return {
                "subject": msg.subject,
                "data": msg.data.decode() if msg.data else None,
                "seq": msg.seq,
                "time": msg.time,
                "headers": dict(msg.headers) if msg.headers else {},
            }
        except Exception as e:
            logger.error(
                "Failed to get message",
                stream=stream,
                seq=seq,
                error=str(e),
            )
            return None

    async def create_consumer(
        self,
        stream: str,
        name: str,
        filter_subject: str | None = None,
        durable: bool = True,
        ack_wait: int = 30,
        max_deliver: int = 3,
        max_ack_pending: int = 1000,
    ) -> dict[str, Any]:
        """Create a consumer for a stream.

        Args:
            stream: Stream name
            name: Consumer name
            filter_subject: Optional subject filter
            durable: Whether consumer is durable
            ack_wait: Ack wait time in seconds
            max_deliver: Maximum delivery attempts
            max_ack_pending: Maximum pending acknowledgements

        Returns:
            Consumer info dict
        """
        try:
            from nats.js.api import ConsumerConfig, AckPolicy, DeliverPolicy

            config = ConsumerConfig(
                name=name,
                durable_name=name if durable else None,
                filter_subject=filter_subject,
                ack_policy=AckPolicy.EXPLICIT,
                ack_wait=ack_wait,
                max_deliver=max_deliver,
                max_ack_pending=max_ack_pending,
                deliver_policy=DeliverPolicy.ALL,
            )

            consumer = await self.client.js.add_consumer(stream, config)

            logger.info(
                "Created consumer",
                stream=stream,
                consumer=name,
            )

            return {
                "name": consumer.name,
                "stream": stream,
                "num_pending": consumer.num_pending,
                "num_waiting": consumer.num_waiting,
            }

        except Exception as e:
            logger.error(
                "Failed to create consumer",
                stream=stream,
                consumer=name,
                error=str(e),
            )
            raise

    async def delete_consumer(self, stream: str, name: str) -> bool:
        """Delete a consumer.

        Args:
            stream: Stream name
            name: Consumer name

        Returns:
            True if deleted successfully
        """
        try:
            await self.client.js.delete_consumer(stream, name)
            logger.info("Deleted consumer", stream=stream, consumer=name)
            return True
        except Exception as e:
            logger.error(
                "Failed to delete consumer",
                stream=stream,
                consumer=name,
                error=str(e),
            )
            return False


# Global stream manager instance
_stream_manager: StreamManager | None = None


def get_stream_manager() -> StreamManager:
    """Get the global stream manager instance."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = StreamManager()
    return _stream_manager


async def init_streams() -> StreamManager:
    """Initialize streams from configuration."""
    manager = get_stream_manager()
    await manager.setup_streams()
    return manager
