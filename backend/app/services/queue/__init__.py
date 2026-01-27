"""Message queue service for async event processing.

This module provides:
- NATS JetStream client for reliable messaging
- Stream and consumer management
- Background worker framework
- Dead letter queue handling
"""

from app.services.queue.config import QueueConfig, get_queue_config
from app.services.queue.client import NATSClient, get_nats_client
from app.services.queue.streams import StreamManager, get_stream_manager
from app.services.queue.consumer import Consumer, ConsumerConfig
from app.services.queue.worker import Worker, WorkerPool

__all__ = [
    # Config
    "QueueConfig",
    "get_queue_config",
    # Client
    "NATSClient",
    "get_nats_client",
    # Streams
    "StreamManager",
    "get_stream_manager",
    # Consumer
    "Consumer",
    "ConsumerConfig",
    # Worker
    "Worker",
    "WorkerPool",
]
