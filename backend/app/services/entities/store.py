"""Entity store for canonical domain entities.

PostgreSQL-backed store with tenant isolation via RLS.
"""

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.entities.models import (
    Entity,
    EntityQuery,
    EntityRelation,
    EntityType,
    RelationType,
)

logger = structlog.get_logger()


class EntityStore:
    """Store for canonical domain entities.

    Provides CRUD operations with tenant isolation and
    relationship management.
    """

    async def create(
        self,
        session: AsyncSession,
        entity: Entity,
    ) -> Entity:
        """Create a new entity.

        Args:
            session: Database session
            entity: Entity to create

        Returns:
            Created entity with generated ID
        """
        # Generate domain ID if not set
        if not entity.domain_id:
            entity.domain_id = entity.generate_domain_id()

        await session.execute(
            text("""
                INSERT INTO entities (
                    id, tenant_id, entity_type, source, source_id, connection_id,
                    domain_id, source_created_at, source_updated_at,
                    created_at, updated_at, raw_event_ids, metadata, tags, data
                ) VALUES (
                    :id, :tenant_id, :entity_type, :source, :source_id, :connection_id,
                    :domain_id, :source_created_at, :source_updated_at,
                    :created_at, :updated_at, :raw_event_ids, :metadata, :tags, :data
                )
                ON CONFLICT (tenant_id, domain_id) DO UPDATE SET
                    source_updated_at = EXCLUDED.source_updated_at,
                    updated_at = EXCLUDED.updated_at,
                    raw_event_ids = entities.raw_event_ids || EXCLUDED.raw_event_ids,
                    metadata = entities.metadata || EXCLUDED.metadata,
                    data = entities.data || EXCLUDED.data
            """),
            {
                "id": entity.id,
                "tenant_id": entity.tenant_id,
                "entity_type": entity.entity_type.value,
                "source": entity.source,
                "source_id": entity.source_id,
                "connection_id": entity.connection_id,
                "domain_id": entity.domain_id,
                "source_created_at": entity.source_created_at,
                "source_updated_at": entity.source_updated_at,
                "created_at": entity.created_at,
                "updated_at": entity.updated_at,
                "raw_event_ids": entity.raw_event_ids,
                "metadata": entity.metadata,
                "tags": entity.tags,
                "data": entity.model_dump(exclude={
                    "id", "tenant_id", "entity_type", "source", "source_id",
                    "connection_id", "domain_id", "source_created_at",
                    "source_updated_at", "created_at", "updated_at",
                    "raw_event_ids", "metadata", "tags",
                }),
            },
        )
        await session.flush()

        logger.debug(
            "Entity created",
            entity_id=entity.id,
            entity_type=entity.entity_type.value,
            domain_id=entity.domain_id,
        )

        return entity

    async def get(
        self,
        session: AsyncSession,
        entity_id: str,
    ) -> dict[str, Any] | None:
        """Get an entity by ID.

        Args:
            session: Database session
            entity_id: Entity ID

        Returns:
            Entity data or None
        """
        result = await session.execute(
            text("""
                SELECT * FROM entities WHERE id = :id
            """),
            {"id": entity_id},
        )
        row = result.fetchone()

        if not row:
            return None

        return self._row_to_dict(row)

    async def get_by_domain_id(
        self,
        session: AsyncSession,
        domain_id: str,
    ) -> dict[str, Any] | None:
        """Get an entity by domain ID.

        Args:
            session: Database session
            domain_id: 5-segment domain ID

        Returns:
            Entity data or None
        """
        result = await session.execute(
            text("""
                SELECT * FROM entities WHERE domain_id = :domain_id
            """),
            {"domain_id": domain_id},
        )
        row = result.fetchone()

        if not row:
            return None

        return self._row_to_dict(row)

    async def get_by_source(
        self,
        session: AsyncSession,
        tenant_id: str,
        source: str,
        source_id: str,
        entity_type: EntityType | None = None,
    ) -> dict[str, Any] | None:
        """Get an entity by source identifier.

        Args:
            session: Database session
            tenant_id: Tenant ID
            source: Source system
            source_id: ID in source system
            entity_type: Optional entity type filter

        Returns:
            Entity data or None
        """
        sql = """
            SELECT * FROM entities
            WHERE tenant_id = :tenant_id
            AND source = :source
            AND source_id = :source_id
        """
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "source": source,
            "source_id": source_id,
        }

        if entity_type:
            sql += " AND entity_type = :entity_type"
            params["entity_type"] = entity_type.value

        result = await session.execute(text(sql), params)
        row = result.fetchone()

        if not row:
            return None

        return self._row_to_dict(row)

    async def query(
        self,
        session: AsyncSession,
        query: EntityQuery,
    ) -> list[dict[str, Any]]:
        """Query entities.

        Args:
            session: Database session
            query: Query parameters

        Returns:
            List of matching entities
        """
        sql = "SELECT * FROM entities WHERE tenant_id = :tenant_id"
        params: dict[str, Any] = {"tenant_id": query.tenant_id}

        if query.entity_type:
            sql += " AND entity_type = :entity_type"
            params["entity_type"] = query.entity_type.value

        if query.source:
            sql += " AND source = :source"
            params["source"] = query.source

        if query.source_id:
            sql += " AND source_id = :source_id"
            params["source_id"] = query.source_id

        if query.domain_id:
            sql += " AND domain_id = :domain_id"
            params["domain_id"] = query.domain_id

        if query.ids:
            sql += " AND id = ANY(:ids)"
            params["ids"] = query.ids

        if query.tags:
            sql += " AND tags && :tags"
            params["tags"] = query.tags

        if query.created_after:
            sql += " AND created_at >= :created_after"
            params["created_after"] = query.created_after

        if query.created_before:
            sql += " AND created_at <= :created_before"
            params["created_before"] = query.created_before

        if query.updated_after:
            sql += " AND updated_at >= :updated_after"
            params["updated_after"] = query.updated_after

        # Sorting
        valid_sort_fields = ["created_at", "updated_at", "entity_type", "source"]
        sort_field = query.sort_by if query.sort_by in valid_sort_fields else "updated_at"
        sort_order = "DESC" if query.sort_order.lower() == "desc" else "ASC"
        sql += f" ORDER BY {sort_field} {sort_order}"

        # Pagination
        sql += " LIMIT :limit OFFSET :offset"
        params["limit"] = query.limit
        params["offset"] = query.offset

        result = await session.execute(text(sql), params)
        rows = result.fetchall()

        return [self._row_to_dict(row) for row in rows]

    async def update(
        self,
        session: AsyncSession,
        entity_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update an entity.

        Args:
            session: Database session
            entity_id: Entity ID
            updates: Fields to update

        Returns:
            Updated entity or None
        """
        # Build SET clause
        set_clauses = []
        params: dict[str, Any] = {"id": entity_id}

        for key, value in updates.items():
            if key not in ["id", "tenant_id", "created_at"]:
                set_clauses.append(f"{key} = :{key}")
                params[key] = value

        if not set_clauses:
            return await self.get(session, entity_id)

        set_clauses.append("updated_at = :updated_at")
        params["updated_at"] = datetime.now(UTC)

        sql = f"""
            UPDATE entities
            SET {", ".join(set_clauses)}
            WHERE id = :id
            RETURNING *
        """

        result = await session.execute(text(sql), params)
        row = result.fetchone()
        await session.flush()

        if not row:
            return None

        return self._row_to_dict(row)

    async def delete(
        self,
        session: AsyncSession,
        entity_id: str,
    ) -> bool:
        """Delete an entity.

        Args:
            session: Database session
            entity_id: Entity ID

        Returns:
            True if deleted
        """
        result = await session.execute(
            text("DELETE FROM entities WHERE id = :id"),
            {"id": entity_id},
        )
        await session.flush()

        return result.rowcount > 0

    # Relationship methods

    async def create_relation(
        self,
        session: AsyncSession,
        relation: EntityRelation,
    ) -> EntityRelation:
        """Create a relationship between entities.

        Args:
            session: Database session
            relation: Relationship to create

        Returns:
            Created relationship
        """
        await session.execute(
            text("""
                INSERT INTO entity_relations (
                    id, tenant_id, from_entity_id, from_entity_type,
                    to_entity_id, to_entity_type, relation_type,
                    properties, created_at, valid_from, valid_to
                ) VALUES (
                    :id, :tenant_id, :from_entity_id, :from_entity_type,
                    :to_entity_id, :to_entity_type, :relation_type,
                    :properties, :created_at, :valid_from, :valid_to
                )
                ON CONFLICT (tenant_id, from_entity_id, to_entity_id, relation_type)
                DO UPDATE SET
                    properties = EXCLUDED.properties,
                    valid_to = EXCLUDED.valid_to
            """),
            {
                "id": relation.id,
                "tenant_id": relation.tenant_id,
                "from_entity_id": relation.from_entity_id,
                "from_entity_type": relation.from_entity_type.value,
                "to_entity_id": relation.to_entity_id,
                "to_entity_type": relation.to_entity_type.value,
                "relation_type": relation.relation_type.value,
                "properties": relation.properties,
                "created_at": relation.created_at,
                "valid_from": relation.valid_from,
                "valid_to": relation.valid_to,
            },
        )
        await session.flush()

        return relation

    async def get_relations(
        self,
        session: AsyncSession,
        entity_id: str,
        relation_type: RelationType | None = None,
        direction: str = "both",
    ) -> list[dict[str, Any]]:
        """Get relationships for an entity.

        Args:
            session: Database session
            entity_id: Entity ID
            relation_type: Optional relation type filter
            direction: "from", "to", or "both"

        Returns:
            List of relationships
        """
        conditions = []
        params: dict[str, Any] = {}

        if direction in ("from", "both"):
            conditions.append("from_entity_id = :entity_id")

        if direction in ("to", "both"):
            if conditions:
                conditions = [f"({conditions[0]} OR to_entity_id = :entity_id)"]
            else:
                conditions.append("to_entity_id = :entity_id")

        params["entity_id"] = entity_id

        sql = f"SELECT * FROM entity_relations WHERE {' AND '.join(conditions)}"

        if relation_type:
            sql += " AND relation_type = :relation_type"
            params["relation_type"] = relation_type.value

        result = await session.execute(text(sql), params)
        rows = result.fetchall()

        return [
            {
                "id": row.id,
                "tenant_id": row.tenant_id,
                "from_entity_id": row.from_entity_id,
                "from_entity_type": row.from_entity_type,
                "to_entity_id": row.to_entity_id,
                "to_entity_type": row.to_entity_type,
                "relation_type": row.relation_type,
                "properties": row.properties,
                "created_at": row.created_at,
            }
            for row in rows
        ]

    async def get_related_entities(
        self,
        session: AsyncSession,
        entity_id: str,
        relation_type: RelationType | None = None,
        target_type: EntityType | None = None,
    ) -> list[dict[str, Any]]:
        """Get entities related to a given entity.

        Args:
            session: Database session
            entity_id: Source entity ID
            relation_type: Optional relation type filter
            target_type: Optional target entity type filter

        Returns:
            List of related entities
        """
        sql = """
            SELECT e.* FROM entities e
            JOIN entity_relations r ON (
                (r.from_entity_id = :entity_id AND r.to_entity_id = e.id)
                OR (r.to_entity_id = :entity_id AND r.from_entity_id = e.id)
            )
            WHERE e.id != :entity_id
        """
        params: dict[str, Any] = {"entity_id": entity_id}

        if relation_type:
            sql += " AND r.relation_type = :relation_type"
            params["relation_type"] = relation_type.value

        if target_type:
            sql += " AND e.entity_type = :target_type"
            params["target_type"] = target_type.value

        result = await session.execute(text(sql), params)
        rows = result.fetchall()

        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row) -> dict[str, Any]:
        """Convert a database row to a dictionary."""
        data = row.data if hasattr(row, "data") and row.data else {}

        return {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "entity_type": row.entity_type,
            "source": row.source,
            "source_id": row.source_id,
            "connection_id": row.connection_id,
            "domain_id": row.domain_id,
            "source_created_at": row.source_created_at,
            "source_updated_at": row.source_updated_at,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "raw_event_ids": row.raw_event_ids or [],
            "metadata": row.metadata or {},
            "tags": row.tags or [],
            **data,
        }


# Global store instance
_entity_store: EntityStore | None = None


def get_entity_store() -> EntityStore:
    """Get the global entity store instance."""
    global _entity_store
    if _entity_store is None:
        _entity_store = EntityStore()
    return _entity_store
