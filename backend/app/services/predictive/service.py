"""Predictive Analytics Service - Main service orchestrating all predictive capabilities."""

import logging
from datetime import datetime
from typing import Any

from app.services.predictive.models import (
    Bottleneck,
    PredictiveInsight,
    Recommendation,
    RiskAssessment,
    TimeSeries,
    TimeSeriesPoint,
    TrendPrediction,
)
from app.services.predictive.trends import TrendPredictor
from app.services.predictive.bottlenecks import BottleneckDetector
from app.services.predictive.risk import RiskScorer
from app.services.predictive.recommendations import RecommendationEngine

logger = logging.getLogger(__name__)


class PredictiveAnalyticsService:
    """Main service for predictive analytics.

    Orchestrates trend prediction, bottleneck detection, risk scoring,
    and recommendation generation.
    """

    def __init__(self, llm_gateway: Any | None = None):
        """Initialize predictive analytics service.

        Args:
            llm_gateway: Optional LLM gateway for AI-powered insights
        """
        self._llm_gateway = llm_gateway
        self._trend_predictor = TrendPredictor()
        self._bottleneck_detector = BottleneckDetector()
        self._risk_scorer = RiskScorer()
        self._recommendation_engine = RecommendationEngine(llm_gateway)

    async def get_insights(
        self,
        metrics: dict[str, Any],
        time_series_data: dict[str, list[dict[str, Any]]] | None = None,
        context: dict[str, Any] | None = None,
    ) -> PredictiveInsight:
        """Get comprehensive predictive insights.

        Args:
            metrics: Current metric values
            time_series_data: Historical time series data by metric name
            context: Additional context (team info, etc.)

        Returns:
            Complete predictive insight
        """
        logger.info("Generating predictive insights")

        # Convert raw time series data
        time_series = self._parse_time_series(time_series_data or {})

        # Generate trend predictions
        trends = self._predict_trends(time_series)

        # Detect bottlenecks
        bottlenecks = self._bottleneck_detector.detect_all(metrics, time_series)

        # Generate recommendations
        recommendations = self._recommendation_engine.generate_recommendations(
            trends=trends,
            bottlenecks=bottlenecks,
            metrics=metrics,
        )

        # Generate summary
        summary = self._generate_summary(trends, bottlenecks, recommendations)

        return PredictiveInsight(
            trends=trends,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            summary=summary,
        )

    def predict_metric_trend(
        self,
        metric_name: str,
        data_points: list[dict[str, Any]],
        horizon_days: int = 7,
    ) -> TrendPrediction:
        """Predict trend for a single metric.

        Args:
            metric_name: Name of the metric
            data_points: List of {timestamp, value} dicts
            horizon_days: Forecast horizon

        Returns:
            Trend prediction
        """
        series = TimeSeries(
            name=metric_name,
            points=[
                TimeSeriesPoint(
                    timestamp=self._parse_timestamp(p["timestamp"]),
                    value=float(p["value"]),
                    metadata=p.get("metadata", {}),
                )
                for p in data_points
            ],
        )

        return self._trend_predictor.predict(series, horizon_days)

    def detect_bottlenecks(
        self,
        metrics: dict[str, Any],
    ) -> list[Bottleneck]:
        """Detect bottlenecks from current metrics.

        Args:
            metrics: Current metric values

        Returns:
            List of detected bottlenecks
        """
        return self._bottleneck_detector.detect_all(metrics)

    def assess_deployment_risk(
        self,
        deployment: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> RiskAssessment:
        """Assess risk for a deployment.

        Args:
            deployment: Deployment information
            context: Additional context

        Returns:
            Risk assessment
        """
        return self._risk_scorer.assess_deployment_risk(deployment, context)

    def assess_pr_risk(
        self,
        pr: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> RiskAssessment:
        """Assess risk for a pull request.

        Args:
            pr: Pull request information
            context: Additional context

        Returns:
            Risk assessment
        """
        return self._risk_scorer.assess_pr_risk(pr, context)

    def get_recommendations(
        self,
        trends: list[TrendPrediction] | None = None,
        bottlenecks: list[Bottleneck] | None = None,
        risk: RiskAssessment | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> list[Recommendation]:
        """Get recommendations based on various inputs.

        Args:
            trends: Trend predictions
            bottlenecks: Detected bottlenecks
            risk: Risk assessment
            metrics: Current metrics

        Returns:
            Prioritized recommendations
        """
        return self._recommendation_engine.generate_recommendations(
            trends=trends,
            bottlenecks=bottlenecks,
            risk_assessment=risk,
            metrics=metrics,
        )

    def detect_anomalies(
        self,
        metric_name: str,
        data_points: list[dict[str, Any]],
        sensitivity: float = 2.0,
    ) -> list[TimeSeriesPoint]:
        """Detect anomalies in metric data.

        Args:
            metric_name: Name of the metric
            data_points: Historical data points
            sensitivity: Sensitivity threshold (z-score)

        Returns:
            List of anomalous points
        """
        series = TimeSeries(
            name=metric_name,
            points=[
                TimeSeriesPoint(
                    timestamp=self._parse_timestamp(p["timestamp"]),
                    value=float(p["value"]),
                )
                for p in data_points
            ],
        )

        return self._trend_predictor.detect_anomalies(series, sensitivity)

    def compare_periods(
        self,
        metric_name: str,
        data_points: list[dict[str, Any]],
        period1_days: int = 7,
        period2_days: int = 7,
    ) -> dict[str, Any]:
        """Compare two time periods for a metric.

        Args:
            metric_name: Name of the metric
            data_points: Historical data points
            period1_days: Recent period length
            period2_days: Comparison period length

        Returns:
            Comparison results
        """
        series = TimeSeries(
            name=metric_name,
            points=[
                TimeSeriesPoint(
                    timestamp=self._parse_timestamp(p["timestamp"]),
                    value=float(p["value"]),
                )
                for p in data_points
            ],
        )

        return self._trend_predictor.compare_periods(series, period1_days, period2_days)

    def _parse_time_series(
        self,
        raw_data: dict[str, list[dict[str, Any]]],
    ) -> dict[str, TimeSeries]:
        """Parse raw time series data into TimeSeries objects."""
        result = {}

        for name, points in raw_data.items():
            result[name] = TimeSeries(
                name=name,
                points=[
                    TimeSeriesPoint(
                        timestamp=self._parse_timestamp(p["timestamp"]),
                        value=float(p["value"]),
                        metadata=p.get("metadata", {}),
                    )
                    for p in points
                ],
            )

        return result

    def _parse_timestamp(self, ts: Any) -> datetime:
        """Parse timestamp from various formats."""
        if isinstance(ts, datetime):
            return ts
        elif isinstance(ts, str):
            # Handle ISO format
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            return datetime.fromisoformat(ts)
        elif isinstance(ts, (int, float)):
            # Assume Unix timestamp
            return datetime.fromtimestamp(ts)
        else:
            return datetime.utcnow()

    def _predict_trends(
        self,
        time_series: dict[str, TimeSeries],
    ) -> list[TrendPrediction]:
        """Predict trends for all time series."""
        predictions = []

        for name, series in time_series.items():
            if len(series.points) >= 7:  # Need minimum data
                prediction = self._trend_predictor.predict(series)
                predictions.append(prediction)

        return predictions

    def _generate_summary(
        self,
        trends: list[TrendPrediction],
        bottlenecks: list[Bottleneck],
        recommendations: list[Recommendation],
    ) -> str:
        """Generate executive summary of insights."""
        parts = []

        # Trend summary
        declining = [t for t in trends if t.direction.value == "declining"]
        improving = [t for t in trends if t.direction.value == "improving"]

        if declining:
            parts.append(f"{len(declining)} metric(s) showing declining trends")
        if improving:
            parts.append(f"{len(improving)} metric(s) improving")

        # Bottleneck summary
        if bottlenecks:
            critical = len([b for b in bottlenecks if b.severity.value == "critical"])
            if critical:
                parts.append(f"{critical} critical bottleneck(s) identified")
            else:
                parts.append(f"{len(bottlenecks)} bottleneck(s) detected")

        # Recommendation summary
        if recommendations:
            high_priority = len([r for r in recommendations if r.priority.value in ("critical", "high")])
            parts.append(f"{high_priority} high-priority recommendations")

        if not parts:
            return "No significant issues detected. Metrics are stable."

        return ". ".join(parts) + "."


# Factory function
def get_predictive_analytics_service(
    llm_gateway: Any | None = None,
) -> PredictiveAnalyticsService:
    """Create a predictive analytics service instance.

    Args:
        llm_gateway: Optional LLM gateway for AI features

    Returns:
        Configured PredictiveAnalyticsService
    """
    return PredictiveAnalyticsService(llm_gateway=llm_gateway)
