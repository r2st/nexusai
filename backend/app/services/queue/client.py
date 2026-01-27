"""NATS JetStream client for message queue operations."""

import asyncio
from typing import Any

import structlog

from app.services.queue.config import QueueConfig, get_queue_config

logger = structlog.get_logger()


class NATSClient:
    """Async NATS client with JetStream support.

    Provides connection management, automatic reconnection,
    and graceful shutdown handling.
    """

    def __init__(self, config: QueueConfig | None = None):
        self.config = config or get_queue_config()
        self._nc = None  # NATS connection
        self._js = None  # JetStream context
        self._connected = False
        self._connecting = False
        self._reconnect_task: asyncio.Task | None = None

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected and self._nc is not None

    @property
    def nc(self):
        """Get the NATS connection."""
        if not self._nc:
            raise RuntimeError("NATS client not connected")
        return self._nc

    @property
    def js(self):
        """Get the JetStream context."""
        if not self._js:
            raise RuntimeError("NATS client not connected")
        return self._js

    async def connect(self) -> None:
        """Connect to NATS server."""
        if self._connected or self._connecting:
            return

        self._connecting = True

        try:
            import nats
            from nats.errors import NoServersError, ConnectionClosedError

            # Build connection options
            options: dict[str, Any] = {
                "servers": [self.config.url],
                "name": self.config.name,
                "reconnect_time_wait": self.config.reconnect_time_wait,
                "max_reconnect_attempts": self.config.max_reconnect_attempts,
                "error_cb": self._error_callback,
                "disconnected_cb": self._disconnected_callback,
                "reconnected_cb": self._reconnected_callback,
                "closed_cb": self._closed_callback,
            }

            # Add authentication
            if self.config.user and self.config.password:
                options["user"] = self.config.user
                options["password"] = self.config.password
            elif self.config.token:
                options["token"] = self.config.token
            elif self.config.nkey_seed:
                options["nkeys_seed"] = self.config.nkey_seed
            elif self.config.credentials_path:
                options["user_credentials"] = self.config.credentials_path

            # Add TLS
            if self.config.tls_enabled:
                import ssl
                ssl_ctx = ssl.create_default_context()
                if self.config.tls_ca_path:
                    ssl_ctx.load_verify_locations(self.config.tls_ca_path)
                if self.config.tls_cert_path and self.config.tls_key_path:
                    ssl_ctx.load_cert_chain(
                        self.config.tls_cert_path,
                        self.config.tls_key_path,
                    )
                options["tls"] = ssl_ctx

            # Connect
            self._nc = await nats.connect(**options)

            # Get JetStream context
            self._js = self._nc.jetstream()

            self._connected = True
            logger.info(
                "Connected to NATS",
                url=self.config.url,
                client_id=self._nc.client_id,
            )

        except ImportError:
            logger.error("nats-py package not installed")
            raise
        except Exception as e:
            logger.error("Failed to connect to NATS", error=str(e))
            raise
        finally:
            self._connecting = False

    async def disconnect(self) -> None:
        """Disconnect from NATS server."""
        if not self._nc:
            return

        try:
            # Drain pending messages
            await self._nc.drain()
            # Close connection
            await self._nc.close()

            self._connected = False
            self._nc = None
            self._js = None

            logger.info("Disconnected from NATS")

        except Exception as e:
            logger.error("Error disconnecting from NATS", error=str(e))

    async def _error_callback(self, error: Exception) -> None:
        """Handle NATS errors."""
        logger.error("NATS error", error=str(error))

    async def _disconnected_callback(self) -> None:
        """Handle disconnection."""
        self._connected = False
        logger.warning("Disconnected from NATS")

    async def _reconnected_callback(self) -> None:
        """Handle reconnection."""
        self._connected = True
        logger.info("Reconnected to NATS")

    async def _closed_callback(self) -> None:
        """Handle connection closed."""
        self._connected = False
        logger.info("NATS connection closed")

    async def publish(
        self,
        subject: str,
        payload: bytes,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Publish a message to a subject.

        Args:
            subject: Target subject
            payload: Message payload
            headers: Optional message headers
        """
        await self.nc.publish(subject, payload, headers=headers)

    async def publish_js(
        self,
        subject: str,
        payload: bytes,
        headers: dict[str, str] | None = None,
        msg_id: str | None = None,
    ) -> Any:
        """Publish a message to JetStream.

        Args:
            subject: Target subject
            payload: Message payload
            headers: Optional message headers
            msg_id: Optional message ID for deduplication

        Returns:
            PubAck from JetStream
        """
        pub_headers = headers or {}
        if msg_id:
            pub_headers["Nats-Msg-Id"] = msg_id

        ack = await self.js.publish(subject, payload, headers=pub_headers)
        return ack

    async def request(
        self,
        subject: str,
        payload: bytes,
        timeout: float = 5.0,
    ) -> Any:
        """Send a request and wait for response.

        Args:
            subject: Target subject
            payload: Request payload
            timeout: Timeout in seconds

        Returns:
            Response message
        """
        return await self.nc.request(subject, payload, timeout=timeout)

    async def subscribe(
        self,
        subject: str,
        callback,
        queue: str | None = None,
    ) -> Any:
        """Subscribe to a subject.

        Args:
            subject: Subject pattern to subscribe to
            callback: Message handler callback
            queue: Optional queue group name

        Returns:
            Subscription
        """
        return await self.nc.subscribe(subject, cb=callback, queue=queue)

    async def health_check(self) -> dict[str, Any]:
        """Check connection health.

        Returns:
            Health status dict
        """
        status = {
            "connected": self._connected,
            "url": self.config.url,
        }

        if self._nc and self._connected:
            status["client_id"] = self._nc.client_id
            status["connected_server"] = str(self._nc.connected_url)
            status["pending_data_size"] = self._nc.pending_data_size
            status["max_payload"] = self._nc.max_payload

        return status


# Global client instance
_nats_client: NATSClient | None = None


def get_nats_client() -> NATSClient:
    """Get the global NATS client instance."""
    global _nats_client
    if _nats_client is None:
        _nats_client = NATSClient()
    return _nats_client


async def init_nats_client() -> NATSClient:
    """Initialize and connect the NATS client."""
    client = get_nats_client()
    await client.connect()
    return client
