"""Configuration for message queue service."""


from pydantic import BaseModel, Field

from app.core.config import settings


class StreamConfig(BaseModel):
    """Configuration for a NATS JetStream stream."""

    name: str
    subjects: list[str]
    retention: str = "limits"  # limits, interest, workqueue
    storage: str = "file"  # file, memory
    max_age_seconds: int = 7 * 24 * 60 * 60  # 7 days
    max_msgs: int = 10_000_000
    max_bytes: int = 10 * 1024 * 1024 * 1024  # 10GB
    duplicate_window_seconds: int = 60
    replicas: int = 1


class ConsumerConfigModel(BaseModel):
    """Configuration for a NATS JetStream consumer."""

    name: str
    stream: str
    filter_subject: str | None = None
    durable: bool = True
    ack_wait_seconds: int = 30
    max_deliver: int = 3
    max_ack_pending: int = 1000
    deliver_policy: str = "all"  # all, last, new, by_start_sequence, by_start_time


class QueueConfig(BaseModel):
    """Configuration for the message queue service."""

    # NATS connection
    url: str = Field(default="nats://localhost:4222")
    name: str = Field(default="nexusai")
    reconnect_time_wait: int = Field(default=2)
    max_reconnect_attempts: int = Field(default=5)

    # Authentication
    user: str | None = None
    password: str | None = None
    token: str | None = None
    nkey_seed: str | None = None
    credentials_path: str | None = None

    # TLS
    tls_enabled: bool = False
    tls_cert_path: str | None = None
    tls_key_path: str | None = None
    tls_ca_path: str | None = None

    # Streams
    streams: list[StreamConfig] = Field(default_factory=list)

    # Default stream configurations
    events_stream: StreamConfig = Field(
        default_factory=lambda: StreamConfig(
            name="EVENTS",
            subjects=["events.>"],
            retention="limits",
            max_age_seconds=7 * 24 * 60 * 60,  # 7 days
        )
    )
    entities_stream: StreamConfig = Field(
        default_factory=lambda: StreamConfig(
            name="ENTITIES",
            subjects=["entities.>"],
            retention="limits",
            max_age_seconds=30 * 24 * 60 * 60,  # 30 days
        )
    )
    tasks_stream: StreamConfig = Field(
        default_factory=lambda: StreamConfig(
            name="TASKS",
            subjects=["tasks.>"],
            retention="workqueue",
            max_age_seconds=24 * 60 * 60,  # 1 day
        )
    )
    dlq_stream: StreamConfig = Field(
        default_factory=lambda: StreamConfig(
            name="DLQ",
            subjects=["dlq.>"],
            retention="limits",
            max_age_seconds=30 * 24 * 60 * 60,  # 30 days
        )
    )

    # Worker settings
    worker_concurrency: int = Field(default=10)
    worker_batch_size: int = Field(default=100)
    worker_poll_interval_ms: int = Field(default=100)

    # Health check
    health_check_interval_seconds: int = Field(default=30)

    @classmethod
    def from_settings(cls) -> "QueueConfig":
        """Create config from application settings."""
        return cls(
            url=getattr(settings, "NATS_URL", "nats://localhost:4222"),
            name=getattr(settings, "NATS_CLIENT_NAME", "nexusai"),
            user=getattr(settings, "NATS_USER", None),
            password=getattr(settings, "NATS_PASSWORD", None),
            token=getattr(settings, "NATS_TOKEN", None),
            tls_enabled=getattr(settings, "NATS_TLS_ENABLED", False),
            worker_concurrency=getattr(settings, "NATS_WORKER_CONCURRENCY", 10),
        )


# Global config instance
_queue_config: QueueConfig | None = None


def get_queue_config() -> QueueConfig:
    """Get the global queue configuration."""
    global _queue_config
    if _queue_config is None:
        _queue_config = QueueConfig.from_settings()
    return _queue_config
