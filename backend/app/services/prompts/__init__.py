"""Prompt Registry for versioned prompt management.

This module provides:
- Versioned prompt storage and retrieval
- A/B testing framework for prompts
- Performance tracking and analytics
- Template variable substitution
- Safe variable injection
- Langfuse prompt management integration
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
from app.services.prompts.langfuse_manager import (
    LangfusePromptManager,
    get_langfuse_prompt_manager,
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
    # Langfuse Prompt Management
    "LangfusePromptManager",
    "get_langfuse_prompt_manager",
]
