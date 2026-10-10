"""ClickHouse Integration for Analytics and Telemetry.

ClickHouse provides high-performance OLAP queries for:
- Real-time analytics dashboards
- Time-series telemetry data
- Aggregated metrics storage
- Historical trend analysis
"""

from datetime import datetime, timedelta
from typing import Any

import httpx
from pydantic import BaseModel

from app.core.config import settings


class ClickHouseConfig(BaseModel):
    """ClickHouse connection configuration."""

    host: str = "localhost"
    port: int = 8123  # HTTP interface
    native_port: int = 9000  # Native protocol
    database: str = "nexusai"
    user: str = "default"
    password: str = ""
    secure: bool = False


class QueryResult(BaseModel):
    """ClickHouse query result."""

    data: list[dict[str, Any]]
    rows: int
    statistics: dict[str, Any] = {}
    elapsed: float = 0.0


class ClickHouseService:
    """Service for ClickHouse analytics operations."""

    def __init__(self, config: ClickHouseConfig | None = None):
        self.config = config or ClickHouseConfig(
            host=getattr(settings, "CLICKHOUSE_HOST", "localhost"),
            port=getattr(settings, "CLICKHOUSE_PORT", 8123),
            database=getattr(settings, "CLICKHOUSE_DATABASE", "nexusai"),
            user=getattr(settings, "CLICKHOUSE_USER", "default"),
            password=getattr(settings, "CLICKHOUSE_PASSWORD", ""),
        )
        self._initialized = False

    @property
    def base_url(self) -> str:
        """Get ClickHouse HTTP URL."""
        protocol = "https" if self.config.secure else "http"
        return f"{protocol}://{self.config.host}:{self.config.port}"

    async def initialize(self) -> bool:
        """Initialize ClickHouse database and tables."""
        if self._initialized:
            return True

        try:
            # Create database
            await self.execute(
                f"CREATE DATABASE IF NOT EXISTS {self.config.database}"
            )

            # Create analytics tables
            await self._create_tables()

            self._initialized = True
            return True

        except Exception as e:
            print(f"Failed to initialize ClickHouse: {e}")
            return False

    async def _create_tables(self) -> None:
        """Create analytics tables."""
        # Metrics time-series table
        await self.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.config.database}.metrics (
                tenant_id UUID,
                project_id UUID,
                metric_name String,
                metric_value Float64,
                dimensions Map(String, String),
                timestamp DateTime64(3),
                date Date MATERIALIZED toDate(timestamp)
            )
            ENGINE = MergeTree()
            PARTITION BY toYYYYMM(date)
            ORDER BY (tenant_id, project_id, metric_name, timestamp)
            TTL date + INTERVAL 365 DAY
        """)

        # API request logs
        await self.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.config.database}.api_requests (
                request_id UUID,
                tenant_id UUID,
                user_id UUID,
                endpoint String,
                method String,
                status_code UInt16,
                response_time_ms UInt32,
                request_size UInt32,
                response_size UInt32,
                user_agent String,
                ip_address String,
                timestamp DateTime64(3),
                date Date MATERIALIZED toDate(timestamp)
            )
            ENGINE = MergeTree()
            PARTITION BY toYYYYMM(date)
            ORDER BY (tenant_id, endpoint, timestamp)
            TTL date + INTERVAL 90 DAY
        """)

        # AI usage events
        await self.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.config.database}.ai_usage (
                event_id UUID,
                tenant_id UUID,
                user_id UUID,
                tool String,  -- cursor, copilot, claude_code, etc.
                event_type String,  -- completion, chat, edit, etc.
                tokens_input UInt32,
                tokens_output UInt32,
                cost_usd Float64,
                duration_ms UInt32,
                model String,
                metadata String,  -- JSON string
                timestamp DateTime64(3),
                date Date MATERIALIZED toDate(timestamp)
            )
            ENGINE = MergeTree()
            PARTITION BY toYYYYMM(date)
            ORDER BY (tenant_id, tool, timestamp)
            TTL date + INTERVAL 365 DAY
        """)

        # DORA metrics history
        await self.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.config.database}.dora_metrics (
                tenant_id UUID,
                project_id UUID,
                deployment_frequency Float64,
                lead_time_hours Float64,
                mttr_hours Float64,
                change_failure_rate Float64,
                overall_level String,
                period_start DateTime,
                period_end DateTime,
                timestamp DateTime64(3),
                date Date MATERIALIZED toDate(timestamp)
            )
            ENGINE = MergeTree()
            PARTITION BY toYYYYMM(date)
            ORDER BY (tenant_id, project_id, timestamp)
        """)

        # Pipeline execution logs
        await self.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.config.database}.pipeline_runs (
                run_id UUID,
                tenant_id UUID,
                blueprint_id UUID,
                project_id UUID,
                status String,
                stage_count UInt8,
                task_count UInt16,
                completed_tasks UInt16,
                failed_tasks UInt16,
                duration_seconds UInt32,
                error_message String,
                started_at DateTime64(3),
                finished_at DateTime64(3),
                date Date MATERIALIZED toDate(started_at)
            )
            ENGINE = MergeTree()
            PARTITION BY toYYYYMM(date)
            ORDER BY (tenant_id, blueprint_id, started_at)
        """)

        # Create materialized views for common aggregations
        await self._create_materialized_views()

    async def _create_materialized_views(self) -> None:
        """Create materialized views for pre-aggregated data."""
        # Hourly API stats
        await self.execute(f"""
            CREATE MATERIALIZED VIEW IF NOT EXISTS {self.config.database}.api_stats_hourly
            ENGINE = SummingMergeTree()
            PARTITION BY toYYYYMM(hour)
            ORDER BY (tenant_id, endpoint, hour)
            AS SELECT
                tenant_id,
                endpoint,
                toStartOfHour(timestamp) AS hour,
                count() AS request_count,
                sum(response_time_ms) AS total_response_time,
                countIf(status_code >= 400) AS error_count
            FROM {self.config.database}.api_requests
            GROUP BY tenant_id, endpoint, hour
        """)

        # Daily AI usage stats
        await self.execute(f"""
            CREATE MATERIALIZED VIEW IF NOT EXISTS {self.config.database}.ai_usage_daily
            ENGINE = SummingMergeTree()
            PARTITION BY toYYYYMM(day)
            ORDER BY (tenant_id, tool, day)
            AS SELECT
                tenant_id,
                tool,
                toDate(timestamp) AS day,
                count() AS event_count,
                sum(tokens_input) AS total_tokens_input,
                sum(tokens_output) AS total_tokens_output,
                sum(cost_usd) AS total_cost
            FROM {self.config.database}.ai_usage
            GROUP BY tenant_id, tool, day
        """)

    async def execute(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> QueryResult:
        """Execute a ClickHouse query.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            QueryResult with data
        """
        async with httpx.AsyncClient() as client:
            # Build URL with parameters
            url_params = {
                "database": self.config.database,
                "default_format": "JSON",
            }

            if params:
                url_params.update(params)

            response = await client.post(
                self.base_url,
                params=url_params,
                content=query,
                auth=(self.config.user, self.config.password) if self.config.password else None,
                headers={"Content-Type": "text/plain"},
            )

            if response.status_code != 200:
                raise Exception(f"ClickHouse error: {response.text}")

            # Parse response
            try:
                data = response.json()
                return QueryResult(
                    data=data.get("data", []),
                    rows=data.get("rows", 0),
                    statistics=data.get("statistics", {}),
                    elapsed=data.get("statistics", {}).get("elapsed", 0),
                )
            except Exception:
                # Non-JSON response (e.g., CREATE TABLE)
                return QueryResult(data=[], rows=0)

    async def insert_metrics(
        self,
        tenant_id: str,
        project_id: str,
        metrics: list[dict[str, Any]],
    ) -> None:
        """Insert metrics data.

        Args:
            tenant_id: Tenant ID
            project_id: Project ID
            metrics: List of metric dicts with name, value, dimensions
        """
        if not metrics:
            return

        values = []
        for m in metrics:
            dimensions = m.get("dimensions", {})
            dim_str = ", ".join(f"'{k}': '{v}'" for k, v in dimensions.items())
            values.append(
                f"('{tenant_id}', '{project_id}', '{m['name']}', "
                f"{m['value']}, map({dim_str}), now64())"
            )

        query = f"""
            INSERT INTO {self.config.database}.metrics
            (tenant_id, project_id, metric_name, metric_value, dimensions, timestamp)
            VALUES {', '.join(values)}
        """
        await self.execute(query)

    async def insert_api_request(
        self,
        tenant_id: str,
        user_id: str | None,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: int,
        request_size: int = 0,
        response_size: int = 0,
        user_agent: str = "",
        ip_address: str = "",
    ) -> None:
        """Log an API request.

        Args:
            tenant_id: Tenant ID
            user_id: User ID (optional)
            endpoint: API endpoint
            method: HTTP method
            status_code: Response status code
            response_time_ms: Response time in ms
            request_size: Request body size
            response_size: Response body size
            user_agent: Client user agent
            ip_address: Client IP
        """
        user_id_val = f"'{user_id}'" if user_id else "generateUUIDv4()"

        query = f"""
            INSERT INTO {self.config.database}.api_requests
            (request_id, tenant_id, user_id, endpoint, method, status_code,
             response_time_ms, request_size, response_size, user_agent, ip_address, timestamp)
            VALUES (
                generateUUIDv4(), '{tenant_id}', {user_id_val}, '{endpoint}',
                '{method}', {status_code}, {response_time_ms}, {request_size},
                {response_size}, '{user_agent}', '{ip_address}', now64()
            )
        """
        await self.execute(query)

    async def insert_ai_usage(
        self,
        tenant_id: str,
        user_id: str,
        tool: str,
        event_type: str,
        tokens_input: int,
        tokens_output: int,
        cost_usd: float,
        duration_ms: int,
        model: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log AI tool usage.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            tool: AI tool name
            event_type: Event type
            tokens_input: Input tokens
            tokens_output: Output tokens
            cost_usd: Cost in USD
            duration_ms: Duration in ms
            model: Model used
            metadata: Additional metadata
        """
        import json

        meta_str = json.dumps(metadata or {}).replace("'", "\\'")

        query = f"""
            INSERT INTO {self.config.database}.ai_usage
            (event_id, tenant_id, user_id, tool, event_type, tokens_input,
             tokens_output, cost_usd, duration_ms, model, metadata, timestamp)
            VALUES (
                generateUUIDv4(), '{tenant_id}', '{user_id}', '{tool}',
                '{event_type}', {tokens_input}, {tokens_output}, {cost_usd},
                {duration_ms}, '{model}', '{meta_str}', now64()
            )
        """
        await self.execute(query)

    async def get_api_stats(
        self,
        tenant_id: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        granularity: str = "hour",
    ) -> list[dict[str, Any]]:
        """Get API usage statistics.

        Args:
            tenant_id: Tenant ID
            period_start: Start of period
            period_end: End of period
            granularity: Time granularity (hour, day, week)

        Returns:
            List of stats by period
        """
        period_end = period_end or datetime.utcnow()
        period_start = period_start or (period_end - timedelta(days=7))

        time_func = {
            "hour": "toStartOfHour",
            "day": "toDate",
            "week": "toStartOfWeek",
        }.get(granularity, "toStartOfHour")

        query = f"""
            SELECT
                {time_func}(timestamp) AS period,
                endpoint,
                count() AS requests,
                avg(response_time_ms) AS avg_response_time,
                countIf(status_code >= 400) AS errors,
                countIf(status_code >= 400) / count() * 100 AS error_rate
            FROM {self.config.database}.api_requests
            WHERE tenant_id = '{tenant_id}'
                AND timestamp >= '{period_start.isoformat()}'
                AND timestamp <= '{period_end.isoformat()}'
            GROUP BY period, endpoint
            ORDER BY period DESC
        """

        result = await self.execute(query)
        return result.data

    async def get_ai_usage_stats(
        self,
        tenant_id: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> dict[str, Any]:
        """Get AI tool usage statistics.

        Args:
            tenant_id: Tenant ID
            period_start: Start of period
            period_end: End of period

        Returns:
            Usage stats by tool
        """
        period_end = period_end or datetime.utcnow()
        period_start = period_start or (period_end - timedelta(days=30))

        query = f"""
            SELECT
                tool,
                count() AS events,
                sum(tokens_input) AS total_tokens_input,
                sum(tokens_output) AS total_tokens_output,
                sum(cost_usd) AS total_cost,
                avg(duration_ms) AS avg_duration_ms,
                uniq(user_id) AS unique_users
            FROM {self.config.database}.ai_usage
            WHERE tenant_id = '{tenant_id}'
                AND timestamp >= '{period_start.isoformat()}'
                AND timestamp <= '{period_end.isoformat()}'
            GROUP BY tool
            ORDER BY total_cost DESC
        """

        result = await self.execute(query)

        return {
            "by_tool": result.data,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        }

    async def get_dora_trend(
        self,
        tenant_id: str,
        project_id: str,
        periods: int = 12,
    ) -> list[dict[str, Any]]:
        """Get DORA metrics trend.

        Args:
            tenant_id: Tenant ID
            project_id: Project ID
            periods: Number of periods

        Returns:
            DORA metrics by period
        """
        query = f"""
            SELECT
                period_start,
                period_end,
                deployment_frequency,
                lead_time_hours,
                mttr_hours,
                change_failure_rate,
                overall_level
            FROM {self.config.database}.dora_metrics
            WHERE tenant_id = '{tenant_id}'
                AND project_id = '{project_id}'
            ORDER BY period_end DESC
            LIMIT {periods}
        """

        result = await self.execute(query)
        return list(reversed(result.data))

    async def get_pipeline_stats(
        self,
        tenant_id: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> dict[str, Any]:
        """Get pipeline execution statistics.

        Args:
            tenant_id: Tenant ID
            period_start: Start of period
            period_end: End of period

        Returns:
            Pipeline execution stats
        """
        period_end = period_end or datetime.utcnow()
        period_start = period_start or (period_end - timedelta(days=30))

        query = f"""
            SELECT
                status,
                count() AS runs,
                avg(duration_seconds) AS avg_duration,
                sum(completed_tasks) AS total_completed,
                sum(failed_tasks) AS total_failed
            FROM {self.config.database}.pipeline_runs
            WHERE tenant_id = '{tenant_id}'
                AND started_at >= '{period_start.isoformat()}'
                AND started_at <= '{period_end.isoformat()}'
            GROUP BY status
        """

        result = await self.execute(query)

        return {
            "by_status": result.data,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        }

    async def health_check(self) -> bool:
        """Check ClickHouse connectivity."""
        try:
            result = await self.execute("SELECT 1")
            return len(result.data) > 0
        except Exception:
            return False


# Singleton instance
clickhouse_service = ClickHouseService()
