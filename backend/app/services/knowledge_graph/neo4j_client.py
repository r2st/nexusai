"""Neo4j client for knowledge graph operations."""

from dataclasses import dataclass, field
from typing import Any
from contextlib import asynccontextmanager

import structlog

logger = structlog.get_logger()


@dataclass
class Neo4jConfig:
    """Neo4j connection configuration."""

    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"
    max_connection_pool_size: int = 50
    connection_timeout: float = 30.0
    encrypted: bool = False
    trust: str = "TRUST_ALL_CERTIFICATES"


class Neo4jClient:
    """Async Neo4j client for knowledge graph operations.

    Provides connection management and query execution for Neo4j
    knowledge graphs used in agent discovery workflows.
    """

    def __init__(self, config: Neo4jConfig):
        self.config = config
        self._driver = None
        self._async_driver = None

    def _get_driver(self):
        """Get or create Neo4j driver (sync)."""
        if self._driver is None:
            try:
                from neo4j import GraphDatabase

                self._driver = GraphDatabase.driver(
                    self.config.uri,
                    auth=(self.config.username, self.config.password),
                    max_connection_pool_size=self.config.max_connection_pool_size,
                    connection_timeout=self.config.connection_timeout,
                    encrypted=self.config.encrypted,
                )
                logger.info("Neo4j driver initialized", uri=self.config.uri)
            except ImportError:
                logger.error("neo4j package not installed")
                raise
        return self._driver

    async def _get_async_driver(self):
        """Get or create async Neo4j driver."""
        if self._async_driver is None:
            try:
                from neo4j import AsyncGraphDatabase

                self._async_driver = AsyncGraphDatabase.driver(
                    self.config.uri,
                    auth=(self.config.username, self.config.password),
                    max_connection_pool_size=self.config.max_connection_pool_size,
                    connection_timeout=self.config.connection_timeout,
                    encrypted=self.config.encrypted,
                )
                logger.info("Neo4j async driver initialized", uri=self.config.uri)
            except ImportError:
                logger.error("neo4j package not installed")
                raise
        return self._async_driver

    async def close(self):
        """Close the Neo4j driver."""
        if self._async_driver:
            await self._async_driver.close()
            self._async_driver = None
        if self._driver:
            self._driver.close()
            self._driver = None
        logger.info("Neo4j drivers closed")

    async def verify_connectivity(self) -> bool:
        """Verify Neo4j connection."""
        try:
            driver = await self._get_async_driver()
            await driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error("Neo4j connectivity check failed", error=str(e))
            return False

    @asynccontextmanager
    async def session(self, database: str | None = None):
        """Get an async Neo4j session."""
        driver = await self._get_async_driver()
        db = database or self.config.database
        session = driver.session(database=db)
        try:
            yield session
        finally:
            await session.close()

    async def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results."""
        async with self.session(database) as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> dict[str, Any]:
        """Execute a write transaction."""
        async with self.session(database) as session:
            result = await session.run(query, parameters or {})
            summary = await result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set,
            }

    async def get_node_count(self, label: str | None = None) -> int:
        """Get count of nodes, optionally filtered by label."""
        if label:
            query = f"MATCH (n:{label}) RETURN count(n) as count"
        else:
            query = "MATCH (n) RETURN count(n) as count"

        results = await self.execute_query(query)
        return results[0]["count"] if results else 0

    async def get_relationship_count(self, rel_type: str | None = None) -> int:
        """Get count of relationships, optionally filtered by type."""
        if rel_type:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
        else:
            query = "MATCH ()-[r]->() RETURN count(r) as count"

        results = await self.execute_query(query)
        return results[0]["count"] if results else 0

    async def get_labels(self) -> list[str]:
        """Get all node labels in the graph."""
        query = "CALL db.labels() YIELD label RETURN label"
        results = await self.execute_query(query)
        return [r["label"] for r in results]

    async def get_relationship_types(self) -> list[str]:
        """Get all relationship types in the graph."""
        query = "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        results = await self.execute_query(query)
        return [r["relationshipType"] for r in results]

    async def get_schema(self) -> dict[str, Any]:
        """Get the graph schema (labels, properties, relationships)."""
        labels = await self.get_labels()
        rel_types = await self.get_relationship_types()

        schema = {
            "labels": labels,
            "relationship_types": rel_types,
            "node_properties": {},
            "relationship_properties": {},
        }

        # Get properties for each label
        for label in labels:
            query = f"""
                MATCH (n:{label})
                WITH n LIMIT 100
                UNWIND keys(n) as key
                RETURN DISTINCT key
            """
            results = await self.execute_query(query)
            schema["node_properties"][label] = [r["key"] for r in results]

        # Get properties for each relationship type
        for rel_type in rel_types:
            query = f"""
                MATCH ()-[r:{rel_type}]->()
                WITH r LIMIT 100
                UNWIND keys(r) as key
                RETURN DISTINCT key
            """
            results = await self.execute_query(query)
            schema["relationship_properties"][rel_type] = [r["key"] for r in results]

        return schema

    async def get_graph_stats(self) -> dict[str, Any]:
        """Get comprehensive graph statistics."""
        node_count = await self.get_node_count()
        rel_count = await self.get_relationship_count()
        labels = await self.get_labels()
        rel_types = await self.get_relationship_types()

        # Get counts per label
        label_counts = {}
        for label in labels:
            count = await self.get_node_count(label)
            label_counts[label] = count

        # Get counts per relationship type
        rel_counts = {}
        for rel_type in rel_types:
            count = await self.get_relationship_count(rel_type)
            rel_counts[rel_type] = count

        return {
            "total_nodes": node_count,
            "total_relationships": rel_count,
            "labels": label_counts,
            "relationship_types": rel_counts,
        }

    async def find_path(
        self,
        start_label: str,
        start_property: str,
        start_value: Any,
        end_label: str,
        end_property: str,
        end_value: Any,
        max_hops: int = 5,
    ) -> list[dict[str, Any]]:
        """Find shortest path between two nodes."""
        query = f"""
            MATCH (start:{start_label} {{{start_property}: $start_value}})
            MATCH (end:{end_label} {{{end_property}: $end_value}})
            MATCH path = shortestPath((start)-[*..{max_hops}]-(end))
            RETURN path,
                   [node in nodes(path) | labels(node)] as node_labels,
                   [rel in relationships(path) | type(rel)] as rel_types
        """

        return await self.execute_query(
            query,
            {
                "start_value": start_value,
                "end_value": end_value,
            },
        )

    async def get_neighbors(
        self,
        label: str,
        property_name: str,
        property_value: Any,
        depth: int = 1,
        direction: str = "both",
    ) -> list[dict[str, Any]]:
        """Get neighboring nodes."""
        direction_pattern = {
            "outgoing": "-[r]->",
            "incoming": "<-[r]-",
            "both": "-[r]-",
        }.get(direction, "-[r]-")

        query = f"""
            MATCH (n:{label} {{{property_name}: $value}})
            MATCH (n){direction_pattern}(neighbor)
            RETURN DISTINCT
                   labels(neighbor) as labels,
                   properties(neighbor) as properties,
                   type(r) as relationship_type
            LIMIT 100
        """

        return await self.execute_query(query, {"value": property_value})
