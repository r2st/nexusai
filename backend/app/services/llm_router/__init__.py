"""
LLM Model Router Service

Intelligent routing of LLM requests across multiple providers:
- Task-based routing (summarization, code gen, analysis)
- Automatic fallbacks
- Semantic caching
- Cost tracking
- Load balancing
"""

from .engine import ModelRouter, RoutingConfig, RouteResult
from .registry import ModelRegistry, ModelInfo, ModelProvider
from .cache import SemanticCache
from .cost import CostTracker, CostEstimate

__all__ = [
    # Router
    "ModelRouter",
    "RoutingConfig",
    "RouteResult",
    # Registry
    "ModelRegistry",
    "ModelInfo",
    "ModelProvider",
    # Cache
    "SemanticCache",
    # Cost
    "CostTracker",
    "CostEstimate",
]
