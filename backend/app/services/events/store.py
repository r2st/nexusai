"""Event store for immutable raw event storage.

Uses S3-compatible storage for durability and replay capability.
Events are stored with tenant isolation and time-based partitioning.
"""

import json
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.events.models import (
    EventQuery,
    EventSource,
    EventStats,
    EventType,
    RawEvent,
)
from app.services.storage.manager import get_storage_manager

logger = structlog.get_logger()


class EventStore:
    """Immutable event store backed by S3 and PostgreSQL.

    Architecture:
    - Full event payloads stored in S3 (immutable, cheap, replayable)
    - Event metadata indexed in PostgreSQL (fast queries, RLS)

    Storage path format:
    s3://bucket/{tenant_id}/events/{source}/{year}/{month}/{day}/{event_id}.json
    """

    def __init__(self):
        self.storage = get_storage_manager()
        self._bucket_prefix = getattr(settings, "EVENT_STORE_PREFIX", "events")

    def _get_storage_path(self, event: RawEvent) -> str:
        """Generate S3 storage path for an event.

        Format: {tenant_id}/events/{source}/{YYYY}/{MM}/{DD}/{event_id}.json
        """
        dt = event.received_at
        return (
            f"{event.tenant_id}/"
            f"{self._bucket_prefix}/"
            f"{event.source.value}/"
            f"{dt.year:04d}/"
            f"{dt.month:02d}/"
            f"{dt.day:02d}/"
            f"{event.id}.json"
        )

    async def store(
        self,
        event: RawEvent,
        session: AsyncSession | None = None,
    ) -> str:
        """Store a raw event.

        1. Write full payload to S3
        2. Index metadata in PostgreSQL (if session provided)

        Args:
            event: The raw event to store
            session: Optional database session for indexing

        Returns:
            Storage path of the event
        """
        storage_path = self._get_storage_path(event)

        try:
            # Serialize event to JSON
            event_json = event.model_dump_json(indent=2)

            # Store in S3
            await self.storage.upload(
                key=storage_path,
                data=event_json.encode("utf-8"),
                content_type="application/json",
                metadata={
                    "tenant_id": event.tenant_id,
                    "source": event.source.value,
                    "event_type": event.event_type.value,
                    "source_event_type": event.source_event_type,
                    "received_at": event.received_at.isoformat(),
                },
            )

            # Index in PostgreSQL if session provided
            if session:
                await self._index_event(session, event, storage_path)

            logger.info(
                "Event stored",
                event_id=event.id,
                tenant_id=event.tenant_id,
                source=event.source.value,
                path=storage_path,
            )

            return storage_path

        except Exception as e:
            logger.error(
                "Failed to store event",
                event_id=event.id,
                error=str(e),
            )
            raise

    async def _index_event(
        self,
        session: AsyncSession,
        event: RawEvent,
        storage_path: str,
    ) -> None:
        """Index event metadata in PostgreSQL for fast queries."""
        # Use raw SQL to insert into events_index table
        # This allows RLS to apply automatically
        await session.execute(
            text("""
                INSERT INTO events_index (
                    id, tenant_id, source, source_event_type, event_type,
                    source_id, source_timestamp, connection_id,
                    received_at, storage_path, processed, schema_version
                ) VALUES (
                    :id, :tenant_id, :source, :source_event_type, :event_type,
                    :source_id, :source_timestamp, :connection_id,
                    :received_at, :storage_path, :processed, :schema_version
                )
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": event.id,
                "tenant_id": event.tenant_id,
                "source": event.source.value,
                "source_event_type": event.source_event_type,
                "event_type": event.event_type.value,
                "source_id": event.source_id,
                "source_timestamp": event.source_timestamp,
                "connection_id": event.connection_id,
                "received_at": event.received_at,
                "storage_path": storage_path,
                "processed": event.processed,
                "schema_version": event.schema_version,
            },
        )
        await session.flush()

    async def get(
        self,
        event_id: str,
        tenant_id: str,
    ) -> RawEvent | None:
        """Retrieve a raw event by ID.

        Args:
            event_id: Event ID
            tenant_id: Tenant ID (for path construction)

        Returns:
            The raw event or None if not found
        """
        # We need to find the event - check index first if available
        # For now, we'll need the storage path from the index

        # This is a simplified implementation
        # In production, query the index first to get the path
        logger.warning(
            "get() requires index lookup - implement with session",
            event_id=event_id,
        )
        return None

    async def get_by_path(self, storage_path: str) -> RawEvent | None:
        """Retrieve a raw event by its storage path.

        Args:
            storage_path: S3 path to the event

        Returns:
            The raw event or None if not found
        """
        try:
            data = await self.storage.download(storage_path)
            if data is None:
                return None

            event_dict = json.loads(data.decode("utf-8"))
            return RawEvent(**event_dict)

        except Exception as e:
            logger.error(
                "Failed to retrieve event",
                path=storage_path,
                error=str(e),
            )
            return None

    async def query(
        self,
        session: AsyncSession,
        query: EventQuery,
    ) -> list[dict[str, Any]]:
        """Query events from the index.

        Args:
            session: Database session
            query: Query parameters

        Returns:
            List of event metadata (not full payloads)
        """
        # Build dynamic query
        sql = """
            SELECT
                id, tenant_id, source, source_event_type, event_type,
                source_id, source_timestamp, connection_id,
                received_at, storage_path, processed
            FROM events_index
            WHERE tenant_id = :tenant_id
        """
        params: dict[str, Any] = {"tenant_id": query.tenant_id}

        if query.source:
            sql += " AND source = :source"
            params["source"] = query.source.value

        if query.event_type:
            sql += " AND event_type = :event_type"
            params["event_type"] = query.event_type.value

        if query.connection_id:
            sql += " AND connection_id = :connection_id"
            params["connection_id"] = query.connection_id

        if query.start_time:
            sql += " AND received_at >= :start_time"
            params["start_time"] = query.start_time

        if query.end_time:
            sql += " AND received_at <= :end_time"
            params["end_time"] = query.end_time

        if query.processed is not None:
            sql += " AND processed = :processed"
            params["processed"] = query.processed

        sql += " ORDER BY received_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = query.limit
        params["offset"] = query.offset

        result = await session.execute(text(sql), params)
        rows = result.fetchall()

        return [
            {
                "id": row.id,
                "tenant_id": row.tenant_id,
                "source": row.source,
                "source_event_type": row.source_event_type,
                "event_type": row.event_type,
                "source_id": row.source_id,
                "source_timestamp": row.source_timestamp.isoformat() if row.source_timestamp else None,
                "connection_id": row.connection_id,
                "received_at": row.received_at.isoformat() if row.received_at else None,
                "storage_path": row.storage_path,
                "processed": row.processed,
            }
            for row in rows
        ]

    async def get_stats(
        self,
        session: AsyncSession,
        tenant_id: str,
    ) -> EventStats:
        """Get statistics about stored events for a tenant.

        Args:
            session: Database session
            tenant_id: Tenant ID

        Returns:
            Event statistics
        """
        stats = EventStats(tenant_id=tenant_id)

        result = await session.execute(
            text("""
                SELECT
                    COUNT(*) as total,
                    MIN(received_at) as oldest,
                    MAX(received_at) as newest
                FROM events_index
                WHERE tenant_id = :tenant_id
            """),
            {"tenant_id": tenant_id},
        )
        row = result.fetchone()
        if row:
            stats.total_events = row.total or 0
            stats.oldest_event = row.oldest
            stats.newest_event = row.newest

        result = await session.execute(
            text("""
                SELECT source, event_type, COUNT(*) as count
                FROM events_index
                WHERE tenant_id = :tenant_id
                GROUP BY source, event_type
            """),
            {"tenant_id": tenant_id},
        )
        by_source: dict[str, int] = {}
        by_type: dict[str, int] = {}
        for row in result:
            by_source[row.source] = by_source.get(row.source, 0) + row.count
            by_type[row.event_type] = by_type.get(row.event_type, 0) + row.count
        stats.events_by_source = by_source
        stats.events_by_type = by_type

        return stats

    async def mark_processed(
        self,
        session: AsyncSession,
        event_id: str,
        error: str | None = None,
    ) -> None:
        """Mark an event as processed.

        Args:
            session: Database session
            event_id: Event ID
            error: Optional error message if processing failed
        """
        if error:
            await session.execute(
                text("""
                    UPDATE events_index
                    SET processed = false,
                        processing_error = :error,
                        updated_at = NOW()
                    WHERE id = :event_id
                """),
                {"event_id": event_id, "error": error},
            )
        else:
            await session.execute(
                text("""
                    UPDATE events_index
                    SET processed = true,
                        processed_at = NOW(),
                        updated_at = NOW()
                    WHERE id = :event_id
                """),
                {"event_id": event_id},
            )
        await session.flush()

    async def replay(
        self,
        session: AsyncSession,
        tenant_id: str,
        source: EventSource | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        batch_size: int = 100,
    ):
        """Replay events from the store.

        Yields events in chronological order for reprocessing.

        Args:
            session: Database session
            tenant_id: Tenant ID
            source: Optional source filter
            start_time: Optional start time
            end_time: Optional end time
            batch_size: Number of events per batch

        Yields:
            RawEvent objects
        """
        offset = 0

        while True:
            query = EventQuery(
                tenant_id=tenant_id,
                source=source,
                start_time=start_time,
                end_time=end_time,
                limit=batch_size,
                offset=offset,
            )

            events_meta = await self.query(session, query)

            if not events_meta:
                break

            for meta in events_meta:
                event = await self.get_by_path(meta["storage_path"])
                if event:
                    yield event

            offset += batch_size

            if len(events_meta) < batch_size:
                break


# Global store instance
_event_store: EventStore | None = None


def get_event_store() -> EventStore:
    """Get the global event store instance."""
    global _event_store
    if _event_store is None:
        _event_store = EventStore()
    return _event_store
