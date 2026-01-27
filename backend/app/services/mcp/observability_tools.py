"""
Observability MCP Tool Handlers

Provides tools for distributed tracing, log aggregation, metrics queries,
and alert management through MCP for AI assistant integration.
"""

import json
import logging
import re
import random
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from .server import MCPToolHandler
from .protocol import MCPTool
from .errors import (
    service_unavailable_error,
    not_found_error,
    connection_error,
    internal_error,
    invalid_input_error,
    ToolErrorResponse,
    ErrorCategory,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

class LogLevel(str, Enum):
    """Log severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status."""

    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class Span:
    """Distributed trace span."""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: int
    status: str  # ok, error
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict] = field(default_factory=list)


@dataclass
class Trace:
    """Distributed trace."""

    trace_id: str
    root_service: str
    root_operation: str
    start_time: datetime
    duration_ms: int
    span_count: int
    services: List[str]
    has_errors: bool
    spans: List[Span] = field(default_factory=list)


@dataclass
class LogEntry:
    """Log entry."""

    id: str
    timestamp: datetime
    level: LogLevel
    service: str
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricPoint:
    """Metric data point."""

    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """Metric definition."""

    name: str
    description: str
    unit: str
    metric_type: str  # counter, gauge, histogram
    data_points: List[MetricPoint] = field(default_factory=list)


@dataclass
class Alert:
    """Alert."""

    id: str
    name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    service: str
    started_at: datetime
    resolved_at: Optional[datetime] = None
    labels: Dict[str, str] = field(default_factory=dict)


# =============================================================================
# Observability Service (Mock Implementation)
# =============================================================================

class ObservabilityService:
    """Service for observability data: traces, logs, metrics, alerts."""

    def __init__(self):
        self._traces: Dict[str, Trace] = {}
        self._logs: List[LogEntry] = []
        self._metrics: Dict[str, Metric] = {}
        self._alerts: Dict[str, Alert] = {}
        self._generate_sample_data()

    def _generate_sample_data(self):
        """Generate sample observability data for demonstration."""
        from uuid import uuid4

        services = ["api-gateway", "user-service", "order-service", "payment-service", "notification-service"]
        operations = ["GET /api/users", "POST /api/orders", "process_payment", "send_notification", "authenticate"]

        # Generate traces
        for i in range(20):
            trace_id = uuid4().hex[:16]
            start_time = datetime.now(UTC) - timedelta(hours=random.randint(0, 48))
            has_error = random.random() < 0.2

            # Generate spans for this trace
            spans = []
            root_service = random.choice(services)
            root_operation = random.choice(operations)

            # Root span
            root_span_id = uuid4().hex[:8]
            root_duration = random.randint(100, 2000)
            spans.append(Span(
                trace_id=trace_id,
                span_id=root_span_id,
                parent_span_id=None,
                operation_name=root_operation,
                service_name=root_service,
                start_time=start_time,
                end_time=start_time + timedelta(milliseconds=root_duration),
                duration_ms=root_duration,
                status="error" if has_error else "ok",
                tags={"http.method": "GET", "http.status_code": "500" if has_error else "200"},
            ))

            # Child spans
            num_children = random.randint(2, 5)
            for j in range(num_children):
                child_service = random.choice([s for s in services if s != root_service])
                child_duration = random.randint(10, 500)
                child_start = start_time + timedelta(milliseconds=random.randint(10, 100))

                spans.append(Span(
                    trace_id=trace_id,
                    span_id=uuid4().hex[:8],
                    parent_span_id=root_span_id,
                    operation_name=f"call_{child_service}",
                    service_name=child_service,
                    start_time=child_start,
                    end_time=child_start + timedelta(milliseconds=child_duration),
                    duration_ms=child_duration,
                    status="ok",
                    tags={"component": "http"},
                ))

            services_in_trace = list(set(s.service_name for s in spans))

            self._traces[trace_id] = Trace(
                trace_id=trace_id,
                root_service=root_service,
                root_operation=root_operation,
                start_time=start_time,
                duration_ms=root_duration,
                span_count=len(spans),
                services=services_in_trace,
                has_errors=has_error,
                spans=spans,
            )

        # Generate logs
        log_messages = [
            (LogLevel.INFO, "Request received"),
            (LogLevel.INFO, "Processing started"),
            (LogLevel.DEBUG, "Cache hit for key"),
            (LogLevel.WARNING, "High latency detected"),
            (LogLevel.ERROR, "Connection timeout"),
            (LogLevel.ERROR, "Database query failed"),
            (LogLevel.INFO, "Request completed"),
            (LogLevel.CRITICAL, "Out of memory"),
        ]

        for i in range(100):
            level, base_msg = random.choice(log_messages)
            service = random.choice(services)
            timestamp = datetime.now(UTC) - timedelta(minutes=random.randint(0, 1440))

            self._logs.append(LogEntry(
                id=uuid4().hex[:8],
                timestamp=timestamp,
                level=level,
                service=service,
                message=f"{base_msg} - request_id={uuid4().hex[:8]}",
                trace_id=random.choice(list(self._traces.keys())) if random.random() > 0.3 else None,
                attributes={"host": f"pod-{random.randint(1,5)}", "region": random.choice(["us-east", "eu-west"])},
            ))

        # Sort logs by timestamp
        self._logs.sort(key=lambda l: l.timestamp, reverse=True)

        # Generate metrics
        metric_defs = [
            ("http_requests_total", "Total HTTP requests", "requests", "counter"),
            ("http_request_duration_seconds", "HTTP request duration", "seconds", "histogram"),
            ("cpu_usage_percent", "CPU usage", "percent", "gauge"),
            ("memory_usage_bytes", "Memory usage", "bytes", "gauge"),
            ("error_rate", "Error rate", "percent", "gauge"),
            ("active_connections", "Active connections", "connections", "gauge"),
        ]

        for name, desc, unit, mtype in metric_defs:
            points = []
            for minutes_ago in range(60):
                ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
                value = random.uniform(0, 100) if "percent" in name else random.uniform(10, 1000)
                points.append(MetricPoint(
                    timestamp=ts,
                    value=round(value, 2),
                    labels={"service": random.choice(services)},
                ))

            self._metrics[name] = Metric(
                name=name,
                description=desc,
                unit=unit,
                metric_type=mtype,
                data_points=points,
            )

        # Generate alerts
        alert_defs = [
            ("High Error Rate", AlertSeverity.CRITICAL, "Error rate exceeded 5%"),
            ("High Latency", AlertSeverity.WARNING, "P99 latency > 1s"),
            ("Memory Pressure", AlertSeverity.WARNING, "Memory usage > 80%"),
            ("Service Down", AlertSeverity.CRITICAL, "Health check failing"),
        ]

        for i, (name, severity, message) in enumerate(alert_defs):
            alert_id = uuid4().hex[:8]
            started = datetime.now(UTC) - timedelta(hours=random.randint(1, 24))
            status = random.choice([AlertStatus.FIRING, AlertStatus.RESOLVED, AlertStatus.ACKNOWLEDGED])

            self._alerts[alert_id] = Alert(
                id=alert_id,
                name=name,
                severity=severity,
                status=status,
                message=message,
                service=random.choice(services),
                started_at=started,
                resolved_at=started + timedelta(hours=random.randint(1, 4)) if status == AlertStatus.RESOLVED else None,
                labels={"env": "production", "team": "platform"},
            )

    async def health_check(self) -> bool:
        """Check if observability service is available."""
        return True

    async def search_traces(
        self,
        service: Optional[str] = None,
        operation: Optional[str] = None,
        min_duration_ms: Optional[int] = None,
        has_errors: Optional[bool] = None,
        limit: int = 20,
    ) -> List[Trace]:
        """Search for traces."""
        traces = list(self._traces.values())

        if service:
            traces = [t for t in traces if service in t.services]
        if operation:
            traces = [t for t in traces if operation.lower() in t.root_operation.lower()]
        if min_duration_ms:
            traces = [t for t in traces if t.duration_ms >= min_duration_ms]
        if has_errors is not None:
            traces = [t for t in traces if t.has_errors == has_errors]

        # Sort by start time (newest first)
        traces.sort(key=lambda t: t.start_time, reverse=True)
        return traces[:limit]

    async def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get a trace by ID."""
        return self._traces.get(trace_id)

    async def search_logs(
        self,
        service: Optional[str] = None,
        level: Optional[LogLevel] = None,
        query: Optional[str] = None,
        trace_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[LogEntry]:
        """Search logs."""
        logs = self._logs.copy()

        if service:
            logs = [l for l in logs if l.service == service]
        if level:
            logs = [l for l in logs if l.level == level]
        if query:
            query_lower = query.lower()
            logs = [l for l in logs if query_lower in l.message.lower()]
        if trace_id:
            logs = [l for l in logs if l.trace_id == trace_id]
        if start_time:
            logs = [l for l in logs if l.timestamp >= start_time]
        if end_time:
            logs = [l for l in logs if l.timestamp <= end_time]

        return logs[:limit]

    async def get_log_stats(
        self,
        service: Optional[str] = None,
        hours: int = 24,
    ) -> Dict:
        """Get log statistics."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        logs = [l for l in self._logs if l.timestamp >= cutoff]

        if service:
            logs = [l for l in logs if l.service == service]

        level_counts = {}
        service_counts = {}
        for log in logs:
            level_counts[log.level.value] = level_counts.get(log.level.value, 0) + 1
            service_counts[log.service] = service_counts.get(log.service, 0) + 1

        return {
            "total_logs": len(logs),
            "time_range_hours": hours,
            "by_level": level_counts,
            "by_service": service_counts,
            "error_count": level_counts.get("error", 0) + level_counts.get("critical", 0),
        }

    async def query_metrics(
        self,
        metric_name: str,
        service: Optional[str] = None,
        minutes: int = 60,
    ) -> Optional[Dict]:
        """Query metric data."""
        metric = self._metrics.get(metric_name)
        if not metric:
            return None

        cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
        points = [p for p in metric.data_points if p.timestamp >= cutoff]

        if service:
            points = [p for p in points if p.labels.get("service") == service]

        if not points:
            return {
                "metric": metric_name,
                "description": metric.description,
                "unit": metric.unit,
                "data_points": [],
            }

        values = [p.value for p in points]
        return {
            "metric": metric_name,
            "description": metric.description,
            "unit": metric.unit,
            "time_range_minutes": minutes,
            "statistics": {
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "avg": round(sum(values) / len(values), 2),
                "current": round(values[0], 2),
            },
            "data_points": [
                {
                    "timestamp": p.timestamp.isoformat(),
                    "value": p.value,
                    "labels": p.labels,
                }
                for p in points[:20]  # Limit output
            ],
        }

    async def list_metrics(self) -> List[Dict]:
        """List available metrics."""
        return [
            {
                "name": m.name,
                "description": m.description,
                "unit": m.unit,
                "type": m.metric_type,
            }
            for m in self._metrics.values()
        ]

    async def list_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        service: Optional[str] = None,
    ) -> List[Alert]:
        """List alerts."""
        alerts = list(self._alerts.values())

        if status:
            alerts = [a for a in alerts if a.status == status]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if service:
            alerts = [a for a in alerts if a.service == service]

        # Sort by started_at (newest first)
        alerts.sort(key=lambda a: a.started_at, reverse=True)
        return alerts

    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get an alert by ID."""
        return self._alerts.get(alert_id)

    async def acknowledge_alert(self, alert_id: str) -> Optional[Alert]:
        """Acknowledge an alert."""
        alert = self._alerts.get(alert_id)
        if alert:
            alert.status = AlertStatus.ACKNOWLEDGED
        return alert


# Global observability service instance
observability_service = ObservabilityService()


# =============================================================================
# Observability Tools
# =============================================================================

class ObsHealthCheckHandler(MCPToolHandler):
    """Check observability service health."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="obs_health_check",
            description="Check if the observability service (traces, logs, metrics) is available and healthy",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        try:
            is_healthy = await observability_service.health_check()
            metrics = await observability_service.list_metrics()
            alerts = await observability_service.list_alerts()

            return {
                "success": True,
                "healthy": is_healthy,
                "status": "available" if is_healthy else "unavailable",
                "capabilities": {
                    "traces": True,
                    "logs": True,
                    "metrics": len(metrics),
                    "active_alerts": sum(1 for a in alerts if a.status == AlertStatus.FIRING),
                },
                "message": "Observability service is running and ready to use.",
                "next_steps": [
                    "Use 'obs_search_traces' to find distributed traces",
                    "Use 'obs_search_logs' to search application logs",
                    "Use 'obs_list_alerts' to view active alerts",
                ],
            }
        except Exception as e:
            return connection_error(
                target="Observability Service",
                original_error=str(e),
            ).to_dict()


# =============================================================================
# Trace Tools
# =============================================================================

class ObsSearchTracesHandler(MCPToolHandler):
    """Search distributed traces."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="obs_search_traces",
            description="Search for distributed traces across services with optional filters",
            input_schema={
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Filter by service name",
                    },
                    "operation": {
                        "type": "string",
                        "description": "Filter by operation name",
                    },
                    "min_duration_ms": {
                        "type": "integer",
                        "description": "Minimum duration in milliseconds",
                    },
                    "has_errors": {
                        "type": "boolean",
                        "description": "Filter to only show traces with errors",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of traces (default: 20)",
                        "default": 20,
                    },
                },
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        service = arguments.get("service")
        operation = arguments.get("operation")
        min_duration_ms = arguments.get("min_duration_ms")
        has_errors = arguments.get("has_errors")
        limit = arguments.get("limit", 20)

        try:
            traces = await observability_service.search_traces(
                service=service,
                operation=operation,
                min_duration_ms=min_duration_ms,
                has_errors=has_errors,
                limit=limit,
            )

            return {
                "success": True,
                "count": len(traces),
                "filters": {
                    "service": service,
                    "operation": operation,
                    "min_duration_ms": min_duration_ms,
                    "has_errors": has_errors,
                },
                "traces": [
                    {
                        "trace_id": t.trace_id,
                        "root_service": t.root_service,
                        "root_operation": t.root_operation,
                        "duration_ms": t.duration_ms,
                        "span_count": t.span_count,
                        "services": t.services,
                        "has_errors": t.has_errors,
                        "start_time": t.start_time.isoformat(),
                    }
                    for t in traces
                ],
            }
        except Exception as e:
            return internal_error(
                operation="search_traces",
                error_message=str(e),
            ).to_dict()


class ObsGetTraceHandler(MCPToolHandler):
    """Get trace details."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="obs_get_trace",
            description="Get detailed information about a specific trace including all spans",
            input_schema={
                "type": "object",
                "properties": {
                    "trace_id": {
                        "type": "string",
                        "description": "Trace ID",
                    },
                },
                "required": ["trace_id"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        trace_id = arguments["trace_id"]

        try:
            trace = await observability_service.get_trace(trace_id)

            if not trace:
                return not_found_error(
                    resource_type="trace",
                    resource_name=trace_id,
                ).to_dict()

            return {
                "success": True,
                "trace": {
                    "trace_id": trace.trace_id,
                    "root_service": trace.root_service,
                    "root_operation": trace.root_operation,
                    "duration_ms": trace.duration_ms,
                    "span_count": trace.span_count,
                    "services": trace.services,
                    "has_errors": trace.has_errors,
                    "start_time": trace.start_time.isoformat(),
                    "spans": [
                        {
                            "span_id": s.span_id,
                            "parent_span_id": s.parent_span_id,
                            "service": s.service_name,
                            "operation": s.operation_name,
                            "duration_ms": s.duration_ms,
                            "status": s.status,
                            "tags": s.tags,
                        }
                        for s in trace.spans
                    ],
                },
            }
        except Exception as e:
            return internal_error(
                operation="get_trace",
                error_message=str(e),
            ).to_dict()


# =============================================================================
# Log Tools
# =============================================================================

class ObsSearchLogsHandler(MCPToolHandler):
    """Search application logs."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="obs_search_logs",
            description="Search application logs with filters for service, level, and text query",
            input_schema={
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Filter by service name",
                    },
                    "level": {
                        "type": "string",
                        "description": "Filter by log level",
                        "enum": [l.value for l in LogLevel],
                    },
                    "query": {
                        "type": "string",
                        "description": "Text search in log messages",
                    },
                    "trace_id": {
                        "type": "string",
                        "description": "Filter by trace ID to see logs for a specific request",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of logs (default: 50)",
                        "default": 50,
                    },
                },
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        service = arguments.get("service")
        level_str = arguments.get("level")
        query = arguments.get("query")
        trace_id = arguments.get("trace_id")
        limit = arguments.get("limit", 50)

        level = LogLevel(level_str) if level_str else None

        try:
            logs = await observability_service.search_logs(
                service=service,
                level=level,
                query=query,
                trace_id=trace_id,
                limit=limit,
            )

            return {
                "success": True,
                "count": len(logs),
                "filters": {
                    "service": service,
                    "level": level_str,
                    "query": query,
                    "trace_id": trace_id,
                },
                "logs": [
                    {
                        "timestamp": l.timestamp.isoformat(),
                        "level": l.level.value,
                        "service": l.service,
                        "message": l.message,
                        "trace_id": l.trace_id,
                        "attributes": l.attributes,
                    }
                    for l in logs
                ],
            }
        except Exception as e:
            return internal_error(
                operation="search_logs",
                error_message=str(e),
            ).to_dict()


class ObsGetLogStatsHandler(MCPToolHandler):
    """Get log statistics."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="obs_get_log_stats",
            description="Get statistics about log volume by level and service",
            input_schema={
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Filter by service name",
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Time range in hours (default: 24)",
                        "default": 24,
                    },
                },
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        service = arguments.get("service")
        hours = arguments.get("hours", 24)

        try:
            stats = await observability_service.get_log_stats(service, hours)

            return {
                "success": True,
                "service": service or "all",
                **stats,
                "health_status": "healthy" if stats["error_count"] < 10 else "degraded" if stats["error_count"] < 50 else "critical",
            }
        except Exception as e:
            return internal_error(
                operation="get_log_stats",
                error_message=str(e),
            ).to_dict()


# =============================================================================
# Metrics Tools
# =============================================================================

class ObsListMetricsHandler(MCPToolHandler):
    """List available metrics."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="obs_list_metrics",
            description="List all available metrics that can be queried",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        try:
            metrics = await observability_service.list_metrics()

            return {
                "success": True,
                "count": len(metrics),
                "metrics": metrics,
            }
        except Exception as e:
            return internal_error(
                operation="list_metrics",
                error_message=str(e),
            ).to_dict()


class ObsQueryMetricHandler(MCPToolHandler):
    """Query metric data."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="obs_query_metric",
            description="Query time-series data for a specific metric",
            input_schema={
                "type": "object",
                "properties": {
                    "metric_name": {
                        "type": "string",
                        "description": "Name of the metric to query",
                    },
                    "service": {
                        "type": "string",
                        "description": "Filter by service name",
                    },
                    "minutes": {
                        "type": "integer",
                        "description": "Time range in minutes (default: 60)",
                        "default": 60,
                    },
                },
                "required": ["metric_name"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        metric_name = arguments["metric_name"]
        service = arguments.get("service")
        minutes = arguments.get("minutes", 60)

        try:
            result = await observability_service.query_metrics(
                metric_name=metric_name,
                service=service,
                minutes=minutes,
            )

            if not result:
                available = await observability_service.list_metrics()
                return not_found_error(
                    resource_type="metric",
                    resource_name=metric_name,
                    available_resources=[m["name"] for m in available],
                ).to_dict()

            return {
                "success": True,
                **result,
            }
        except Exception as e:
            return internal_error(
                operation="query_metric",
                error_message=str(e),
            ).to_dict()


# =============================================================================
# Alert Tools
# =============================================================================

class ObsListAlertsHandler(MCPToolHandler):
    """List alerts."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="obs_list_alerts",
            description="List active and recent alerts",
            input_schema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by alert status",
                        "enum": [s.value for s in AlertStatus],
                    },
                    "severity": {
                        "type": "string",
                        "description": "Filter by severity",
                        "enum": [s.value for s in AlertSeverity],
                    },
                    "service": {
                        "type": "string",
                        "description": "Filter by service name",
                    },
                },
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        status_str = arguments.get("status")
        severity_str = arguments.get("severity")
        service = arguments.get("service")

        status = AlertStatus(status_str) if status_str else None
        severity = AlertSeverity(severity_str) if severity_str else None

        try:
            alerts = await observability_service.list_alerts(
                status=status,
                severity=severity,
                service=service,
            )

            firing_count = sum(1 for a in alerts if a.status == AlertStatus.FIRING)

            return {
                "success": True,
                "count": len(alerts),
                "firing_count": firing_count,
                "filters": {
                    "status": status_str,
                    "severity": severity_str,
                    "service": service,
                },
                "alerts": [
                    {
                        "id": a.id,
                        "name": a.name,
                        "severity": a.severity.value,
                        "status": a.status.value,
                        "message": a.message,
                        "service": a.service,
                        "started_at": a.started_at.isoformat(),
                        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                        "labels": a.labels,
                    }
                    for a in alerts
                ],
            }
        except Exception as e:
            return internal_error(
                operation="list_alerts",
                error_message=str(e),
            ).to_dict()


class ObsGetAlertHandler(MCPToolHandler):
    """Get alert details."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="obs_get_alert",
            description="Get detailed information about a specific alert",
            input_schema={
                "type": "object",
                "properties": {
                    "alert_id": {
                        "type": "string",
                        "description": "Alert ID",
                    },
                },
                "required": ["alert_id"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        alert_id = arguments["alert_id"]

        try:
            alert = await observability_service.get_alert(alert_id)

            if not alert:
                return not_found_error(
                    resource_type="alert",
                    resource_name=alert_id,
                ).to_dict()

            return {
                "success": True,
                "alert": {
                    "id": alert.id,
                    "name": alert.name,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "message": alert.message,
                    "service": alert.service,
                    "started_at": alert.started_at.isoformat(),
                    "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                    "duration": str(datetime.now(UTC) - alert.started_at) if alert.status == AlertStatus.FIRING else None,
                    "labels": alert.labels,
                },
            }
        except Exception as e:
            return internal_error(
                operation="get_alert",
                error_message=str(e),
            ).to_dict()


class ObsAcknowledgeAlertHandler(MCPToolHandler):
    """Acknowledge an alert."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="obs_acknowledge_alert",
            description="Acknowledge an alert to indicate it's being investigated",
            input_schema={
                "type": "object",
                "properties": {
                    "alert_id": {
                        "type": "string",
                        "description": "Alert ID to acknowledge",
                    },
                },
                "required": ["alert_id"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        alert_id = arguments["alert_id"]

        try:
            alert = await observability_service.acknowledge_alert(alert_id)

            if not alert:
                return not_found_error(
                    resource_type="alert",
                    resource_name=alert_id,
                ).to_dict()

            return {
                "success": True,
                "message": f"Alert {alert_id} acknowledged",
                "alert": {
                    "id": alert.id,
                    "name": alert.name,
                    "status": alert.status.value,
                },
            }
        except Exception as e:
            return internal_error(
                operation="acknowledge_alert",
                error_message=str(e),
            ).to_dict()


# =============================================================================
# Helper function to get all observability tool handlers
# =============================================================================

def get_all_observability_tool_handlers() -> list[MCPToolHandler]:
    """Return all Observability MCP tool handlers."""
    return [
        # Health
        ObsHealthCheckHandler(),

        # Traces
        ObsSearchTracesHandler(),
        ObsGetTraceHandler(),

        # Logs
        ObsSearchLogsHandler(),
        ObsGetLogStatsHandler(),

        # Metrics
        ObsListMetricsHandler(),
        ObsQueryMetricHandler(),

        # Alerts
        ObsListAlertsHandler(),
        ObsGetAlertHandler(),
        ObsAcknowledgeAlertHandler(),
    ]
