"""
Model Registry

Registry of available LLM models and their capabilities.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """Supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    AWS_BEDROCK = "aws_bedrock"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"


class ModelCapability(str, Enum):
    """Model capabilities for task routing."""
    CHAT = "chat"
    COMPLETION = "completion"
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    SUMMARIZATION = "summarization"
    REASONING = "reasoning"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
    JSON_MODE = "json_mode"
    STREAMING = "streaming"
    EMBEDDINGS = "embeddings"


class TaskType(str, Enum):
    """Task types for routing decisions."""
    GENERAL_CHAT = "general_chat"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    CODE_EXPLANATION = "code_explanation"
    SUMMARIZATION = "summarization"
    ANALYSIS = "analysis"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    TRANSLATION = "translation"
    PLANNING = "planning"
    REASONING = "reasoning"


@dataclass
class ModelPricing:
    """Pricing information for a model."""
    input_cost_per_1k: float  # Cost per 1000 input tokens
    output_cost_per_1k: float  # Cost per 1000 output tokens
    currency: str = "USD"


@dataclass
class ModelLimits:
    """Rate and context limits for a model."""
    max_context_tokens: int
    max_output_tokens: int
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000


@dataclass
class ModelInfo:
    """Information about an LLM model."""
    id: str
    name: str
    provider: ModelProvider
    
    # Capabilities
    capabilities: Set[ModelCapability] = field(default_factory=set)
    
    # Performance characteristics
    latency_tier: str = "medium"  # fast, medium, slow
    quality_tier: str = "medium"  # low, medium, high, premium
    
    # Limits
    limits: Optional[ModelLimits] = None
    
    # Pricing
    pricing: Optional[ModelPricing] = None
    
    # Task affinities (task -> score 0-1)
    task_scores: Dict[TaskType, float] = field(default_factory=dict)
    
    # Status
    is_available: bool = True
    deprecation_date: Optional[str] = None
    
    # Configuration
    default_params: Dict[str, Any] = field(default_factory=dict)


# Pre-defined model configurations
OPENAI_MODELS = {
    "gpt-4o": ModelInfo(
        id="gpt-4o",
        name="GPT-4o",
        provider=ModelProvider.OPENAI,
        capabilities={
            ModelCapability.CHAT,
            ModelCapability.CODE_GENERATION,
            ModelCapability.CODE_ANALYSIS,
            ModelCapability.REASONING,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.JSON_MODE,
            ModelCapability.STREAMING,
        },
        latency_tier="fast",
        quality_tier="premium",
        limits=ModelLimits(
            max_context_tokens=128000,
            max_output_tokens=16384,
            requests_per_minute=500,
            tokens_per_minute=800000,
        ),
        pricing=ModelPricing(
            input_cost_per_1k=0.0025,
            output_cost_per_1k=0.01,
        ),
        task_scores={
            TaskType.GENERAL_CHAT: 0.95,
            TaskType.CODE_GENERATION: 0.95,
            TaskType.CODE_REVIEW: 0.95,
            TaskType.REASONING: 0.95,
            TaskType.ANALYSIS: 0.9,
        },
    ),
    "gpt-4o-mini": ModelInfo(
        id="gpt-4o-mini",
        name="GPT-4o Mini",
        provider=ModelProvider.OPENAI,
        capabilities={
            ModelCapability.CHAT,
            ModelCapability.CODE_GENERATION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.JSON_MODE,
            ModelCapability.STREAMING,
        },
        latency_tier="fast",
        quality_tier="high",
        limits=ModelLimits(
            max_context_tokens=128000,
            max_output_tokens=16384,
            requests_per_minute=1000,
            tokens_per_minute=2000000,
        ),
        pricing=ModelPricing(
            input_cost_per_1k=0.00015,
            output_cost_per_1k=0.0006,
        ),
        task_scores={
            TaskType.GENERAL_CHAT: 0.85,
            TaskType.CODE_GENERATION: 0.8,
            TaskType.CLASSIFICATION: 0.9,
            TaskType.EXTRACTION: 0.85,
        },
    ),
    "o1": ModelInfo(
        id="o1",
        name="O1",
        provider=ModelProvider.OPENAI,
        capabilities={
            ModelCapability.CHAT,
            ModelCapability.REASONING,
            ModelCapability.CODE_ANALYSIS,
        },
        latency_tier="slow",
        quality_tier="premium",
        limits=ModelLimits(
            max_context_tokens=200000,
            max_output_tokens=100000,
            requests_per_minute=100,
        ),
        pricing=ModelPricing(
            input_cost_per_1k=0.015,
            output_cost_per_1k=0.06,
        ),
        task_scores={
            TaskType.REASONING: 1.0,
            TaskType.PLANNING: 0.95,
            TaskType.CODE_REVIEW: 0.9,
            TaskType.ANALYSIS: 0.95,
        },
    ),
}

ANTHROPIC_MODELS = {
    "claude-sonnet-4-20250514": ModelInfo(
        id="claude-sonnet-4-20250514",
        name="Claude Sonnet 4",
        provider=ModelProvider.ANTHROPIC,
        capabilities={
            ModelCapability.CHAT,
            ModelCapability.CODE_GENERATION,
            ModelCapability.CODE_ANALYSIS,
            ModelCapability.REASONING,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        },
        latency_tier="medium",
        quality_tier="premium",
        limits=ModelLimits(
            max_context_tokens=200000,
            max_output_tokens=64000,
            requests_per_minute=100,
        ),
        pricing=ModelPricing(
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.015,
        ),
        task_scores={
            TaskType.CODE_GENERATION: 1.0,
            TaskType.CODE_REVIEW: 1.0,
            TaskType.CODE_EXPLANATION: 0.95,
            TaskType.REASONING: 0.95,
            TaskType.ANALYSIS: 0.95,
        },
    ),
    "claude-3-5-haiku-20241022": ModelInfo(
        id="claude-3-5-haiku-20241022",
        name="Claude 3.5 Haiku",
        provider=ModelProvider.ANTHROPIC,
        capabilities={
            ModelCapability.CHAT,
            ModelCapability.CODE_GENERATION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        },
        latency_tier="fast",
        quality_tier="high",
        limits=ModelLimits(
            max_context_tokens=200000,
            max_output_tokens=8192,
            requests_per_minute=500,
        ),
        pricing=ModelPricing(
            input_cost_per_1k=0.0008,
            output_cost_per_1k=0.004,
        ),
        task_scores={
            TaskType.GENERAL_CHAT: 0.85,
            TaskType.CODE_GENERATION: 0.8,
            TaskType.CLASSIFICATION: 0.9,
            TaskType.EXTRACTION: 0.85,
        },
    ),
}


class ModelRegistry:
    """
    Registry of available LLM models.
    
    Features:
    - Model discovery
    - Capability filtering
    - Task-based selection
    - Availability tracking
    """
    
    def __init__(self):
        self._models: Dict[str, ModelInfo] = {}
        
        # Register built-in models
        self._models.update(OPENAI_MODELS)
        self._models.update(ANTHROPIC_MODELS)
    
    def register(self, model: ModelInfo) -> None:
        """Register a model."""
        self._models[model.id] = model
        logger.info(f"Registered model: {model.id} ({model.provider.value})")
    
    def unregister(self, model_id: str) -> bool:
        """Unregister a model."""
        if model_id in self._models:
            del self._models[model_id]
            return True
        return False
    
    def get(self, model_id: str) -> Optional[ModelInfo]:
        """Get a model by ID."""
        return self._models.get(model_id)
    
    def list_all(self, available_only: bool = True) -> List[ModelInfo]:
        """List all models."""
        models = list(self._models.values())
        if available_only:
            models = [m for m in models if m.is_available]
        return models
    
    def list_by_provider(
        self,
        provider: ModelProvider,
        available_only: bool = True,
    ) -> List[ModelInfo]:
        """List models by provider."""
        models = [m for m in self._models.values() if m.provider == provider]
        if available_only:
            models = [m for m in models if m.is_available]
        return models
    
    def list_by_capability(
        self,
        capability: ModelCapability,
        available_only: bool = True,
    ) -> List[ModelInfo]:
        """List models with a specific capability."""
        models = [m for m in self._models.values() if capability in m.capabilities]
        if available_only:
            models = [m for m in models if m.is_available]
        return models
    
    def find_best_for_task(
        self,
        task: TaskType,
        required_capabilities: Optional[Set[ModelCapability]] = None,
        max_cost_per_1k: Optional[float] = None,
        latency_tier: Optional[str] = None,
    ) -> List[ModelInfo]:
        """
        Find the best models for a task.
        
        Returns models sorted by task score (highest first).
        """
        candidates = []
        
        for model in self._models.values():
            if not model.is_available:
                continue
            
            # Check required capabilities
            if required_capabilities:
                if not required_capabilities.issubset(model.capabilities):
                    continue
            
            # Check cost limit
            if max_cost_per_1k and model.pricing:
                avg_cost = (model.pricing.input_cost_per_1k + model.pricing.output_cost_per_1k) / 2
                if avg_cost > max_cost_per_1k:
                    continue
            
            # Check latency tier
            if latency_tier and model.latency_tier != latency_tier:
                continue
            
            # Get task score
            score = model.task_scores.get(task, 0.5)
            candidates.append((model, score))
        
        # Sort by score
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return [m for m, _ in candidates]
    
    def set_availability(self, model_id: str, available: bool) -> None:
        """Set model availability."""
        if model_id in self._models:
            self._models[model_id].is_available = available


# Global registry
model_registry = ModelRegistry()
