"""Prompt Registry for versioned prompt management.

This module provides:
- Versioned prompt storage and retrieval
- A/B testing framework for prompts
- Performance tracking and analytics
- Template variable substitution
- Safe variable injection
"""

from app.services.prompts.models import (
    Prompt,
    PromptVersion,
    PromptExperiment,
    PromptAssignment,
    PromptPerformance,
)
from app.services.prompts.registry import PromptRegistry, get_prompt_registry
from app.services.prompts.variables import (
    VariableInjector,
    VariableDefinition,
    VariableType,
    InjectionResult,
    inject_variables,
)
from app.services.prompts.experiments import (
    ExperimentService,
    Experiment,
    ExperimentConfig,
    ExperimentStatus,
    PromptVariant,
    VariantType,
)

__all__ = [
    # Models
    "Prompt",
    "PromptVersion",
    "PromptExperiment",
    "PromptAssignment",
    "PromptPerformance",
    # Registry
    "PromptRegistry",
    "get_prompt_registry",
    # Variable Injection
    "VariableInjector",
    "VariableDefinition",
    "VariableType",
    "InjectionResult",
    "inject_variables",
    # A/B Testing
    "ExperimentService",
    "Experiment",
    "ExperimentConfig",
    "ExperimentStatus",
    "PromptVariant",
    "VariantType",
]
