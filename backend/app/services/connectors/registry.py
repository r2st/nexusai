"""Connector registry for managing multiple connectors."""

from datetime import UTC, datetime
from typing import Any, Type

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorStatus,
)

logger = structlog.get_logger()


class ConnectorRegistry:
    """Registry for managing connector instances.

    Handles:
    - Connector registration and discovery
    - Instance lifecycle management
    - Configuration persistence
    - Scheduled sync coordination
    """

    def __init__(self):
        # Registered connector classes by source type
        self._connector_classes: dict[str, Type[BaseConnector]] = {}

        # Active connector instances by ID
        self._instances: dict[str, BaseConnector] = {}

    def register_connector_class(
        self,
        source: str,
        connector_class: Type[BaseConnector],
    ) -> None:
        """Register a connector class for a source type.

        Args:
            source: Source type identifier (github, gitlab, etc)
            connector_class: Connector class to register
        """
        self._connector_classes[source] = connector_class
        logger.info("Registered connector class", source=source)

    def get_connector_class(self, source: str) -> Type[BaseConnector] | None:
        """Get connector class for a source type."""
        return self._connector_classes.get(source)

    def list_supported_sources(self) -> list[str]:
        """List all supported source types."""
        return list(self._connector_classes.keys())

    async def create_connector(
        self,
        session: AsyncSession,
        config: ConnectorConfig,
    ) -> BaseConnector:
        """Create a new connector instance.

        Args:
            session: Database session
            config: Connector configuration

        Returns:
            Connector instance
        """
        connector_class = self._connector_classes.get(config.source)
        if not connector_class:
            raise ValueError(f"Unknown source type: {config.source}")

        # Save config to database
        await self._save_config(session, config)

        # Create instance
        connector = connector_class(config)
        self._instances[config.id] = connector

        logger.info(
            "Created connector",
            connector_id=config.id,
            source=config.source,
        )

        return connector

    async def get_connector(
        self,
        session: AsyncSession,
        connector_id: str,
    ) -> BaseConnector | None:
        """Get a connector by ID.

        Args:
            session: Database session
            connector_id: Connector ID

        Returns:
            Connector instance or None
        """
        # Check cache first
        if connector_id in self._instances:
            return self._instances[connector_id]

        # Load from database
        config = await self._load_config(session, connector_id)
        if not config:
            return None

        # Create instance
        connector_class = self._connector_classes.get(config.source)
        if not connector_class:
            logger.error("Unknown source type", source=config.source)
            return None

        connector = connector_class(config)
        self._instances[connector_id] = connector

        return connector

    async def list_connectors(
        self,
        session: AsyncSession,
        tenant_id: str,
        source: str | None = None,
        status: ConnectorStatus | None = None,
    ) -> list[dict[str, Any]]:
        """List connectors for a tenant.

        Args:
            session: Database session
            tenant_id: Tenant ID
            source: Optional source filter
            status: Optional status filter

        Returns:
            List of connector info dicts
        """
        sql = """
            SELECT * FROM connections
            WHERE tenant_id = :tenant_id
            AND is_active = true
        """
        params: dict[str, Any] = {"tenant_id": tenant_id}

        if source:
            sql += " AND source = :source"
            params["source"] = source

        if status:
            sql += " AND sync_status = :status"
            params["status"] = status.value

        result = await session.execute(text(sql), params)
        rows = result.fetchall()

        return [
            {
                "id": row.id,
                "tenant_id": row.tenant_id,
                "source": row.source,
                "name": row.name,
                "endpoint": row.endpoint,
                "status": row.sync_status,
                "last_sync_at": row.last_sync_at,
                "created_at": row.created_at,
            }
            for row in rows
        ]

    async def delete_connector(
        self,
        session: AsyncSession,
        connector_id: str,
    ) -> bool:
        """Delete a connector.

        Args:
            session: Database session
            connector_id: Connector ID

        Returns:
            True if deleted
        """
        # Disconnect if active
        if connector_id in self._instances:
            connector = self._instances[connector_id]
            await connector.disconnect()
            del self._instances[connector_id]

        # Soft delete in database
        result = await session.execute(
            text("""
                UPDATE connections
                SET is_active = false, updated_at = :updated_at
                WHERE id = :id
            """),
            {"id": connector_id, "updated_at": datetime.now(UTC)},
        )
        await session.flush()

        return result.rowcount > 0

    async def update_connector(
        self,
        session: AsyncSession,
        connector_id: str,
        updates: dict[str, Any],
    ) -> bool:
        """Update connector configuration.

        Args:
            session: Database session
            connector_id: Connector ID
            updates: Fields to update

        Returns:
            True if updated
        """
        # Build update query
        set_clauses = []
        params: dict[str, Any] = {
            "id": connector_id,
            "updated_at": datetime.now(UTC),
        }

        allowed_fields = [
            "name", "endpoint", "webhook_secret", "config",
            "sync_status", "sync_error", "last_sync_at",
        ]

        for field, value in updates.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = :{field}")
                params[field] = value

        if not set_clauses:
            return True

        set_clauses.append("updated_at = :updated_at")

        sql = f"""
            UPDATE connections
            SET {", ".join(set_clauses)}
            WHERE id = :id
        """

        result = await session.execute(text(sql), params)
        await session.flush()

        # Reload instance if cached
        if connector_id in self._instances:
            config = await self._load_config(session, connector_id)
            if config:
                self._instances[connector_id].config = config

        return result.rowcount > 0

    async def _save_config(
        self,
        session: AsyncSession,
        config: ConnectorConfig,
    ) -> None:
        """Save connector config to database."""
        await session.execute(
            text("""
                INSERT INTO connections (
                    id, tenant_id, source, name, endpoint,
                    credentials, webhook_secret, config, scopes,
                    sync_status, is_active, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :source, :name, :endpoint,
                    :credentials, :webhook_secret, :config, :scopes,
                    :sync_status, :is_active, :created_at, :updated_at
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    endpoint = EXCLUDED.endpoint,
                    config = EXCLUDED.config,
                    updated_at = EXCLUDED.updated_at
            """),
            {
                "id": config.id,
                "tenant_id": config.tenant_id,
                "source": config.source,
                "name": config.name,
                "endpoint": config.endpoint,
                "credentials": config.credentials,
                "webhook_secret": config.credentials.get("webhook_secret"),
                "config": config.config,
                "scopes": config.scopes,
                "sync_status": config.status.value,
                "is_active": True,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        )
        await session.flush()

    async def _load_config(
        self,
        session: AsyncSession,
        connector_id: str,
    ) -> ConnectorConfig | None:
        """Load connector config from database."""
        result = await session.execute(
            text("SELECT * FROM connections WHERE id = :id AND is_active = true"),
            {"id": connector_id},
        )
        row = result.fetchone()

        if not row:
            return None

        return ConnectorConfig(
            id=row.id,
            tenant_id=row.tenant_id,
            source=row.source,
            name=row.name,
            endpoint=row.endpoint,
            credentials=row.credentials or {},
            config=row.config or {},
            scopes=row.scopes or [],
            status=ConnectorStatus(row.sync_status) if row.sync_status else ConnectorStatus.PENDING,
            last_sync_at=row.last_sync_at,
        )

    async def sync_all(
        self,
        session: AsyncSession,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """Sync all connectors for a tenant.

        Args:
            session: Database session
            tenant_id: Tenant ID

        Returns:
            List of sync results
        """
        connectors = await self.list_connectors(session, tenant_id)
        results = []

        for conn_info in connectors:
            connector = await self.get_connector(session, conn_info["id"])
            if connector:
                try:
                    result = await connector.sync()
                    results.append({
                        "connector_id": conn_info["id"],
                        "source": conn_info["source"],
                        "success": result.success,
                        "events": result.events_fetched,
                        "entities": result.entities_created + result.entities_updated,
                    })
                except Exception as e:
                    logger.error(
                        "Sync failed",
                        connector_id=conn_info["id"],
                        error=str(e),
                    )
                    results.append({
                        "connector_id": conn_info["id"],
                        "source": conn_info["source"],
                        "success": False,
                        "error": str(e),
                    })

        return results


# Global registry instance
_connector_registry: ConnectorRegistry | None = None


def get_connector_registry() -> ConnectorRegistry:
    """Get the global connector registry."""
    global _connector_registry
    if _connector_registry is None:
        _connector_registry = ConnectorRegistry()
        _register_default_connectors(_connector_registry)
    return _connector_registry


def _register_default_connectors(registry: ConnectorRegistry) -> None:
    """Register built-in connectors."""
    from app.services.connectors.github import GitHubConnector
    from app.services.connectors.gitlab import GitLabConnector

    registry.register_connector_class("github", GitHubConnector)
    registry.register_connector_class("gitlab", GitLabConnector)
