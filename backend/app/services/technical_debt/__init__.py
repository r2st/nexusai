"""
Technical Debt Service

Quantification, tracking, and reporting of technical debt.
"""

from .service import (
    TechnicalDebtService,
    get_technical_debt_service,
)
from .models import (
    DebtCategory,
    DebtSeverity,
    DebtItem,
    DebtMetrics,
    DebtTrend,
    DebtReport,
    RefactoringRecommendation,
    DebtConfig,
)
from .analyzers import (
    ComplexityAnalyzer,
    DuplicationAnalyzer,
    CoverageAnalyzer,
    DependencyAnalyzer,
)

__all__ = [
    # Service
    "TechnicalDebtService",
    "get_technical_debt_service",
    # Models
    "DebtCategory",
    "DebtSeverity",
    "DebtItem",
    "DebtMetrics",
    "DebtTrend",
    "DebtReport",
    "RefactoringRecommendation",
    "DebtConfig",
    # Analyzers
    "ComplexityAnalyzer",
    "DuplicationAnalyzer",
    "CoverageAnalyzer",
    "DependencyAnalyzer",
]
