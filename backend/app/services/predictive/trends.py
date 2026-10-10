"""Trend Predictor - Time series analysis and forecasting."""

import math
from collections import deque
from datetime import datetime, timedelta
from typing import Any

from app.services.predictive.models import (
    TimeSeries,
    TimeSeriesPoint,
    TrendDirection,
    TrendPrediction,
)


class TrendPredictor:
    """Predicts trends in time series data.

    Uses simple statistical methods for trend detection and forecasting.
    For production, consider integrating Prophet, ARIMA, or ML models.
    """

    def __init__(self):
        """Initialize trend predictor."""
        self._min_data_points = 7
        self._volatility_threshold = 0.3

    def predict(
        self,
        series: TimeSeries,
        horizon_days: int = 7,
    ) -> TrendPrediction:
        """Predict future trend for a time series.

        Args:
            series: Historical time series data
            horizon_days: Number of days to forecast

        Returns:
            Trend prediction with forecast
        """
        if len(series.points) < self._min_data_points:
            return self._insufficient_data_prediction(series, horizon_days)

        values = series.values
        current_value = values[-1]

        # Calculate trend statistics
        slope = self._calculate_slope(values)
        volatility = self._calculate_volatility(values)
        direction = self._determine_direction(slope, volatility)

        # Detect seasonality (simple weekly pattern check)
        seasonality = self._detect_seasonality(values)

        # Generate forecast
        forecast = self._generate_forecast(values, slope, horizon_days, seasonality)

        # Calculate predicted value (end of horizon)
        predicted_value = forecast[-1].value if forecast else current_value

        # Calculate confidence based on data quality and volatility
        confidence = self._calculate_confidence(values, volatility)

        # Generate insights
        insights = self._generate_insights(
            series.name, direction, slope, volatility, seasonality
        )

        return TrendPrediction(
            metric_name=series.name,
            direction=direction,
            current_value=current_value,
            predicted_value=predicted_value,
            confidence=confidence,
            prediction_horizon=f"{horizon_days}d",
            trend_slope=slope,
            volatility=volatility,
            seasonality_detected=seasonality is not None,
            historical_data=series.points[-30:],  # Last 30 points
            forecast_data=forecast,
            insights=insights,
        )

    def _calculate_slope(self, values: list[float]) -> float:
        """Calculate trend slope using linear regression."""
        n = len(values)
        if n < 2:
            return 0.0

        # Simple linear regression
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def _calculate_volatility(self, values: list[float]) -> float:
        """Calculate volatility (coefficient of variation)."""
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0

        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)

        return std_dev / abs(mean)

    def _determine_direction(self, slope: float, volatility: float) -> TrendDirection:
        """Determine trend direction from slope and volatility."""
        if volatility > self._volatility_threshold:
            return TrendDirection.VOLATILE

        # Normalize slope relative to typical metric scales
        if slope > 0.1:
            return TrendDirection.IMPROVING
        elif slope < -0.1:
            return TrendDirection.DECLINING
        else:
            return TrendDirection.STABLE

    def _detect_seasonality(self, values: list[float]) -> dict[str, Any] | None:
        """Detect weekly seasonality pattern."""
        if len(values) < 14:  # Need at least 2 weeks
            return None

        # Simple autocorrelation at lag 7 (weekly)
        lag = 7
        if len(values) < lag * 2:
            return None

        n = len(values)
        mean = sum(values) / n

        # Calculate autocorrelation at lag 7
        numerator = sum(
            (values[i] - mean) * (values[i - lag] - mean)
            for i in range(lag, n)
        )
        denominator = sum((v - mean) ** 2 for v in values)

        if denominator == 0:
            return None

        autocorr = numerator / denominator

        # If strong weekly correlation, seasonality detected
        if abs(autocorr) > 0.5:
            return {"period": 7, "strength": autocorr}

        return None

    def _generate_forecast(
        self,
        values: list[float],
        slope: float,
        horizon_days: int,
        seasonality: dict[str, Any] | None,
    ) -> list[TimeSeriesPoint]:
        """Generate forecast points."""
        forecast = []
        current = values[-1]
        now = datetime.utcnow()

        for i in range(1, horizon_days + 1):
            # Base linear forecast
            predicted = current + slope * i

            # Add seasonal component if detected
            if seasonality:
                period = seasonality["period"]
                # Use historical pattern for seasonal adjustment
                if len(values) > period:
                    seasonal_idx = (len(values) + i) % period
                    historical_at_phase = [
                        values[j] for j in range(len(values))
                        if j % period == seasonal_idx
                    ]
                    if historical_at_phase:
                        seasonal_mean = sum(historical_at_phase) / len(historical_at_phase)
                        overall_mean = sum(values) / len(values)
                        seasonal_factor = seasonal_mean / overall_mean if overall_mean > 0 else 1
                        predicted *= max(0, seasonal_factor)

            # Ensure non-negative for most metrics
            predicted = max(0, predicted)

            forecast.append(TimeSeriesPoint(
                timestamp=now + timedelta(days=i),
                value=round(predicted, 2),
            ))

        return forecast

    def _calculate_confidence(self, values: list[float], volatility: float) -> float:
        """Calculate prediction confidence."""
        # Base confidence from data quantity
        n = len(values)
        data_confidence = min(1.0, n / 30)  # Max confidence at 30+ points

        # Reduce confidence for high volatility
        volatility_factor = max(0, 1 - volatility)

        # Combined confidence
        confidence = data_confidence * volatility_factor

        return round(max(0.1, min(1.0, confidence)), 2)

    def _generate_insights(
        self,
        metric_name: str,
        direction: TrendDirection,
        slope: float,
        volatility: float,
        seasonality: dict[str, Any] | None,
    ) -> list[str]:
        """Generate human-readable insights."""
        insights = []

        # Direction insight
        if direction == TrendDirection.IMPROVING:
            insights.append(f"{metric_name} shows a positive trend with {abs(slope):.2f} improvement per period")
        elif direction == TrendDirection.DECLINING:
            insights.append(f"{metric_name} is declining at a rate of {abs(slope):.2f} per period")
        elif direction == TrendDirection.VOLATILE:
            insights.append(f"{metric_name} shows high volatility ({volatility:.1%}), making predictions less reliable")
        else:
            insights.append(f"{metric_name} is relatively stable")

        # Seasonality insight
        if seasonality:
            insights.append(f"Weekly pattern detected (strength: {seasonality['strength']:.2f})")

        # Volatility warning
        if volatility > 0.5:
            insights.append("High variance in data suggests investigating external factors")

        return insights

    def _insufficient_data_prediction(
        self,
        series: TimeSeries,
        horizon_days: int,
    ) -> TrendPrediction:
        """Return prediction when insufficient data available."""
        current = series.values[-1] if series.values else 0

        return TrendPrediction(
            metric_name=series.name,
            direction=TrendDirection.STABLE,
            current_value=current,
            predicted_value=current,
            confidence=0.1,
            prediction_horizon=f"{horizon_days}d",
            insights=["Insufficient data for reliable prediction (need at least 7 data points)"],
            historical_data=series.points,
        )

    def detect_anomalies(
        self,
        series: TimeSeries,
        sensitivity: float = 2.0,
    ) -> list[TimeSeriesPoint]:
        """Detect anomalies in time series using z-score method.

        Args:
            series: Time series data
            sensitivity: Number of standard deviations for anomaly threshold

        Returns:
            List of anomalous points
        """
        if len(series.points) < 10:
            return []

        values = series.values
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return []

        anomalies = []
        for point in series.points:
            z_score = abs((point.value - mean) / std_dev)
            if z_score > sensitivity:
                anomalies.append(point)

        return anomalies

    def compare_periods(
        self,
        series: TimeSeries,
        period1_days: int = 7,
        period2_days: int = 7,
    ) -> dict[str, Any]:
        """Compare two consecutive periods.

        Args:
            series: Time series data
            period1_days: Days in recent period
            period2_days: Days in comparison period

        Returns:
            Comparison metrics
        """
        total_needed = period1_days + period2_days
        if len(series.values) < total_needed:
            return {"error": "Insufficient data for comparison"}

        recent = series.values[-period1_days:]
        previous = series.values[-(period1_days + period2_days):-period1_days]

        recent_avg = sum(recent) / len(recent)
        previous_avg = sum(previous) / len(previous)

        if previous_avg == 0:
            change_pct = 0
        else:
            change_pct = ((recent_avg - previous_avg) / previous_avg) * 100

        return {
            "recent_average": round(recent_avg, 2),
            "previous_average": round(previous_avg, 2),
            "change_percent": round(change_pct, 1),
            "direction": "up" if change_pct > 0 else "down" if change_pct < 0 else "flat",
        }
