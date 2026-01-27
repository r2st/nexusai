"""Code Review Automation Service.

This module provides automated code review capabilities including:
- PR diff analysis
- Code smell detection
- LLM-powered review generation
- GitHub/GitLab webhook integration
"""

from app.services.code_review.analyzer import PRAnalyzer
from app.services.code_review.models import (
    CodeReview,
    CodeSmell,
    DiffAnalysis,
    PRInfo,
    ReviewComment,
    SmellSeverity,
    WebhookEvent,
)
from app.services.code_review.smells import CodeSmellDetector
from app.services.code_review.reviewer import ReviewGenerator
from app.services.code_review.webhooks import WebhookHandler
from app.services.code_review.service import CodeReviewService, get_code_review_service

__all__ = [
    "CodeReviewService",
    "get_code_review_service",
    "PRAnalyzer",
    "PRInfo",
    "DiffAnalysis",
    "CodeSmellDetector",
    "CodeSmell",
    "SmellSeverity",
    "ReviewGenerator",
    "CodeReview",
    "ReviewComment",
    "WebhookHandler",
    "WebhookEvent",
]
