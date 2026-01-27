"""Knowledge graph discovery service for database schema understanding."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any

import structlog

from app.services.knowledge_graph.neo4j_client import Neo4jClient

logger = structlog.get_logger()


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""

    TABLE = "Table"
    COLUMN = "Column"
    METRIC = "Metric"
    TRANSFORMATION = "Transformation"
    DASHBOARD = "Dashboard"
    REPORT = "Report"
    PIPELINE = "Pipeline"
    CONNECTION = "Connection"
    PROJECT = "Project"
    TEAM = "Team"


class RelationshipType(str, Enum):
    """Types of relationships in the knowledge graph."""

    HAS_COLUMN = "HAS_COLUMN"
    REFERENCES = "REFERENCES"
    DEPENDS_ON = "DEPENDS_ON"
    DERIVED_FROM = "DERIVED_FROM"
    USES_TABLE = "USES_TABLE"
    PRODUCES = "PRODUCES"
    BELONGS_TO = "BELONGS_TO"
    OWNS = "OWNS"
    CALCULATES = "CALCULATES"
    VISUALIZES = "VISUALIZES"


@dataclass
class ColumnMetadata:
    """Metadata for a database column."""

    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    foreign_key: bool = False
    foreign_key_table: str | None = None
    foreign_key_column: str | None = None
    description: str | None = None
    sample_values: list[Any] = field(default_factory=list)


@dataclass
class TableMetadata:
    """Metadata for a database table."""

    name: str
    schema_name: str = "public"
    description: str | None = None
    columns: list[ColumnMetadata] = field(default_factory=list)
    row_count: int | None = None
    size_bytes: int | None = None
    last_updated: datetime | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class SchemaNode:
    """A node in the schema knowledge graph."""

    node_id: str
    node_type: NodeType
    name: str
    properties: dict[str, Any] = field(default_factory=dict)
    labels: list[str] = field(default_factory=list)


@dataclass
class SchemaRelationship:
    """A relationship in the schema knowledge graph."""

    source_id: str
    target_id: str
    relationship_type: RelationshipType
    properties: dict[str, Any] = field(default_factory=dict)


class KnowledgeGraphDiscovery:
    """Service for discovering and querying database schema via knowledge graph.

    This service enables agents to understand database structure before
    executing queries, following the discovery workflow:
    1. Query knowledge graph for available tables
    2. Explore relationships between entities
    3. Understand data lineage and dependencies
    4. Generate optimized queries based on schema understanding
    """

    def __init__(self, neo4j_client: Neo4jClient):
        self.neo4j = neo4j_client

    async def discover_tables(
        self,
        project_id: str | None = None,
        schema_name: str | None = None,
        tags: list[str] | None = None,
    ) -> list[TableMetadata]:
        """Discover available tables in the knowledge graph."""
        filters = []
        params: dict[str, Any] = {}

        if project_id:
            filters.append("(t)-[:BELONGS_TO]->(:Project {id: $project_id})")
            params["project_id"] = project_id

        if schema_name:
            filters.append("t.schema_name = $schema_name")
            params["schema_name"] = schema_name

        if tags:
            filters.append("any(tag IN t.tags WHERE tag IN $tags)")
            params["tags"] = tags

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        query = f"""
            MATCH (t:Table)
            {where_clause}
            OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)
            WITH t, collect({{
                name: c.name,
                data_type: c.data_type,
                nullable: c.nullable,
                primary_key: c.primary_key,
                foreign_key: c.foreign_key,
                description: c.description
            }}) as columns
            RETURN
                t.name as name,
                t.schema_name as schema_name,
                t.description as description,
                t.row_count as row_count,
                t.size_bytes as size_bytes,
                t.last_updated as last_updated,
                t.tags as tags,
                columns
            ORDER BY t.name
        """

        results = await self.neo4j.execute_query(query, params)

        tables = []
        for r in results:
            columns = [
                ColumnMetadata(
                    name=c["name"],
                    data_type=c["data_type"],
                    nullable=c.get("nullable", True),
                    primary_key=c.get("primary_key", False),
                    foreign_key=c.get("foreign_key", False),
                    description=c.get("description"),
                )
                for c in r["columns"]
                if c.get("name")
            ]

            tables.append(
                TableMetadata(
                    name=r["name"],
                    schema_name=r.get("schema_name", "public"),
                    description=r.get("description"),
                    columns=columns,
                    row_count=r.get("row_count"),
                    size_bytes=r.get("size_bytes"),
                    last_updated=r.get("last_updated"),
                    tags=r.get("tags", []),
                )
            )

        logger.info("Discovered tables", count=len(tables))
        return tables

    async def discover_metrics(
        self,
        category: str | None = None,
        project_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Discover available metrics in the knowledge graph."""
        filters = []
        params: dict[str, Any] = {}

        if category:
            filters.append("m.category = $category")
            params["category"] = category

        if project_id:
            filters.append("(m)-[:BELONGS_TO]->(:Project {id: $project_id})")
            params["project_id"] = project_id

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        query = f"""
            MATCH (m:Metric)
            {where_clause}
            OPTIONAL MATCH (m)-[:CALCULATES]->(t:Table)
            OPTIONAL MATCH (m)-[:DERIVED_FROM]->(source:Metric)
            RETURN
                m.name as name,
                m.category as category,
                m.description as description,
                m.formula as formula,
                m.unit as unit,
                m.aggregation as aggregation,
                collect(DISTINCT t.name) as source_tables,
                collect(DISTINCT source.name) as derived_from
            ORDER BY m.category, m.name
        """

        results = await self.neo4j.execute_query(query, params)

        logger.info("Discovered metrics", count=len(results))
        return results

    async def discover_relationships(
        self,
        table_name: str,
    ) -> dict[str, list[dict[str, Any]]]:
        """Discover relationships for a specific table."""
        query = """
            MATCH (t:Table {name: $table_name})

            // Outgoing relationships
            OPTIONAL MATCH (t)-[r1]->(target)
            WHERE NOT type(r1) = 'HAS_COLUMN'
            WITH t, collect({
                type: type(r1),
                target_type: labels(target)[0],
                target_name: target.name,
                properties: properties(r1)
            }) as outgoing

            // Incoming relationships
            MATCH (t:Table {name: $table_name})
            OPTIONAL MATCH (source)-[r2]->(t)
            WITH t, outgoing, collect({
                type: type(r2),
                source_type: labels(source)[0],
                source_name: source.name,
                properties: properties(r2)
            }) as incoming

            // Foreign key relationships via columns
            MATCH (t:Table {name: $table_name})
            OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)-[:REFERENCES]->(ref_c:Column)<-[:HAS_COLUMN]-(ref_t:Table)
            WITH t, outgoing, incoming, collect({
                column: c.name,
                references_table: ref_t.name,
                references_column: ref_c.name
            }) as foreign_keys

            RETURN outgoing, incoming, foreign_keys
        """

        results = await self.neo4j.execute_query(query, {"table_name": table_name})

        if not results:
            return {"outgoing": [], "incoming": [], "foreign_keys": []}

        result = results[0]
        return {
            "outgoing": [r for r in result["outgoing"] if r.get("target_name")],
            "incoming": [r for r in result["incoming"] if r.get("source_name")],
            "foreign_keys": [r for r in result["foreign_keys"] if r.get("references_table")],
        }

    async def discover_data_lineage(
        self,
        entity_name: str,
        entity_type: str = "Table",
        direction: str = "upstream",
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        """Discover data lineage (upstream sources or downstream consumers)."""
        if direction == "upstream":
            # Find sources that this entity depends on
            query = f"""
                MATCH (target:{entity_type} {{name: $entity_name}})
                MATCH path = (source)-[:PRODUCES|DERIVED_FROM|DEPENDS_ON*1..{max_depth}]->(target)
                WITH path, nodes(path) as path_nodes, relationships(path) as path_rels
                RETURN
                    [n IN path_nodes | {{type: labels(n)[0], name: n.name}}] as nodes,
                    [r IN path_rels | type(r)] as relationships,
                    length(path) as depth
                ORDER BY depth
                LIMIT 100
            """
        else:
            # Find consumers of this entity
            query = f"""
                MATCH (source:{entity_type} {{name: $entity_name}})
                MATCH path = (source)-[:PRODUCES|DERIVED_FROM|DEPENDS_ON*1..{max_depth}]->(target)
                WITH path, nodes(path) as path_nodes, relationships(path) as path_rels
                RETURN
                    [n IN path_nodes | {{type: labels(n)[0], name: n.name}}] as nodes,
                    [r IN path_rels | type(r)] as relationships,
                    length(path) as depth
                ORDER BY depth
                LIMIT 100
            """

        results = await self.neo4j.execute_query(query, {"entity_name": entity_name})

        logger.info(
            "Discovered data lineage",
            entity=entity_name,
            direction=direction,
            paths=len(results),
        )
        return results

    async def discover_dora_entities(self) -> dict[str, Any]:
        """Discover DORA metrics-related entities in the knowledge graph."""
        query = """
            // Find DORA-related tables
            MATCH (t:Table)
            WHERE t.name CONTAINS 'dora' OR
                  t.name CONTAINS 'deployment' OR
                  t.name CONTAINS 'incident' OR
                  t.name CONTAINS 'change' OR
                  t.name CONTAINS 'lead_time'
            WITH collect({name: t.name, description: t.description}) as dora_tables

            // Find DORA metrics
            MATCH (m:Metric)
            WHERE m.category = 'DORA' OR
                  m.name IN ['deployment_frequency', 'lead_time_for_changes',
                             'time_to_restore', 'change_failure_rate']
            WITH dora_tables, collect({
                name: m.name,
                description: m.description,
                formula: m.formula
            }) as dora_metrics

            // Find transformations that calculate DORA metrics
            MATCH (tr:Transformation)
            WHERE tr.name CONTAINS 'dora' OR tr.output_type = 'DORA'
            WITH dora_tables, dora_metrics, collect({
                name: tr.name,
                description: tr.description
            }) as dora_transformations

            RETURN dora_tables, dora_metrics, dora_transformations
        """

        results = await self.neo4j.execute_query(query)

        if not results:
            return {"tables": [], "metrics": [], "transformations": []}

        result = results[0]
        return {
            "tables": result.get("dora_tables", []),
            "metrics": result.get("dora_metrics", []),
            "transformations": result.get("dora_transformations", []),
        }

    async def search_entities(
        self,
        search_term: str,
        entity_types: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search for entities matching a search term."""
        types = entity_types or ["Table", "Column", "Metric", "Transformation"]
        type_filter = " OR ".join([f"n:{t}" for t in types])

        query = f"""
            MATCH (n)
            WHERE ({type_filter})
            AND (
                toLower(n.name) CONTAINS toLower($search_term) OR
                toLower(coalesce(n.description, '')) CONTAINS toLower($search_term)
            )
            RETURN
                labels(n)[0] as type,
                n.name as name,
                n.description as description,
                properties(n) as properties
            ORDER BY
                CASE WHEN toLower(n.name) STARTS WITH toLower($search_term) THEN 0 ELSE 1 END,
                n.name
            LIMIT $limit
        """

        results = await self.neo4j.execute_query(
            query,
            {"search_term": search_term, "limit": limit},
        )

        logger.info("Search completed", term=search_term, results=len(results))
        return results

    async def get_table_schema_for_query(
        self,
        table_names: list[str],
    ) -> dict[str, TableMetadata]:
        """Get detailed schema for specific tables (for query generation)."""
        query = """
            UNWIND $table_names as table_name
            MATCH (t:Table {name: table_name})
            OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)
            WITH t, collect({
                name: c.name,
                data_type: c.data_type,
                nullable: c.nullable,
                primary_key: c.primary_key,
                foreign_key: c.foreign_key,
                foreign_key_table: c.foreign_key_table,
                foreign_key_column: c.foreign_key_column,
                description: c.description
            }) as columns
            RETURN
                t.name as name,
                t.schema_name as schema_name,
                t.description as description,
                columns
        """

        results = await self.neo4j.execute_query(query, {"table_names": table_names})

        schemas = {}
        for r in results:
            columns = [
                ColumnMetadata(
                    name=c["name"],
                    data_type=c["data_type"],
                    nullable=c.get("nullable", True),
                    primary_key=c.get("primary_key", False),
                    foreign_key=c.get("foreign_key", False),
                    foreign_key_table=c.get("foreign_key_table"),
                    foreign_key_column=c.get("foreign_key_column"),
                    description=c.get("description"),
                )
                for c in r["columns"]
                if c.get("name")
            ]

            schemas[r["name"]] = TableMetadata(
                name=r["name"],
                schema_name=r.get("schema_name", "public"),
                description=r.get("description"),
                columns=columns,
            )

        return schemas

    async def sync_from_postgresql(
        self,
        db_url: str,
        schema_name: str = "public",
        project_id: str | None = None,
    ) -> dict[str, int]:
        """Sync PostgreSQL schema into the knowledge graph."""
        try:
            from sqlalchemy import create_engine, inspect, MetaData

            engine = create_engine(db_url.replace("+asyncpg", ""))
            inspector = inspect(engine)

            nodes_created = 0
            relationships_created = 0

            # Get all tables
            tables = inspector.get_table_names(schema=schema_name)

            for table_name in tables:
                # Create table node
                columns = inspector.get_columns(table_name, schema=schema_name)
                pk_columns = inspector.get_pk_constraint(table_name, schema=schema_name)
                fk_constraints = inspector.get_foreign_keys(table_name, schema=schema_name)

                pk_column_names = pk_columns.get("constrained_columns", [])

                # Build FK lookup
                fk_lookup = {}
                for fk in fk_constraints:
                    for i, col in enumerate(fk["constrained_columns"]):
                        fk_lookup[col] = {
                            "table": fk["referred_table"],
                            "column": fk["referred_columns"][i],
                        }

                # Create table node
                table_query = """
                    MERGE (t:Table {name: $name, schema_name: $schema_name})
                    SET t.last_synced = datetime()
                    RETURN t
                """
                await self.neo4j.execute_write(
                    table_query,
                    {"name": table_name, "schema_name": schema_name},
                )
                nodes_created += 1

                # Create column nodes and relationships
                for col in columns:
                    is_pk = col["name"] in pk_column_names
                    is_fk = col["name"] in fk_lookup
                    fk_info = fk_lookup.get(col["name"], {})

                    column_query = """
                        MERGE (c:Column {name: $col_name, table_name: $table_name})
                        SET c.data_type = $data_type,
                            c.nullable = $nullable,
                            c.primary_key = $primary_key,
                            c.foreign_key = $foreign_key,
                            c.foreign_key_table = $fk_table,
                            c.foreign_key_column = $fk_column
                        WITH c
                        MATCH (t:Table {name: $table_name, schema_name: $schema_name})
                        MERGE (t)-[:HAS_COLUMN]->(c)
                    """
                    await self.neo4j.execute_write(
                        column_query,
                        {
                            "col_name": col["name"],
                            "table_name": table_name,
                            "schema_name": schema_name,
                            "data_type": str(col["type"]),
                            "nullable": col.get("nullable", True),
                            "primary_key": is_pk,
                            "foreign_key": is_fk,
                            "fk_table": fk_info.get("table"),
                            "fk_column": fk_info.get("column"),
                        },
                    )
                    nodes_created += 1
                    relationships_created += 1

                    # Create FK reference relationship
                    if is_fk:
                        fk_rel_query = """
                            MATCH (c:Column {name: $col_name, table_name: $table_name})
                            MATCH (ref_t:Table {name: $ref_table})
                            MATCH (ref_c:Column {name: $ref_column, table_name: $ref_table})
                            MERGE (c)-[:REFERENCES]->(ref_c)
                        """
                        await self.neo4j.execute_write(
                            fk_rel_query,
                            {
                                "col_name": col["name"],
                                "table_name": table_name,
                                "ref_table": fk_info["table"],
                                "ref_column": fk_info["column"],
                            },
                        )
                        relationships_created += 1

                # Link to project if provided
                if project_id:
                    project_query = """
                        MATCH (t:Table {name: $table_name, schema_name: $schema_name})
                        MERGE (p:Project {id: $project_id})
                        MERGE (t)-[:BELONGS_TO]->(p)
                    """
                    await self.neo4j.execute_write(
                        project_query,
                        {
                            "table_name": table_name,
                            "schema_name": schema_name,
                            "project_id": project_id,
                        },
                    )
                    relationships_created += 1

            engine.dispose()

            logger.info(
                "PostgreSQL schema synced to knowledge graph",
                tables=len(tables),
                nodes_created=nodes_created,
                relationships_created=relationships_created,
            )

            return {
                "tables": len(tables),
                "nodes_created": nodes_created,
                "relationships_created": relationships_created,
            }

        except Exception as e:
            logger.error("Failed to sync PostgreSQL schema", error=str(e))
            raise
