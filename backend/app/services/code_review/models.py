"""Data models for Code Review service."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReviewPriority(str, Enum):
    """Priority level for review comments."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ReviewCategory(str, Enum):
    """Category of review comment."""

    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    READABILITY = "readability"
    BUG = "bug"
    STYLE = "style"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    BEST_PRACTICE = "best_practice"
    ARCHITECTURE = "architecture"


class SmellSeverity(str, Enum):
    """Severity of code smell."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class SmellType(str, Enum):
    """Type of code smell."""

    # Complexity
    LONG_METHOD = "long_method"
    COMPLEX_CONDITION = "complex_condition"
    DEEP_NESTING = "deep_nesting"
    GOD_CLASS = "god_class"

    # Duplication
    DUPLICATED_CODE = "duplicated_code"
    COPY_PASTE = "copy_paste"

    # Naming
    BAD_NAMING = "bad_naming"
    MAGIC_NUMBER = "magic_number"

    # Design
    FEATURE_ENVY = "feature_envy"
    DATA_CLUMP = "data_clump"
    PRIMITIVE_OBSESSION = "primitive_obsession"
    REFUSED_BEQUEST = "refused_bequest"

    # Security
    HARDCODED_SECRET = "hardcoded_secret"
    SQL_INJECTION = "sql_injection"
    XSS_VULNERABILITY = "xss_vulnerability"
    INSECURE_RANDOM = "insecure_random"

    # Performance
    N_PLUS_ONE = "n_plus_one"
    MEMORY_LEAK = "memory_leak"
    INEFFICIENT_LOOP = "inefficient_loop"

    # Python specific
    MUTABLE_DEFAULT = "mutable_default"
    BARE_EXCEPT = "bare_except"
    UNUSED_IMPORT = "unused_import"
    STAR_IMPORT = "star_import"
    DANGEROUS_EVAL = "dangerous_eval"

    # JavaScript/TypeScript specific
    VAR_USAGE = "var_usage"
    CONSOLE_LOG = "console_log"
    ANY_TYPE = "any_type"

    # Documentation
    TODO_COMMENT = "todo_comment"


class FileChange(BaseModel):
    """Represents a file change in a PR."""

    filename: str
    old_path: str | None = None
    new_path: str | None = None
    status: str = "modified"  # added, removed, modified, renamed
    additions: int = 0
    deletions: int = 0
    patch: str = ""
    language: str | None = None

    @property
    def is_added(self) -> bool:
        return self.status == "added"

    @property
    def is_removed(self) -> bool:
        return self.status == "removed"

    @property
    def is_renamed(self) -> bool:
        return self.status == "renamed"


class HunkLine(BaseModel):
    """A single line in a diff hunk."""

    line_number: int | None = None
    old_line_number: int | None = None
    new_line_number: int | None = None
    content: str
    type: str = "context"  # context, addition, deletion


class DiffHunk(BaseModel):
    """A hunk in a diff."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    lines: list[HunkLine] = Field(default_factory=list)


class CodeSmell(BaseModel):
    """Detected code smell."""

    type: SmellType
    severity: SmellSeverity
    file: str
    line_start: int
    line_end: int | None = None
    message: str
    suggestion: str | None = None
    code_snippet: str | None = None
    confidence: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewComment(BaseModel):
    """A review comment on a specific line."""

    file: str
    line: int
    end_line: int | None = None
    body: str
    priority: ReviewPriority = ReviewPriority.MEDIUM
    category: ReviewCategory = ReviewCategory.BEST_PRACTICE
    suggestion: str | None = None
    code_suggestion: str | None = None


class CodeReview(BaseModel):
    """Complete code review result."""

    pr_number: int
    repository: str
    summary: str
    overall_quality: float = Field(ge=0, le=10)
    comments: list[ReviewComment] = Field(default_factory=list)
    smells: list[CodeSmell] = Field(default_factory=list)
    approval_recommendation: str = "request_changes"  # approve, request_changes, comment
    metrics: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def critical_issues(self) -> list[ReviewComment]:
        return [c for c in self.comments if c.priority == ReviewPriority.CRITICAL]

    @property
    def security_issues(self) -> list[ReviewComment]:
        return [c for c in self.comments if c.category == ReviewCategory.SECURITY]


class PRInfo(BaseModel):
    """Pull request information."""

    number: int
    title: str
    description: str | None = None
    author: str
    base_branch: str
    head_branch: str
    repository: str
    url: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    labels: list[str] = Field(default_factory=list)
    files_changed: int = 0
    additions: int = 0
    deletions: int = 0


class DiffAnalysis(BaseModel):
    """Analysis result of a PR diff."""

    pr_info: PRInfo
    files: list[FileChange] = Field(default_factory=list)
    hunks_by_file: dict[str, list[DiffHunk]] = Field(default_factory=dict)
    total_additions: int = 0
    total_deletions: int = 0
    languages: list[str] = Field(default_factory=list)
    complexity_score: float = 0.0
    risk_score: float = 0.0

    @property
    def total_changes(self) -> int:
        return self.total_additions + self.total_deletions

    @property
    def is_large_pr(self) -> bool:
        return self.total_changes > 500


class WebhookEvent(BaseModel):
    """Webhook event from GitHub/GitLab."""

    event_type: str
    action: str | None = None
    repository: str
    sender: str
    payload: dict[str, Any]
    received_at: datetime = Field(default_factory=datetime.utcnow)
    signature: str | None = None

    @property
    def is_pr_event(self) -> bool:
        return self.event_type in ("pull_request", "merge_request")

    @property
    def is_push_event(self) -> bool:
        return self.event_type == "push"


class ReviewConfig(BaseModel):
    """Configuration for code review."""

    enabled: bool = True
    auto_review: bool = True
    min_file_changes: int = 1
    max_file_changes: int = 50
    ignore_patterns: list[str] = Field(default_factory=lambda: [
        "*.lock", "*.min.js", "*.min.css", "vendor/*", "node_modules/*"
    ])
    focus_areas: list[ReviewCategory] = Field(default_factory=lambda: [
        ReviewCategory.SECURITY, ReviewCategory.BUG, ReviewCategory.PERFORMANCE
    ])
    llm_model: str = "gemini-2.5-flash"
    max_comments_per_file: int = 10
    include_code_suggestions: bool = True
