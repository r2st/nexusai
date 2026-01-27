"""Dashboard Visualization Agent for creating data visualizations."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger()


class ChartType(str, Enum):
    """Types of charts/visualizations."""

    LINE = "line"
    BAR = "bar"
    AREA = "area"
    PIE = "pie"
    DONUT = "donut"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    GAUGE = "gauge"
    TABLE = "table"
    KPI_CARD = "kpi_card"
    TREND = "trend"
    SPARKLINE = "sparkline"


class DashboardTheme(str, Enum):
    """Dashboard color themes."""

    LIGHT = "light"
    DARK = "dark"
    CORPORATE = "corporate"
    COLORFUL = "colorful"


@dataclass
class ChartConfig:
    """Configuration for a single chart."""

    chart_id: str
    chart_type: ChartType
    title: str
    data_source: str  # SQL query or metric name
    x_axis: str | None = None
    y_axis: str | None = None
    series: list[str] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    width: int = 6  # Grid width (1-12)
    height: int = 4  # Grid height
    position: tuple[int, int] = (0, 0)  # Row, Column


@dataclass
class DashboardConfig:
    """Configuration for a complete dashboard."""

    dashboard_id: str
    title: str
    description: str
    charts: list[ChartConfig]
    filters: list[dict[str, Any]] = field(default_factory=list)
    theme: DashboardTheme = DashboardTheme.LIGHT
    refresh_interval: int = 300  # seconds
    layout: str = "grid"  # "grid" or "freeform"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class VisualizationResult:
    """Result of visualization generation."""

    success: bool
    dashboard: DashboardConfig | None
    chart_specs: list[dict[str, Any]]
    embed_code: str | None = None
    grafana_json: dict[str, Any] | None = None
    error: str | None = None


class DashboardVisualizationAgent:
    """Agent specialized in creating dashboard visualizations.

    This agent:
    - Receives analysis results from DORA or other agents
    - Designs appropriate visualizations for the data
    - Generates Grafana-compatible dashboard JSON
    - Creates embeddable chart configurations
    - Optimizes layout for readability
    """

    def __init__(self, grafana_url: str | None = None):
        self.grafana_url = grafana_url or settings.GRAFANA_URL
        self.agent_id = "dashboard-visualization-agent"
        self.agent_name = "Dashboard Designer"
        self.capabilities = [
            "chart_design",
            "dashboard_layout",
            "grafana_export",
            "theme_customization",
            "data_visualization",
        ]

    async def create_dora_dashboard(
        self,
        dora_data: dict[str, Any],
        dashboard_title: str = "DORA Metrics Dashboard",
    ) -> VisualizationResult:
        """Create a dashboard for DORA metrics visualization."""
        logger.info("Creating DORA dashboard", title=dashboard_title)

        charts = []

        # KPI Cards for each metric
        metrics = dora_data.get("metrics", [])
        for i, metric in enumerate(metrics):
            chart = ChartConfig(
                chart_id=f"kpi-{metric['name']}",
                chart_type=ChartType.KPI_CARD,
                title=metric["name"].replace("_", " ").title(),
                data_source=f"dora.{metric['name']}",
                options={
                    "value": metric["value"],
                    "unit": metric["unit"],
                    "performance": metric["performance"],
                    "trend": metric["trend"],
                    "color": self._get_performance_color(metric["performance"]),
                },
                width=3,
                height=2,
                position=(0, i * 3),
            )
            charts.append(chart)

        # Deployment Frequency Trend
        charts.append(ChartConfig(
            chart_id="df-trend",
            chart_type=ChartType.LINE,
            title="Deployment Frequency Trend",
            data_source="""
                SELECT
                    date_trunc('day', deployed_at) as date,
                    COUNT(*) as deployments
                FROM deployments
                WHERE deployed_at >= NOW() - INTERVAL '30 days'
                GROUP BY 1
                ORDER BY 1
            """,
            x_axis="date",
            y_axis="deployments",
            options={
                "fill": "gradient",
                "strokeWidth": 2,
                "showPoints": True,
            },
            width=6,
            height=4,
            position=(2, 0),
        ))

        # Lead Time Distribution
        charts.append(ChartConfig(
            chart_id="lt-distribution",
            chart_type=ChartType.BAR,
            title="Lead Time Distribution",
            data_source="""
                SELECT
                    CASE
                        WHEN lead_time_hours < 1 THEN '< 1 hour'
                        WHEN lead_time_hours < 24 THEN '1-24 hours'
                        WHEN lead_time_hours < 168 THEN '1-7 days'
                        ELSE '> 7 days'
                    END as bucket,
                    COUNT(*) as count
                FROM deployments
                WHERE deployed_at >= NOW() - INTERVAL '30 days'
                GROUP BY 1
            """,
            x_axis="bucket",
            y_axis="count",
            options={
                "colorByValue": True,
                "orientation": "horizontal",
            },
            width=6,
            height=4,
            position=(2, 6),
        ))

        # Change Failure Rate Gauge
        cfr_metric = next((m for m in metrics if m["name"] == "change_failure_rate"), None)
        if cfr_metric:
            charts.append(ChartConfig(
                chart_id="cfr-gauge",
                chart_type=ChartType.GAUGE,
                title="Change Failure Rate",
                data_source="dora.change_failure_rate",
                options={
                    "value": cfr_metric["value"],
                    "min": 0,
                    "max": 100,
                    "thresholds": [
                        {"value": 5, "color": "green"},
                        {"value": 10, "color": "yellow"},
                        {"value": 15, "color": "orange"},
                        {"value": 100, "color": "red"},
                    ],
                },
                width=4,
                height=4,
                position=(6, 0),
            ))

        # MTTR Trend
        charts.append(ChartConfig(
            chart_id="mttr-trend",
            chart_type=ChartType.AREA,
            title="Mean Time to Restore (MTTR)",
            data_source="""
                SELECT
                    date_trunc('week', created_at) as week,
                    AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600) as mttr_hours
                FROM incidents
                WHERE created_at >= NOW() - INTERVAL '90 days'
                  AND resolved_at IS NOT NULL
                GROUP BY 1
                ORDER BY 1
            """,
            x_axis="week",
            y_axis="mttr_hours",
            options={
                "fill": "gradient",
                "color": "#3b82f6",
            },
            width=4,
            height=4,
            position=(6, 4),
        ))

        # Performance Overview
        charts.append(ChartConfig(
            chart_id="performance-radar",
            chart_type=ChartType.TABLE,
            title="Performance Overview",
            data_source="dora.all_metrics",
            options={
                "columns": ["Metric", "Value", "Performance", "Trend"],
                "data": [
                    [
                        m["name"].replace("_", " ").title(),
                        f"{m['value']} {m['unit']}",
                        m["performance"].title(),
                        "↑" if m["trend"] == "improving" else "↓" if m["trend"] == "declining" else "→",
                    ]
                    for m in metrics
                ],
                "colorByPerformance": True,
            },
            width=4,
            height=4,
            position=(6, 8),
        ))

        dashboard = DashboardConfig(
            dashboard_id=f"dora-{dora_data.get('project_id', 'default')}",
            title=dashboard_title,
            description="DORA metrics dashboard showing key engineering performance indicators",
            charts=charts,
            filters=[
                {
                    "name": "time_range",
                    "type": "timerange",
                    "default": "30d",
                    "options": ["7d", "14d", "30d", "90d"],
                },
                {
                    "name": "project",
                    "type": "dropdown",
                    "default": dora_data.get("project_id"),
                },
            ],
            theme=DashboardTheme.CORPORATE,
        )

        # Generate Grafana-compatible JSON
        grafana_json = self._generate_grafana_json(dashboard)

        return VisualizationResult(
            success=True,
            dashboard=dashboard,
            chart_specs=[self._chart_to_spec(c) for c in charts],
            grafana_json=grafana_json,
        )

    async def create_adoption_dashboard(
        self,
        adoption_data: dict[str, Any],
    ) -> VisualizationResult:
        """Create a dashboard for AI adoption metrics."""
        logger.info("Creating AI adoption dashboard")

        charts = []

        # Overall Adoption Rate KPI
        charts.append(ChartConfig(
            chart_id="adoption-rate",
            chart_type=ChartType.KPI_CARD,
            title="AI Tool Adoption Rate",
            data_source="ai_adoption.rate",
            options={
                "value": adoption_data.get("adoption_rate", 0),
                "unit": "%",
                "trend": adoption_data.get("trend", "stable"),
                "target": 80,
            },
            width=4,
            height=2,
            position=(0, 0),
        ))

        # Active Users KPI
        charts.append(ChartConfig(
            chart_id="active-users",
            chart_type=ChartType.KPI_CARD,
            title="Active AI Tool Users",
            data_source="ai_adoption.active_users",
            options={
                "value": adoption_data.get("active_users", 0),
                "unit": "users",
                "subtitle": f"of {adoption_data.get('total_users', 0)} total",
            },
            width=4,
            height=2,
            position=(0, 4),
        ))

        # Code Suggestions Accepted KPI
        charts.append(ChartConfig(
            chart_id="suggestions-accepted",
            chart_type=ChartType.KPI_CARD,
            title="Suggestions Accepted",
            data_source="ai_adoption.acceptance_rate",
            options={
                "value": adoption_data.get("acceptance_rate", 0),
                "unit": "%",
            },
            width=4,
            height=2,
            position=(0, 8),
        ))

        # Tool Usage by Provider
        charts.append(ChartConfig(
            chart_id="usage-by-provider",
            chart_type=ChartType.PIE,
            title="Usage by AI Tool",
            data_source="ai_adoption.by_provider",
            options={
                "data": adoption_data.get("by_provider", []),
                "showLabels": True,
                "showLegend": True,
            },
            width=6,
            height=4,
            position=(2, 0),
        ))

        # Adoption Trend Over Time
        charts.append(ChartConfig(
            chart_id="adoption-trend",
            chart_type=ChartType.LINE,
            title="Adoption Trend",
            data_source="""
                SELECT
                    date_trunc('week', event_time) as week,
                    COUNT(DISTINCT user_id) as active_users,
                    SUM(suggestions_accepted) as accepted,
                    SUM(suggestions_shown) as shown
                FROM ai_usage_events
                WHERE event_time >= NOW() - INTERVAL '90 days'
                GROUP BY 1
                ORDER BY 1
            """,
            x_axis="week",
            y_axis="active_users",
            series=["active_users", "accepted"],
            options={
                "multiSeries": True,
            },
            width=6,
            height=4,
            position=(2, 6),
        ))

        dashboard = DashboardConfig(
            dashboard_id="ai-adoption",
            title="AI SDLC Adoption Dashboard",
            description="Metrics tracking AI tool adoption across development teams",
            charts=charts,
            theme=DashboardTheme.CORPORATE,
        )

        grafana_json = self._generate_grafana_json(dashboard)

        return VisualizationResult(
            success=True,
            dashboard=dashboard,
            chart_specs=[self._chart_to_spec(c) for c in charts],
            grafana_json=grafana_json,
        )

    def _get_performance_color(self, performance: str) -> str:
        """Get color based on performance level."""
        colors = {
            "elite": "#22c55e",  # Green
            "high": "#3b82f6",   # Blue
            "medium": "#f59e0b", # Yellow
            "low": "#ef4444",    # Red
        }
        return colors.get(performance.lower(), "#6b7280")

    def _chart_to_spec(self, chart: ChartConfig) -> dict[str, Any]:
        """Convert ChartConfig to JSON spec."""
        return {
            "id": chart.chart_id,
            "type": chart.chart_type.value,
            "title": chart.title,
            "dataSource": chart.data_source,
            "xAxis": chart.x_axis,
            "yAxis": chart.y_axis,
            "series": chart.series,
            "options": chart.options,
            "layout": {
                "width": chart.width,
                "height": chart.height,
                "position": chart.position,
            },
        }

    def _generate_grafana_json(self, dashboard: DashboardConfig) -> dict[str, Any]:
        """Generate Grafana-compatible dashboard JSON."""
        panels = []

        for i, chart in enumerate(dashboard.charts):
            panel = {
                "id": i + 1,
                "title": chart.title,
                "type": self._map_chart_type_to_grafana(chart.chart_type),
                "gridPos": {
                    "x": chart.position[1],
                    "y": chart.position[0],
                    "w": chart.width,
                    "h": chart.height,
                },
                "datasource": {
                    "type": "postgres",
                    "uid": "nexusai-postgres",
                },
                "targets": [
                    {
                        "refId": "A",
                        "rawSql": chart.data_source if "SELECT" in chart.data_source else "",
                        "format": "table",
                    }
                ],
                "options": chart.options,
            }
            panels.append(panel)

        return {
            "id": None,
            "uid": dashboard.dashboard_id,
            "title": dashboard.title,
            "description": dashboard.description,
            "tags": ["dora", "devops", "nexusai"],
            "timezone": "browser",
            "schemaVersion": 39,
            "version": 1,
            "refresh": f"{dashboard.refresh_interval}s",
            "time": {
                "from": "now-30d",
                "to": "now",
            },
            "panels": panels,
            "templating": {
                "list": [
                    {
                        "name": f["name"],
                        "type": "custom" if f["type"] == "dropdown" else "interval",
                        "current": {"value": f["default"]},
                        "options": [{"value": o} for o in f.get("options", [])],
                    }
                    for f in dashboard.filters
                ],
            },
        }

    def _map_chart_type_to_grafana(self, chart_type: ChartType) -> str:
        """Map internal chart type to Grafana panel type."""
        mapping = {
            ChartType.LINE: "timeseries",
            ChartType.BAR: "barchart",
            ChartType.AREA: "timeseries",
            ChartType.PIE: "piechart",
            ChartType.DONUT: "piechart",
            ChartType.SCATTER: "scatter",
            ChartType.HEATMAP: "heatmap",
            ChartType.GAUGE: "gauge",
            ChartType.TABLE: "table",
            ChartType.KPI_CARD: "stat",
            ChartType.TREND: "stat",
            ChartType.SPARKLINE: "sparkline",
        }
        return mapping.get(chart_type, "stat")

    def format_for_handoff(self, result: VisualizationResult) -> dict[str, Any]:
        """Format result for handoff to next agent."""
        return {
            "agent": self.agent_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "success": result.success,
            "dashboard_id": result.dashboard.dashboard_id if result.dashboard else None,
            "dashboard_title": result.dashboard.title if result.dashboard else None,
            "chart_count": len(result.chart_specs),
            "charts": result.chart_specs,
            "grafana_url": f"{self.grafana_url}/d/{result.dashboard.dashboard_id}" if result.dashboard else None,
            "handoff_context": "Dashboard visualization complete. Ready for executive summary.",
        }
