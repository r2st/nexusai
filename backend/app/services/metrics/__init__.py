"""Engineering Metrics Services.

Provides comprehensive metrics including:
- DORA Metrics (from DevLake)
- SPACE Framework Metrics
- Business Metrics (ELS, DPI, IQ, VSE, THC, KDS)
- Developer Productivity Metrics
- Team Performance Metrics
- Flow Metrics (WIP, Cycle Time, Throughput)
- AI-Powered Insights Generation
"""

from app.services.metrics.dora import DORAMetricsService, DORAMetrics, dora_metrics_service
from app.services.metrics.space import SPACEMetricsService, space_metrics_service
from app.services.metrics.business import BusinessMetricsService, business_metrics_service
from app.services.metrics.productivity import ProductivityMetricsService, productivity_metrics_service
from app.services.metrics.flow import FlowMetricsService, FlowMetrics, flow_metrics_service
from app.services.metrics.insights import AIInsightsGenerator, MetricsInsight, insights_generator
from app.services.metrics.unified import (
    UnifiedMetricsService,
    UnifiedMetrics,
    MetricsDashboardData,
    unified_metrics_service,
)

__all__ = [
    # Services
    "DORAMetricsService",
    "SPACEMetricsService",
    "BusinessMetricsService",
    "ProductivityMetricsService",
    "FlowMetricsService",
    "AIInsightsGenerator",
    "UnifiedMetricsService",
    # Models
    "DORAMetrics",
    "FlowMetrics",
    "MetricsInsight",
    "UnifiedMetrics",
    "MetricsDashboardData",
    # Singleton instances
    "dora_metrics_service",
    "space_metrics_service",
    "business_metrics_service",
    "productivity_metrics_service",
    "flow_metrics_service",
    "insights_generator",
    "unified_metrics_service",
]
