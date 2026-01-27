"""Worker framework for background message processing."""

import asyncio
import signal
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

from app.services.queue.client import NATSClient, get_nats_client
from app.services.queue.consumer import Consumer, ConsumerConfig, ProcessingResult
from app.services.queue.streams import StreamManager, get_stream_manager

logger = structlog.get_logger()


class Worker(ABC):
    """Abstract base worker class.

    Workers are long-running processes that consume and process
    messages from one or more streams.
    """

    def __init__(
        self,
        name: str,
        client: NATSClient | None = None,
    ):
        self.name = name
        self.client = client or get_nats_client()
        self._running = False
        self._consumers: list[Consumer] = []
        self._tasks: list[asyncio.Task] = []
        self._started_at: datetime | None = None

    @abstractmethod
    async def setup(self) -> None:
        """Set up the worker.

        Subclasses should create consumers here.
        """
        pass

    async def start(self) -> None:
        """Start the worker and all consumers."""
        if self._running:
            logger.warning("Worker already running", worker=self.name)
            return

        try:
            # Ensure NATS connection
            if not self.client.is_connected:
                await self.client.connect()

            # Run setup
            await self.setup()

            self._running = True
            self._started_at = datetime.now(UTC)

            # Start all consumers
            for consumer in self._consumers:
                task = asyncio.create_task(consumer.start())
                self._tasks.append(task)

            logger.info(
                "Worker started",
                worker=self.name,
                consumers=len(self._consumers),
            )

        except Exception as e:
            logger.error("Failed to start worker", worker=self.name, error=str(e))
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the worker and all consumers."""
        self._running = False

        # Stop all consumers
        for consumer in self._consumers:
            await consumer.stop()

        # Cancel tasks
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks.clear()

        logger.info(
            "Worker stopped",
            worker=self.name,
        )

    def add_consumer(self, consumer: Consumer) -> None:
        """Add a consumer to the worker.

        Args:
            consumer: Consumer instance
        """
        self._consumers.append(consumer)

    def get_stats(self) -> dict[str, Any]:
        """Get worker statistics."""
        return {
            "name": self.name,
            "running": self._running,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "uptime_seconds": (
                (datetime.now(UTC) - self._started_at).total_seconds()
                if self._started_at
                else 0
            ),
            "consumers": [c.get_stats() for c in self._consumers],
        }


class WorkerPool:
    """Pool of workers for parallel processing.

    Manages multiple workers with graceful shutdown handling.
    """

    def __init__(
        self,
        workers: list[Worker] | None = None,
        client: NATSClient | None = None,
    ):
        self.workers = workers or []
        self.client = client or get_nats_client()
        self._running = False
        self._shutdown_event = asyncio.Event()

    def add_worker(self, worker: Worker) -> None:
        """Add a worker to the pool."""
        self.workers.append(worker)

    async def start(self) -> None:
        """Start all workers."""
        if self._running:
            return

        # Set up signal handlers
        self._setup_signals()

        # Connect to NATS
        if not self.client.is_connected:
            await self.client.connect()

        # Start all workers
        self._running = True
        for worker in self.workers:
            await worker.start()

        logger.info(
            "Worker pool started",
            workers=len(self.workers),
        )

    async def stop(self) -> None:
        """Stop all workers."""
        self._running = False

        # Stop all workers
        for worker in self.workers:
            await worker.stop()

        # Disconnect from NATS
        await self.client.disconnect()

        logger.info("Worker pool stopped")

    async def run_forever(self) -> None:
        """Run the worker pool until shutdown signal."""
        await self.start()

        # Wait for shutdown signal
        await self._shutdown_event.wait()

        await self.stop()

    def _setup_signals(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self._handle_signal(sig)),
            )

    async def _handle_signal(self, sig: signal.Signals) -> None:
        """Handle shutdown signal."""
        logger.info("Received shutdown signal", signal=sig.name)
        self._shutdown_event.set()

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        return {
            "running": self._running,
            "worker_count": len(self.workers),
            "workers": [w.get_stats() for w in self.workers],
        }


# Example worker implementations

class EventProcessorWorker(Worker):
    """Worker for processing raw events."""

    def __init__(self, client: NATSClient | None = None):
        super().__init__("event-processor", client)

    async def setup(self) -> None:
        """Set up event processing consumers."""
        from app.services.queue.consumer import FunctionConsumer

        # Consumer for all events
        config = ConsumerConfig(
            name="event-processor-all",
            stream="EVENTS",
            subject="events.>",
            batch_size=50,
        )

        async def process_event(data: bytes, metadata: dict[str, Any]) -> ProcessingResult:
            """Process a raw event."""
            import json

            try:
                event_data = json.loads(data.decode())
                event_id = event_data.get("event_id", "unknown")

                # Process the event (entity extraction, metrics, etc.)
                logger.debug(
                    "Processing event",
                    event_id=event_id,
                    source=event_data.get("source"),
                    event_type=event_data.get("event_type"),
                )

                # TODO: Implement actual processing
                # - Extract entities
                # - Update metrics
                # - Trigger downstream processing

                return ProcessingResult(
                    success=True,
                    message_id=event_id,
                )

            except Exception as e:
                return ProcessingResult(
                    success=False,
                    message_id="unknown",
                    error=str(e),
                    should_retry=True,
                    delay_seconds=5,
                )

        consumer = FunctionConsumer(config, process_event, self.client)
        self.add_consumer(consumer)


class EntityProcessorWorker(Worker):
    """Worker for processing entity changes."""

    def __init__(self, client: NATSClient | None = None):
        super().__init__("entity-processor", client)

    async def setup(self) -> None:
        """Set up entity processing consumers."""
        from app.services.queue.consumer import FunctionConsumer

        config = ConsumerConfig(
            name="entity-processor-all",
            stream="ENTITIES",
            subject="entities.>",
            batch_size=50,
        )

        async def process_entity(data: bytes, metadata: dict[str, Any]) -> ProcessingResult:
            """Process an entity change."""
            import json

            try:
                entity_data = json.loads(data.decode())
                entity_id = entity_data.get("id", "unknown")

                logger.debug(
                    "Processing entity",
                    entity_id=entity_id,
                    entity_type=entity_data.get("type"),
                )

                # TODO: Implement actual processing
                # - Update knowledge graph
                # - Update search index
                # - Trigger notifications

                return ProcessingResult(
                    success=True,
                    message_id=entity_id,
                )

            except Exception as e:
                return ProcessingResult(
                    success=False,
                    message_id="unknown",
                    error=str(e),
                    should_retry=True,
                    delay_seconds=5,
                )

        consumer = FunctionConsumer(config, process_entity, self.client)
        self.add_consumer(consumer)


async def run_workers():
    """Run the default worker pool."""
    pool = WorkerPool()

    # Add workers
    pool.add_worker(EventProcessorWorker())
    pool.add_worker(EntityProcessorWorker())

    # Run until shutdown
    await pool.run_forever()


if __name__ == "__main__":
    asyncio.run(run_workers())
