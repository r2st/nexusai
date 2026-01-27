"""Extensions service for IDE integrations."""

from app.services.extensions.models import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisIssue,
    IssueSeverity,
    IssueCategory,
    QuickFix,
    CodeSuggestion,
    ChatRequest,
    ChatResponse,
    HoverInfo,
    CompletionItem,
    CompletionRequest,
    DiagnosticRequest,
    DiagnosticResult,
    ExtensionConfig,
    ExtensionCapabilities,
    SyncEvent,
    SyncEventType,
    Position,
)
from app.services.extensions.service import (
    ExtensionService,
    get_extension_service,
)

__all__ = [
    # Models
    "AnalysisRequest",
    "AnalysisResult",
    "AnalysisIssue",
    "IssueSeverity",
    "IssueCategory",
    "QuickFix",
    "CodeSuggestion",
    "ChatRequest",
    "ChatResponse",
    "HoverInfo",
    "CompletionItem",
    "CompletionRequest",
    "DiagnosticRequest",
    "DiagnosticResult",
    "ExtensionConfig",
    "ExtensionCapabilities",
    "SyncEvent",
    "SyncEventType",
    "Position",
    # Service
    "ExtensionService",
    "get_extension_service",
]
