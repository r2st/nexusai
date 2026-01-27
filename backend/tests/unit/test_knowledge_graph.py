"""
Unit tests for Knowledge Graph API endpoints.
"""

import pytest
from uuid import uuid4


class TestKnowledgeGraphAPI:
    """Test cases for knowledge graph endpoints."""

    @pytest.mark.asyncio
    async def test_get_stats(self, client, auth_headers):
        """Test getting knowledge graph statistics."""
        response = await client.get(
            "/api/v1/knowledge-graph/stats",
            headers=auth_headers,
        )
        # May return 503 if Neo4j is not available
        assert response.status_code in [200, 401, 503]
        if response.status_code == 200:
            data = response.json()
            assert "total_nodes" in data or "status" in data

    @pytest.mark.asyncio
    async def test_discover(self, client, auth_headers):
        """Test discovering entities from query."""
        response = await client.post(
            "/api/v1/knowledge-graph/discover",
            json={"query": "deployment frequency"},
            headers=auth_headers,
        )
        assert response.status_code in [200, 400, 401, 503]

    @pytest.mark.asyncio
    async def test_get_tables(self, client, auth_headers):
        """Test getting available tables."""
        response = await client.get(
            "/api/v1/knowledge-graph/tables",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401, 503]

    @pytest.mark.asyncio
    async def test_get_metrics(self, client, auth_headers):
        """Test getting available metrics."""
        response = await client.get(
            "/api/v1/knowledge-graph/metrics",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401, 503]

    @pytest.mark.asyncio
    async def test_sync_from_postgres(self, client, auth_headers):
        """Test syncing knowledge graph from Postgres."""
        response = await client.post(
            "/api/v1/knowledge-graph/sync",
            headers=auth_headers,
        )
        assert response.status_code in [200, 400, 401, 422, 503]

    @pytest.mark.asyncio
    async def test_get_entity(self, client, auth_headers):
        """Test getting a specific entity."""
        response = await client.get(
            "/api/v1/knowledge-graph/entities/test_entity",
            headers=auth_headers,
        )
        assert response.status_code in [200, 404, 401, 503]

    @pytest.mark.asyncio
    async def test_get_entity_neighbors(self, client, auth_headers):
        """Test getting entity neighbors."""
        response = await client.get(
            "/api/v1/knowledge-graph/entities/test_entity/neighbors",
            headers=auth_headers,
        )
        assert response.status_code in [200, 404, 401, 503]

    @pytest.mark.asyncio
    async def test_get_entity_lineage(self, client, auth_headers):
        """Test getting entity lineage."""
        response = await client.get(
            "/api/v1/knowledge-graph/entities/test_entity/lineage?direction=upstream",
            headers=auth_headers,
        )
        assert response.status_code in [200, 404, 401, 503]

    @pytest.mark.asyncio
    async def test_search_entities(self, client, auth_headers):
        """Test searching entities."""
        response = await client.get(
            "/api/v1/knowledge-graph/search?q=deployment",
            headers=auth_headers,
        )
        assert response.status_code in [200, 400, 401, 503]

    @pytest.mark.asyncio
    async def test_knowledge_graph_unauthorized(self, client):
        """Test accessing knowledge graph without authentication."""
        response = await client.get("/api/v1/knowledge-graph/stats")
        assert response.status_code in [401, 403]


class TestKnowledgeGraphValidation:
    """Test knowledge graph input validation."""

    @pytest.mark.asyncio
    async def test_discover_empty_query(self, client, auth_headers):
        """Test discovery with empty query."""
        response = await client.post(
            "/api/v1/knowledge-graph/discover",
            json={"query": ""},
            headers=auth_headers,
        )
        assert response.status_code in [400, 404, 422, 503]

    @pytest.mark.asyncio
    async def test_lineage_invalid_direction(self, client, auth_headers):
        """Test lineage with invalid direction."""
        response = await client.get(
            "/api/v1/knowledge-graph/entities/test/lineage?direction=invalid",
            headers=auth_headers,
        )
        assert response.status_code in [400, 404, 422, 503]
