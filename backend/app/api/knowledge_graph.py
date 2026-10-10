"""API endpoints for knowledge graph operations."""

from datetime import datetime, UTC
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.config import settings

logger = structlog.get_logger()
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.input_validation import validate_cypher_identifier
from app.services.knowledge_graph import (
    Neo4jClient,
    Neo4jConfig,
    KnowledgeGraphDiscovery,
    AgentDiscoveryWorkflow,
)

router = APIRouter(prefix="/knowledge-graph", tags=["knowledge-graph"])


# ======================
# Request/Response Models
# ======================

class NodeCreate(BaseModel):
    """Request model for creating a node."""

    label: str = Field(..., description="Node label (e.g., 'Table', 'Column', 'Metric')")
    name: str = Field(..., description="Node name")
    properties: dict[str, Any] = Field(default_factory=dict)


class RelationshipCreate(BaseModel):
    """Request model for creating a relationship."""

    source_label: str
    source_name: str
    target_label: str
    target_name: str
    relationship_type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class DiscoveryRequest(BaseModel):
    """Request for agent discovery workflow."""

    query: str = Field(..., description="User query to discover relevant data")
    project_id: str | None = None


class SyncRequest(BaseModel):
    """Request to sync PostgreSQL schema to knowledge graph."""

    schema_name: str = "public"
    project_id: str | None = None


class SchemaResponse(BaseModel):
    """Response containing graph schema."""

    labels: list[str]
    relationship_types: list[str]
    node_properties: dict[str, list[str]]
    relationship_properties: dict[str, list[str]]


class StatsResponse(BaseModel):
    """Response containing graph statistics."""

    total_nodes: int
    total_relationships: int
    labels: dict[str, int]
    relationship_types: dict[str, int]


# ======================
# Dependencies
# ======================

def get_neo4j_client() -> Neo4jClient:
    """Get Neo4j client from settings."""
    if not settings.NEO4J_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge graph feature is disabled. Set NEO4J_ENABLED=true",
        )

    if not settings.NEO4J_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NEO4J_PASSWORD is required when NEO4J_ENABLED=true",
        )

    config = Neo4jConfig(
        uri=settings.NEO4J_URI,
        username=settings.NEO4J_USERNAME,
        password=settings.NEO4J_PASSWORD,
        database=settings.NEO4J_DATABASE,
        max_connection_pool_size=settings.NEO4J_MAX_CONNECTION_POOL_SIZE,
    )
    return Neo4jClient(config)


# ======================
# Endpoints
# ======================

@router.get("/health")
async def health_check():
    """Check knowledge graph connectivity."""
    if not settings.NEO4J_ENABLED:
        return {"status": "disabled", "message": "Knowledge graph is not enabled"}

    try:
        client = get_neo4j_client()
        connected = await client.verify_connectivity()
        await client.close()

        return {
            "status": "healthy" if connected else "unhealthy",
            "uri": settings.NEO4J_URI,
            "database": settings.NEO4J_DATABASE,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


@router.get("/schema", response_model=SchemaResponse)
async def get_schema(
    current_user: User = Depends(get_current_user),
):
    """Get the knowledge graph schema."""
    client = get_neo4j_client()
    try:
        schema = await client.get_schema()
        return SchemaResponse(**schema)
    finally:
        await client.close()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    current_user: User = Depends(get_current_user),
):
    """Get knowledge graph statistics."""
    client = get_neo4j_client()
    try:
        stats = await client.get_graph_stats()
        return StatsResponse(**stats)
    finally:
        await client.close()


@router.post("/nodes")
async def create_node(
    request: NodeCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new node in the knowledge graph."""
    validate_cypher_identifier(request.label, "label")
    client = get_neo4j_client()
    try:
        query = f"""
            CREATE (n:{request.label} {{name: $name}})
            SET n += $properties
            RETURN n
        """
        result = await client.execute_write(
            query,
            {"name": request.name, "properties": request.properties},
        )
        return {
            "status": "created",
            "label": request.label,
            "name": request.name,
            "stats": result,
        }
    finally:
        await client.close()


@router.get("/nodes")
async def list_nodes(
    label: str | None = Query(None, description="Filter by node label"),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
):
    """List nodes in the knowledge graph."""
    if label:
        validate_cypher_identifier(label, "label")
    client = get_neo4j_client()
    try:
        if label:
            query = f"""
                MATCH (n:{label})
                RETURN labels(n) as labels, properties(n) as properties
                LIMIT $limit
            """
        else:
            query = """
                MATCH (n)
                RETURN labels(n) as labels, properties(n) as properties
                LIMIT $limit
            """

        results = await client.execute_query(query, {"limit": limit})
        return {
            "nodes": results,
            "count": len(results),
        }
    finally:
        await client.close()


@router.post("/relationships")
async def create_relationship(
    request: RelationshipCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a relationship between nodes."""
    validate_cypher_identifier(request.source_label, "source_label")
    validate_cypher_identifier(request.target_label, "target_label")
    validate_cypher_identifier(request.relationship_type, "relationship_type")
    client = get_neo4j_client()
    try:
        query = f"""
            MATCH (source:{request.source_label} {{name: $source_name}})
            MATCH (target:{request.target_label} {{name: $target_name}})
            CREATE (source)-[r:{request.relationship_type}]->(target)
            SET r += $properties
            RETURN type(r) as type
        """
        result = await client.execute_write(
            query,
            {
                "source_name": request.source_name,
                "target_name": request.target_name,
                "properties": request.properties,
            },
        )
        return {
            "status": "created",
            "relationship_type": request.relationship_type,
            "stats": result,
        }
    finally:
        await client.close()


@router.get("/relationships")
async def list_relationships(
    relationship_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
):
    """List relationships in the knowledge graph."""
    if relationship_type:
        validate_cypher_identifier(relationship_type, "relationship_type")
    client = get_neo4j_client()
    try:
        if relationship_type:
            query = f"""
                MATCH (a)-[r:{relationship_type}]->(b)
                RETURN
                    labels(a)[0] as source_label,
                    a.name as source_name,
                    type(r) as relationship,
                    labels(b)[0] as target_label,
                    b.name as target_name
                LIMIT $limit
            """
        else:
            query = """
                MATCH (a)-[r]->(b)
                RETURN
                    labels(a)[0] as source_label,
                    a.name as source_name,
                    type(r) as relationship,
                    labels(b)[0] as target_label,
                    b.name as target_name
                LIMIT $limit
            """

        results = await client.execute_query(query, {"limit": limit})
        return {
            "relationships": results,
            "count": len(results),
        }
    finally:
        await client.close()


@router.post("/discover")
async def discover(
    request: DiscoveryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run agent discovery workflow for a query."""
    client = get_neo4j_client()
    try:
        discovery_service = KnowledgeGraphDiscovery(client)
        workflow = AgentDiscoveryWorkflow(client, discovery_service)

        result = await workflow.run_full_discovery(
            session_id=f"discovery-{current_user.id}",
            tenant_id=str(current_user.organization_id) if hasattr(current_user, 'organization_id') else "default",
            user_query=request.query,
            project_id=request.project_id,
        )

        return {
            "success": result.success,
            "schema_summary": result.schema_summary,
            "recommended_tables": result.recommended_tables,
            "recommended_joins": result.recommended_joins,
            "query_template": result.query_template,
            "warnings": result.warnings,
            "error": result.error,
        }
    finally:
        await client.close()


@router.get("/tables")
async def discover_tables(
    project_id: str | None = None,
    schema_name: str | None = None,
    current_user: User = Depends(get_current_user),
):
    """Discover available tables in the knowledge graph."""
    client = get_neo4j_client()
    try:
        discovery = KnowledgeGraphDiscovery(client)
        tables = await discovery.discover_tables(
            project_id=project_id,
            schema_name=schema_name,
        )

        return {
            "tables": [
                {
                    "name": t.name,
                    "schema_name": t.schema_name,
                    "description": t.description,
                    "column_count": len(t.columns),
                    "columns": [
                        {
                            "name": c.name,
                            "data_type": c.data_type,
                            "primary_key": c.primary_key,
                            "foreign_key": c.foreign_key,
                        }
                        for c in t.columns
                    ],
                }
                for t in tables
            ],
            "count": len(tables),
        }
    finally:
        await client.close()


@router.get("/metrics")
async def discover_metrics(
    category: str | None = None,
    project_id: str | None = None,
    current_user: User = Depends(get_current_user),
):
    """Discover available metrics in the knowledge graph."""
    client = get_neo4j_client()
    try:
        discovery = KnowledgeGraphDiscovery(client)
        metrics = await discovery.discover_metrics(
            category=category,
            project_id=project_id,
        )

        return {
            "metrics": metrics,
            "count": len(metrics),
        }
    finally:
        await client.close()


@router.get("/dora-entities")
async def discover_dora_entities(
    current_user: User = Depends(get_current_user),
):
    """Discover DORA metrics-related entities."""
    client = get_neo4j_client()
    try:
        discovery = KnowledgeGraphDiscovery(client)
        entities = await discovery.discover_dora_entities()

        return entities
    finally:
        await client.close()


@router.get("/search")
async def search_entities(
    q: str = Query(..., description="Search term"),
    entity_types: list[str] | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Search for entities in the knowledge graph."""
    if entity_types:
        for et in entity_types:
            validate_cypher_identifier(et, "entity_type")
    client = get_neo4j_client()
    try:
        discovery = KnowledgeGraphDiscovery(client)
        results = await discovery.search_entities(
            search_term=q,
            entity_types=entity_types,
            limit=limit,
        )

        return {
            "results": results,
            "count": len(results),
            "query": q,
        }
    finally:
        await client.close()


@router.get("/lineage/{entity_name}")
async def get_data_lineage(
    entity_name: str,
    entity_type: str = "Table",
    direction: str = Query("upstream", pattern="^(upstream|downstream)$"),
    max_depth: int = Query(5, ge=1, le=10),
    current_user: User = Depends(get_current_user),
):
    """Get data lineage for an entity."""
    validate_cypher_identifier(entity_type, "entity_type")
    client = get_neo4j_client()
    try:
        discovery = KnowledgeGraphDiscovery(client)
        lineage = await discovery.discover_data_lineage(
            entity_name=entity_name,
            entity_type=entity_type,
            direction=direction,
            max_depth=max_depth,
        )

        return {
            "entity": entity_name,
            "entity_type": entity_type,
            "direction": direction,
            "paths": lineage,
            "path_count": len(lineage),
        }
    finally:
        await client.close()


@router.post("/sync")
async def sync_from_postgresql(
    request: SyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync PostgreSQL schema into the knowledge graph."""
    client = get_neo4j_client()
    try:
        discovery = KnowledgeGraphDiscovery(client)

        # Get database URL from settings
        db_url = settings.DATABASE_URL

        result = await discovery.sync_from_postgresql(
            db_url=db_url,
            schema_name=request.schema_name,
            project_id=request.project_id,
        )

        return {
            "status": "synced",
            **result,
        }
    finally:
        await client.close()


@router.delete("/nodes/{label}/{name}")
async def delete_node(
    label: str,
    name: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a node from the knowledge graph."""
    validate_cypher_identifier(label, "label")
    client = get_neo4j_client()
    try:
        query = f"""
            MATCH (n:{label} {{name: $name}})
            DETACH DELETE n
            RETURN count(n) as deleted
        """
        result = await client.execute_write(query, {"name": name})
        return {
            "status": "deleted",
            "label": label,
            "name": name,
        }
    finally:
        await client.close()
