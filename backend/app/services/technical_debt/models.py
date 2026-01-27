"""
Technical Debt Models

Data models for technical debt tracking and reporting.
"""

from enum import Enum
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class DebtCategory(str, Enum):
    """Categories of technical debt."""
    COMPLEXITY = "complexity"
    DUPLICATION = "duplication"
    COVERAGE = "coverage"
    DEPENDENCY = "dependency"
    ARCHITECTURE = "architecture"
    DOCUMENTATION = "documentation"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    CODE_SMELL = "code_smell"


class DebtSeverity(str, Enum):
    """Severity levels for technical debt."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DebtItem(BaseModel):
    """A single item of technical debt."""
    id: str
    category: DebtCategory
    severity: DebtSeverity
    title: str
    description: str
    
    # Location
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    
    # Quantification
    effort_hours: float = 0.0  # Estimated hours to fix
    interest_rate: float = 0.0  # Daily cost in hours if not fixed
    principal: float = 0.0  # Initial debt cost
    
    # Impact
    impact_score: float = 0.0  # 0-100
    affected_components: list[str] = Field(default_factory=list)
    
    # Recommendations
    fix_suggestion: Optional[str] = None
    auto_fixable: bool = False
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    detected_in_commit: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class DebtMetrics(BaseModel):
    """Aggregated technical debt metrics."""
    # Overall score (0-100, higher is better)
    health_score: float = 100.0
    
    # Total debt
    total_debt_hours: float = 0.0
    total_items: int = 0
    
    # By severity
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    
    # By category
    debt_by_category: dict[str, float] = Field(default_factory=dict)
    items_by_category: dict[str, int] = Field(default_factory=dict)
    
    # Code metrics
    average_complexity: float = 0.0
    duplication_percentage: float = 0.0
    test_coverage: float = 0.0
    documentation_coverage: float = 0.0
    
    # Maintainability index (0-100)
    maintainability_index: float = 100.0
    
    # SQALE metrics
    sqale_rating: str = "A"  # A-E rating
    sqale_debt_ratio: float = 0.0
    
    # Cost estimation
    estimated_cost_usd: float = 0.0
    developer_hourly_rate: float = 100.0


class DebtTrend(BaseModel):
    """Technical debt trend over time."""
    date: datetime
    health_score: float
    total_debt_hours: float
    total_items: int
    
    # Delta from previous
    score_delta: float = 0.0
    debt_delta: float = 0.0
    items_delta: int = 0
    
    # Contributing factors
    new_debt_items: int = 0
    resolved_debt_items: int = 0
    commits_analyzed: int = 0


class RefactoringRecommendation(BaseModel):
    """AI-generated refactoring recommendation."""
    id: str
    title: str
    description: str
    category: DebtCategory
    
    # Target
    target_files: list[str] = Field(default_factory=list)
    target_functions: list[str] = Field(default_factory=list)
    
    # Impact
    debt_reduction_hours: float = 0.0
    health_score_improvement: float = 0.0
    complexity_reduction: float = 0.0
    
    # Effort
    estimated_effort_hours: float = 0.0
    risk_level: str = "low"  # low, medium, high
    
    # Implementation
    steps: list[str] = Field(default_factory=list)
    code_examples: list[dict[str, str]] = Field(default_factory=list)
    
    # Priority
    priority_score: float = 0.0  # Based on ROI
    
    # Dependencies
    depends_on: list[str] = Field(default_factory=list)
    blocks: list[str] = Field(default_factory=list)


class QualityGateResult(BaseModel):
    """Result of a quality gate check."""
    passed: bool
    gate_name: str
    
    # Conditions checked
    conditions: list[dict[str, Any]] = Field(default_factory=list)
    failed_conditions: list[str] = Field(default_factory=list)
    
    # Metrics at check time
    metrics: DebtMetrics = Field(default_factory=DebtMetrics)
    
    # Recommendations
    recommendations: list[str] = Field(default_factory=list)


class DebtReport(BaseModel):
    """Comprehensive technical debt report."""
    project_id: str
    project_name: str
    report_date: datetime = Field(default_factory=datetime.utcnow)
    
    # Current state
    metrics: DebtMetrics = Field(default_factory=DebtMetrics)
    
    # All debt items
    debt_items: list[DebtItem] = Field(default_factory=list)
    
    # Trends
    trends: list[DebtTrend] = Field(default_factory=list)
    trend_direction: str = "stable"  # improving, stable, declining
    
    # Top issues
    top_critical_items: list[DebtItem] = Field(default_factory=list)
    hotspot_files: list[dict[str, Any]] = Field(default_factory=list)
    
    # Recommendations
    recommendations: list[RefactoringRecommendation] = Field(default_factory=list)
    
    # Quality gate
    quality_gate: Optional[QualityGateResult] = None
    
    # Summary
    executive_summary: str = ""
    action_items: list[str] = Field(default_factory=list)


class DebtConfig(BaseModel):
    """Configuration for technical debt analysis."""
    # Thresholds
    complexity_threshold: int = 15
    duplication_threshold: float = 5.0  # percentage
    coverage_threshold: float = 80.0  # percentage
    
    # Cost estimation
    developer_hourly_rate: float = 100.0
    
    # Quality gate thresholds
    max_critical_issues: int = 0
    max_high_issues: int = 5
    min_health_score: float = 70.0
    max_debt_ratio: float = 10.0
    
    # Analysis options
    include_tests: bool = False
    include_generated: bool = False
    analyze_dependencies: bool = True
    
    # Categories to include
    categories: list[DebtCategory] = Field(
        default_factory=lambda: list(DebtCategory)
    )
    
    # Exclusions
    exclude_patterns: list[str] = Field(default_factory=list)
