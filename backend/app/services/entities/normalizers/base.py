"""Base normalizer interface for entity transformation."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.services.entities.models import Entity, EntityType


class BaseNormalizer(ABC):
    """Base class for source-specific normalizers.

    Normalizers transform raw event payloads from a source system
    into canonical domain entities.
    """

    @property
    @abstractmethod
    def source(self) -> str:
        """Return the source identifier (e.g., 'github', 'gitlab')."""
        pass

    @abstractmethod
    def normalize(
        self,
        event_type: str,
        payload: dict[str, Any],
        tenant_id: str,
        connection_id: str | None = None,
    ) -> list[Entity]:
        """Normalize a raw event payload into entities.

        Args:
            event_type: The type of event (e.g., 'push', 'pull_request')
            payload: The raw event payload
            tenant_id: Tenant ID for the entities
            connection_id: Optional connection ID

        Returns:
            List of normalized entities
        """
        pass

    def parse_timestamp(self, value: Any) -> datetime | None:
        """Parse a timestamp from various formats.

        Args:
            value: Timestamp value (string, int, or datetime)

        Returns:
            Parsed datetime or None
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, int):
            # Unix timestamp (seconds or milliseconds)
            if value > 1e11:
                value = value / 1000
            from datetime import UTC
            return datetime.fromtimestamp(value, tz=UTC)

        if isinstance(value, str):
            # ISO format
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass

            # Try common formats
            formats = [
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue

        return None

    def extract_entity_type(self, event_type: str) -> EntityType | None:
        """Map event type to entity type.

        Override in subclasses for source-specific mappings.

        Args:
            event_type: Source event type

        Returns:
            EntityType or None if not mappable
        """
        return None
