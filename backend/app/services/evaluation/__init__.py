"""LLM Evaluation Framework.

This module provides:
- Test set management for evaluation
- Quality metrics computation
- Automated evaluation runs
- Regression detection
- CI integration support
"""

from app.services.evaluation.models import (
    TestSet,
    TestCase,
    EvalRun,
    EvalResult,
    QualityMetric,
)
from app.services.evaluation.evaluator import Evaluator, get_evaluator
from app.services.evaluation.runner import EvalRunner, get_eval_runner

__all__ = [
    # Models
    "TestSet",
    "TestCase",
    "EvalRun",
    "EvalResult",
    "QualityMetric",
    # Evaluator
    "Evaluator",
    "get_evaluator",
    # Runner
    "EvalRunner",
    "get_eval_runner",
]
