"""AI Analytics plugins for tracking AI tool usage and productivity.

This package provides plugins for:
- ai_analytics: Overall ROI and productivity metrics
- aisummary: AI-generated summaries
- cursor: Cursor IDE telemetry
- claude_code: Claude Code usage tracking
- github_copilot: GitHub Copilot metrics
- q_dev: Amazon Q Developer integration
"""

from app.services.ai_analytics.base import AIAnalyticsPlugin
from app.services.ai_analytics.cursor import CursorPlugin
from app.services.ai_analytics.claude_code import ClaudeCodePlugin
from app.services.ai_analytics.github_copilot import GitHubCopilotPlugin
from app.services.ai_analytics.q_dev import QDevPlugin
from app.services.ai_analytics.summary import AISummaryService
from app.services.ai_analytics.roi import AIROIService

__all__ = [
    "AIAnalyticsPlugin",
    "CursorPlugin",
    "ClaudeCodePlugin",
    "GitHubCopilotPlugin",
    "QDevPlugin",
    "AISummaryService",
    "AIROIService",
]
