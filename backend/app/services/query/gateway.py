"""Query Gateway for unified data access across stores."""

import time
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.query.models import (
    DASHBOARD_QUERIES,
    DashboardQuery,
    DataSource,
    QueryRequest,
    QueryResponse,
)

logger = structlog.get_logger()


class QueryGateway:
    """Unified query gateway for dashboard data access.

    Aggregates data from multiple stores:
    - Metrics: Precomputed DORA/SPACE rollups
    - Entities: Canonical domain entities
    - Events: Raw event index
    - Search: Full-text search
    - Graph: Knowledge graph queries
    """

    def __init__(self):
        self._cache: dict[str, tuple[datetime, Any]] = {}
        self._cache_ttl = 300  # 5 minutes default

    async def query(
        self,
        session: AsyncSession,
        tenant_id: str,
        request: QueryRequest,
    ) -> QueryResponse:
        """Execute a unified query.

        Args:
            session: Database session
            tenant_id: Tenant ID
            request: Query request

        Returns:
            QueryResponse with aggregated data
        """
        start_time = time.time()

        response = QueryResponse(
            tenant_id=tenant_id,
            request=request,
        )

        try:
            # Query each requested source
            for source in request.sources:
                if source == DataSource.METRICS:
                    data = await self._query_metrics(session, tenant_id, request)
                    response.data["metrics"] = data

                elif source == DataSource.ENTITIES:
                    data = await self._query_entities(session, tenant_id, request)
                    response.data["entities"] = data
                    response.total_count += data.get("total", 0)

                elif source == DataSource.EVENTS:
                    data = await self._query_events(session, tenant_id, request)
                    response.data["events"] = data
                    response.total_count += data.get("total", 0)

                elif source == DataSource.SEARCH:
                    data = await self._query_search(tenant_id, request)
                    response.data["search"] = data
                    response.total_count += data.get("total", 0)

            # Generate summary if requested
            if request.include_trends:
                response.summary = await self._generate_summary(response.data)

        except Exception as e:
            logger.error("Query failed", error=str(e))
            response.warnings.append(f"Query error: {str(e)}")

        response.execution_time_ms = (time.time() - start_time) * 1000
        return response

    async def query_dashboard(
        self,
        session: AsyncSession,
        tenant_id: str,
        dashboard_name: str,
        filters: dict[str, Any] | None = None,
    ) -> QueryResponse:
        """Execute a pre-defined dashboard query.

        Args:
            session: Database session
            tenant_id: Tenant ID
            dashboard_name: Name of the dashboard query
            filters: Optional filter overrides

        Returns:
            QueryResponse
        """
        dashboard = DASHBOARD_QUERIES.get(dashboard_name)
        if not dashboard:
            raise ValueError(f"Unknown dashboard: {dashboard_name}")

        # Check cache
        cache_key = f"{tenant_id}:{dashboard_name}:{hash(str(filters))}"
        if cache_key in self._cache:
            cached_at, cached_data = self._cache[cache_key]
            if (datetime.now(UTC) - cached_at).total_seconds() < dashboard.cache_ttl_seconds:
                return cached_data

        # Parse time range
        end_time = datetime.now(UTC)
        time_ranges = {
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
        }
        start_time = end_time - time_ranges.get(dashboard.time_range, timedelta(days=7))

        # Build request
        request = QueryRequest(
            sources=dashboard.sources,
            start_time=start_time,
            end_time=end_time,
            include_trends=True,
        )

        # Apply filters
        if filters:
            if "project_id" in filters:
                request.project_id = filters["project_id"]
            if "team_id" in filters:
                request.team_id = filters["team_id"]

        # Execute query
        response = await self.query(session, tenant_id, request)

        # Filter metrics
        if dashboard.metrics and "metrics" in response.data:
            filtered_metrics = {}
            for metric in dashboard.metrics:
                if metric in response.data["metrics"]:
                    filtered_metrics[metric] = response.data["metrics"][metric]
            response.data["metrics"] = filtered_metrics

        # Cache response
        self._cache[cache_key] = (datetime.now(UTC), response)

        return response

    async def _query_metrics(
        self,
        session: AsyncSession,
        tenant_id: str,
        request: QueryRequest,
    ) -> dict[str, Any]:
        """Query precomputed metrics rollups."""
        from app.services.rollups import RollupQuery, RollupGranularity, get_rollup_service

        service = get_rollup_service()
        result = {
            "dora": {},
            "space": {},
        }

        # Determine granularity based on time range
        time_range = (request.end_time or datetime.now(UTC)) - (
            request.start_time or datetime.now(UTC) - timedelta(days=30)
        )
        if time_range.days <= 1:
            granularity = RollupGranularity.HOURLY
        elif time_range.days <= 7:
            granularity = RollupGranularity.DAILY
        elif time_range.days <= 90:
            granularity = RollupGranularity.WEEKLY
        else:
            granularity = RollupGranularity.MONTHLY

        # Query DORA metrics
        dora_query = RollupQuery(
            tenant_id=tenant_id,
            metric_type="dora",
            granularity=granularity,
            start_date=request.start_time or datetime.now(UTC) - timedelta(days=30),
            end_date=request.end_time or datetime.now(UTC),
            project_id=request.project_id,
            team_id=request.team_id,
        )
        dora_rollups = await service.query_rollups(session, dora_query)
        result["dora"]["rollups"] = dora_rollups

        # Compute aggregates
        if dora_rollups:
            result["dora"]["latest"] = dora_rollups[-1] if dora_rollups else None
            result["dora"]["count"] = len(dora_rollups)

            # Calculate averages
            valid_rollups = [r for r in dora_rollups if not r.get("no_data")]
            if valid_rollups:
                result["dora"]["averages"] = {
                    "deployment_frequency": sum(
                        r.get("deployment_frequency", 0) for r in valid_rollups
                    ) / len(valid_rollups),
                    "lead_time_hours": sum(
                        r.get("lead_time_hours", 0) for r in valid_rollups if r.get("lead_time_hours")
                    ) / max(len([r for r in valid_rollups if r.get("lead_time_hours")]), 1),
                }

        # Query SPACE metrics
        space_query = RollupQuery(
            tenant_id=tenant_id,
            metric_type="space",
            granularity=granularity,
            start_date=request.start_time or datetime.now(UTC) - timedelta(days=30),
            end_date=request.end_time or datetime.now(UTC),
            project_id=request.project_id,
            team_id=request.team_id,
        )
        space_rollups = await service.query_rollups(session, space_query)
        result["space"]["rollups"] = space_rollups
        result["space"]["latest"] = space_rollups[-1] if space_rollups else None

        return result

    async def _query_entities(
        self,
        session: AsyncSession,
        tenant_id: str,
        request: QueryRequest,
    ) -> dict[str, Any]:
        """Query canonical entities."""
        result = {
            "items": [],
            "total": 0,
            "by_type": {},
        }

        # Build query
        sql = """
            SELECT entity_type, COUNT(*) as count
            FROM entities
            WHERE tenant_id = :tenant_id
        """
        params: dict[str, Any] = {"tenant_id": tenant_id}

        if request.start_time:
            sql += " AND source_created_at >= :start_time"
            params["start_time"] = request.start_time

        if request.end_time:
            sql += " AND source_created_at < :end_time"
            params["end_time"] = request.end_time

        if request.entity_types:
            sql += " AND entity_type = ANY(:entity_types)"
            params["entity_types"] = request.entity_types

        if request.project_id:
            sql += " AND data->>'repository_id' = :project_id"
            params["project_id"] = request.project_id

        sql += " GROUP BY entity_type"

        # Get counts by type
        count_result = await session.execute(text(sql), params)
        for row in count_result.fetchall():
            result["by_type"][row.entity_type] = row.count
            result["total"] += row.count

        # Get actual entities if limit is reasonable
        if request.limit <= 100:
            entity_sql = """
                SELECT id, entity_type, source, source_id, domain_id,
                       source_created_at, data
                FROM entities
                WHERE tenant_id = :tenant_id
            """
            entity_params = {"tenant_id": tenant_id}

            if request.start_time:
                entity_sql += " AND source_created_at >= :start_time"
                entity_params["start_time"] = request.start_time

            if request.end_time:
                entity_sql += " AND source_created_at < :end_time"
                entity_params["end_time"] = request.end_time

            if request.entity_types:
                entity_sql += " AND entity_type = ANY(:entity_types)"
                entity_params["entity_types"] = request.entity_types

            entity_sql += " ORDER BY source_created_at DESC LIMIT :limit OFFSET :offset"
            entity_params["limit"] = request.limit
            entity_params["offset"] = request.offset

            entity_result = await session.execute(text(entity_sql), entity_params)
            result["items"] = [
                {
                    "id": row.id,
                    "entity_type": row.entity_type,
                    "source": row.source,
                    "source_id": row.source_id,
                    "domain_id": row.domain_id,
                    "created_at": row.source_created_at,
                    **(row.data or {}),
                }
                for row in entity_result.fetchall()
            ]

        return result

    async def _query_events(
        self,
        session: AsyncSession,
        tenant_id: str,
        request: QueryRequest,
    ) -> dict[str, Any]:
        """Query raw events."""
        result = {
            "items": [],
            "total": 0,
            "by_source": {},
            "by_type": {},
        }

        # Get counts
        sql = """
            SELECT source, event_type, COUNT(*) as count
            FROM events_index
            WHERE tenant_id = :tenant_id
        """
        params: dict[str, Any] = {"tenant_id": tenant_id}

        if request.start_time:
            sql += " AND received_at >= :start_time"
            params["start_time"] = request.start_time

        if request.end_time:
            sql += " AND received_at < :end_time"
            params["end_time"] = request.end_time

        sql += " GROUP BY source, event_type"

        count_result = await session.execute(text(sql), params)
        for row in count_result.fetchall():
            result["by_source"][row.source] = (
                result["by_source"].get(row.source, 0) + row.count
            )
            result["by_type"][row.event_type] = (
                result["by_type"].get(row.event_type, 0) + row.count
            )
            result["total"] += row.count

        return result

    async def _query_search(
        self,
        tenant_id: str,
        request: QueryRequest,
    ) -> dict[str, Any]:
        """Query full-text search."""
        result = {
            "items": [],
            "total": 0,
        }

        if not request.search_query:
            return result

        # In production, this would query Meilisearch
        # For now, return empty result
        return result

    async def _generate_summary(self, data: dict[str, Any]) -> dict[str, Any]:
        """Generate summary from query results."""
        summary = {}

        # DORA summary
        if "metrics" in data and "dora" in data["metrics"]:
            dora = data["metrics"]["dora"]
            if dora.get("latest"):
                summary["dora_level"] = dora["latest"].get("overall_level", "unknown")
                summary["deployment_frequency"] = dora["latest"].get("deployment_frequency")
                summary["lead_time_hours"] = dora["latest"].get("lead_time_hours")
                summary["mttr_hours"] = dora["latest"].get("mttr_hours")
                summary["change_failure_rate"] = dora["latest"].get("change_failure_rate")

        # Entity summary
        if "entities" in data:
            summary["entity_counts"] = data["entities"].get("by_type", {})

        # Event summary
        if "events" in data:
            summary["event_counts"] = data["events"].get("by_source", {})

        return summary

    def clear_cache(self, tenant_id: str | None = None) -> int:
        """Clear cached query results.

        Args:
            tenant_id: Optional tenant ID to clear cache for

        Returns:
            Number of entries cleared
        """
        if tenant_id:
            keys_to_remove = [k for k in self._cache if k.startswith(f"{tenant_id}:")]
        else:
            keys_to_remove = list(self._cache.keys())

        for key in keys_to_remove:
            del self._cache[key]

        return len(keys_to_remove)

    def list_dashboards(self) -> list[dict[str, Any]]:
        """List available dashboard queries."""
        return [
            {
                "id": name,
                "name": query.name,
                "description": query.description,
                "time_range": query.time_range,
                "metrics": query.metrics,
            }
            for name, query in DASHBOARD_QUERIES.items()
        ]


# Global gateway instance
_query_gateway: QueryGateway | None = None


def get_query_gateway() -> QueryGateway:
    """Get the global query gateway instance."""
    global _query_gateway
    if _query_gateway is None:
        _query_gateway = QueryGateway()
    return _query_gateway
