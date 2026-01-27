"""Predictive Analytics Service.

This module provides predictive analytics capabilities including:
- Time series trend prediction
- Bottleneck detection
- Deployment risk scoring
- Actionable recommendations
"""

from app.services.predictive.trends import TrendPredictor, TrendPrediction, TrendDirection
from app.services.predictive.bottlenecks import BottleneckDetector, Bottleneck, BottleneckType
from app.services.predictive.risk import RiskScorer, RiskAssessment, RiskLevel
from app.services.predictive.recommendations import RecommendationEngine, Recommendation, RecommendationType
from app.services.predictive.service import PredictiveAnalyticsService, get_predictive_analytics_service

__all__ = [
    "PredictiveAnalyticsService",
    "get_predictive_analytics_service",
    "TrendPredictor",
    "TrendPrediction",
    "TrendDirection",
    "BottleneckDetector",
    "Bottleneck",
    "BottleneckType",
    "RiskScorer",
    "RiskAssessment",
    "RiskLevel",
    "RecommendationEngine",
    "Recommendation",
    "RecommendationType",
]
