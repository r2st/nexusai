"""Data models for IDE Extension service."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    """Severity level for code issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


class IssueCategory(str, Enum):
    """Category of code issue."""

    SECURITY = "security"
    PERFORMANCE = "performance"
    BUG = "bug"
    STYLE = "style"
    COMPLEXITY = "complexity"
    MAINTAINABILITY = "maintainability"
    DOCUMENTATION = "documentation"
    BEST_PRACTICE = "best_practice"
    DEPRECATED = "deprecated"
    TYPE_ERROR = "type_error"


class SyncEventType(str, Enum):
    """Type of sync event."""

    FILE_CHANGED = "file_changed"
    FILE_OPENED = "file_opened"
    FILE_CLOSED = "file_closed"
    ANALYSIS_COMPLETE = "analysis_complete"
    DIAGNOSTICS_UPDATED = "diagnostics_updated"
    CONFIG_CHANGED = "config_changed"


class Position(BaseModel):
    """Position in a document."""

    line: int = Field(..., ge=0, description="Zero-based line number")
    character: int = Field(..., ge=0, description="Zero-based character offset")


class Range(BaseModel):
    """Range in a document."""

    start: Position
    end: Position


class QuickFix(BaseModel):
    """A quick fix action for an issue."""

    title: str
    kind: str = "quickfix"  # quickfix, refactor, source
    edit: dict[str, Any] | None = None  # TextEdit format
    command: str | None = None
    arguments: list[Any] | None = None
    is_preferred: bool = False


class AnalysisIssue(BaseModel):
    """A code analysis issue/diagnostic."""

    id: str
    message: str
    severity: IssueSeverity
    category: IssueCategory
    range: Range
    source: str = "nexusai"
    code: str | None = None
    code_description: str | None = None
    related_information: list[dict[str, Any]] | None = None
    quick_fixes: list[QuickFix] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class CodeSuggestion(BaseModel):
    """An AI-generated code suggestion."""

    id: str
    text: str
    insert_text: str
    range: Range
    kind: str = "snippet"  # text, method, function, constructor, field, variable, etc.
    detail: str | None = None
    documentation: str | None = None
    sort_text: str | None = None
    filter_text: str | None = None
    preselect: bool = False
    commit_characters: list[str] = Field(default_factory=list)


class AnalysisRequest(BaseModel):
    """Request to analyze code."""

    file_uri: str = Field(..., description="URI of the file to analyze")
    content: str = Field(..., description="File content")
    language_id: str = Field(..., description="Language identifier (python, typescript, etc.)")
    version: int = Field(1, description="Document version")
    project_root: str | None = Field(None, description="Project root path")
    context_files: list[str] | None = Field(None, description="Related files for context")
    analysis_types: list[str] = Field(
        default_factory=lambda: ["diagnostics", "smells", "security"],
        description="Types of analysis to perform",
    )


class AnalysisResult(BaseModel):
    """Result of code analysis."""

    file_uri: str
    version: int
    issues: list[AnalysisIssue] = Field(default_factory=list)
    suggestions: list[CodeSuggestion] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    analysis_time_ms: float = 0.0
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def error_count(self) -> int:
        return len([i for i in self.issues if i.severity == IssueSeverity.ERROR])

    @property
    def warning_count(self) -> int:
        return len([i for i in self.issues if i.severity == IssueSeverity.WARNING])

    @property
    def security_issues(self) -> list[AnalysisIssue]:
        return [i for i in self.issues if i.category == IssueCategory.SECURITY]


class DiagnosticRequest(BaseModel):
    """Request for diagnostics (lightweight analysis)."""

    file_uri: str
    content: str
    language_id: str
    version: int = 1


class DiagnosticResult(BaseModel):
    """Result of diagnostic check."""

    file_uri: str
    version: int
    diagnostics: list[AnalysisIssue] = Field(default_factory=list)


class CompletionRequest(BaseModel):
    """Request for code completion."""

    file_uri: str
    content: str
    position: Position
    language_id: str
    trigger_kind: int = 1  # 1=Invoked, 2=TriggerCharacter, 3=TriggerForIncompleteCompletions
    trigger_character: str | None = None
    context: dict[str, Any] | None = None
    max_results: int = 10


class CompletionItem(BaseModel):
    """A code completion item."""

    label: str
    kind: int = 1  # LSP CompletionItemKind
    detail: str | None = None
    documentation: str | None = None
    sort_text: str | None = None
    filter_text: str | None = None
    insert_text: str | None = None
    insert_text_format: int = 1  # 1=PlainText, 2=Snippet
    text_edit: dict[str, Any] | None = None
    additional_text_edits: list[dict[str, Any]] | None = None
    command: dict[str, Any] | None = None
    data: Any | None = None


class ChatRequest(BaseModel):
    """Request for chat/assistant interaction."""

    message: str = Field(..., description="User message")
    conversation_id: str | None = Field(None, description="Existing conversation ID")
    file_context: dict[str, Any] | None = Field(None, description="Current file context")
    selection: str | None = Field(None, description="Selected code")
    selection_range: Range | None = Field(None, description="Range of selection")
    command: str | None = Field(None, description="Explicit command (explain, fix, refactor, etc.)")


class ChatResponse(BaseModel):
    """Response from chat/assistant."""

    message: str
    conversation_id: str
    code_blocks: list[dict[str, Any]] = Field(default_factory=list)
    suggested_edits: list[dict[str, Any]] = Field(default_factory=list)
    references: list[dict[str, Any]] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)


class HoverInfo(BaseModel):
    """Information for hover tooltip."""

    contents: str  # Markdown content
    range: Range | None = None


class ExtensionCapabilities(BaseModel):
    """Capabilities supported by the extension API."""

    diagnostics: bool = True
    code_actions: bool = True
    completion: bool = True
    hover: bool = True
    document_symbols: bool = True
    workspace_symbols: bool = True
    formatting: bool = False
    rename: bool = False
    references: bool = False
    definition: bool = False
    chat: bool = True
    inline_suggestions: bool = True


class ExtensionConfig(BaseModel):
    """Configuration for extension behavior."""

    enabled: bool = True
    auto_analyze: bool = True
    analyze_on_save: bool = True
    analyze_on_type: bool = False
    analyze_delay_ms: int = 500
    max_file_size_kb: int = 500
    ignored_patterns: list[str] = Field(default_factory=lambda: [
        "**/node_modules/**",
        "**/.git/**",
        "**/dist/**",
        "**/build/**",
        "**/*.min.js",
        "**/*.min.css",
    ])
    enabled_languages: list[str] = Field(default_factory=lambda: [
        "python", "typescript", "javascript", "typescriptreact", "javascriptreact",
        "go", "rust", "java", "csharp", "cpp", "c",
    ])
    severity_threshold: IssueSeverity = IssueSeverity.INFO
    categories: list[IssueCategory] = Field(default_factory=lambda: list(IssueCategory))
    llm_model: str = "gemini-2.5-flash"
    enable_telemetry: bool = True


class SyncEvent(BaseModel):
    """Event for real-time sync."""

    type: SyncEventType
    file_uri: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
