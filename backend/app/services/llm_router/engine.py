"""
Model Router Engine

Intelligent routing of LLM requests.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, List, Optional, Set
import logging

from .registry import (
    ModelRegistry,
    ModelInfo,
    ModelProvider,
    ModelCapability,
    TaskType,
    model_registry,
)
from .cache import SemanticCache
from .cost import CostTracker, CostEstimate

logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    """Routing strategies."""
    BEST_QUALITY = "best_quality"
    LOWEST_COST = "lowest_cost"
    LOWEST_LATENCY = "lowest_latency"
    BALANCED = "balanced"
    ROUND_ROBIN = "round_robin"


@dataclass
class RoutingConfig:
    """Configuration for routing decisions."""
    # Strategy
    strategy: RoutingStrategy = RoutingStrategy.BALANCED
    
    # Preferences
    preferred_providers: List[ModelProvider] = field(default_factory=list)
    excluded_providers: List[ModelProvider] = field(default_factory=list)
    preferred_models: List[str] = field(default_factory=list)
    excluded_models: List[str] = field(default_factory=list)
    
    # Constraints
    max_cost_per_request: Optional[float] = None
    max_latency_ms: Optional[int] = None
    required_capabilities: Set[ModelCapability] = field(default_factory=set)
    
    # Fallback
    enable_fallback: bool = True
    max_fallback_attempts: int = 3
    fallback_delay_ms: int = 100
    
    # Caching
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600


@dataclass
class RouteResult:
    """Result of a routing decision."""
    model: ModelInfo
    fallback_models: List[ModelInfo]
    cached: bool = False
    cache_key: Optional[str] = None
    estimated_cost: Optional[CostEstimate] = None
    routing_time_ms: int = 0


@dataclass
class RequestContext:
    """Context for a routing request."""
    task_type: TaskType
    input_text: str
    input_tokens: int
    expected_output_tokens: int = 1000
    
    # User/tenant context
    tenant_id: str = ""
    user_id: str = ""
    
    # Request metadata
    request_id: str = ""
    priority: str = "normal"  # low, normal, high
    
    # Hints
    quality_preference: str = "balanced"  # economy, balanced, premium


class ModelRouter:
    """
    Intelligent LLM request router.
    
    Features:
    - Task-based routing
    - Multi-strategy support
    - Automatic fallbacks
    - Semantic caching
    - Cost tracking
    - Load balancing
    """
    
    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        cache: Optional[SemanticCache] = None,
        cost_tracker: Optional[CostTracker] = None,
    ):
        self.registry = registry or model_registry
        self.cache = cache
        self.cost_tracker = cost_tracker
        
        # State
        self._model_health: Dict[str, float] = {}  # model_id -> health score 0-1
        self._round_robin_index: Dict[TaskType, int] = {}
        
        # Callbacks
        self._on_route_selected: List[Callable] = []
        self._on_fallback: List[Callable] = []
    
    async def route(
        self,
        context: RequestContext,
        config: Optional[RoutingConfig] = None,
    ) -> RouteResult:
        """
        Route a request to the best model.
        
        Args:
            context: Request context
            config: Routing configuration
            
        Returns:
            RouteResult with selected model and fallbacks
        """
        import time
        start_time = time.time()
        
        cfg = config or RoutingConfig()
        
        # Check cache
        cache_key = None
        if cfg.enable_cache and self.cache:
            cache_key = self.cache.generate_key(
                context.input_text,
                context.task_type.value,
            )
            cached = await self.cache.get(cache_key)
            if cached:
                # Find the model used for cached response
                model = self.registry.get(cached.get("model_id", ""))
                if model:
                    return RouteResult(
                        model=model,
                        fallback_models=[],
                        cached=True,
                        cache_key=cache_key,
                        routing_time_ms=int((time.time() - start_time) * 1000),
                    )
        
        # Get candidate models
        candidates = self._get_candidates(context, cfg)
        
        if not candidates:
            raise ValueError(f"No models available for task: {context.task_type}")
        
        # Select primary model based on strategy
        primary = self._select_model(candidates, context, cfg)
        
        # Select fallback models
        fallbacks = self._select_fallbacks(candidates, primary, cfg)
        
        # Estimate cost
        cost_estimate = None
        if self.cost_tracker and primary.pricing:
            cost_estimate = self.cost_tracker.estimate(
                primary,
                context.input_tokens,
                context.expected_output_tokens,
            )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        result = RouteResult(
            model=primary,
            fallback_models=fallbacks,
            cached=False,
            cache_key=cache_key,
            estimated_cost=cost_estimate,
            routing_time_ms=elapsed_ms,
        )
        
        # Notify callbacks
        for callback in self._on_route_selected:
            try:
                await callback(context, result)
            except Exception as e:
                logger.warning(f"Route callback error: {e}")
        
        return result
    
    def _get_candidates(
        self,
        context: RequestContext,
        config: RoutingConfig,
    ) -> List[ModelInfo]:
        """Get candidate models for the request."""
        # Start with models for the task
        candidates = self.registry.find_best_for_task(
            context.task_type,
            required_capabilities=config.required_capabilities,
        )
        
        # Apply exclusions
        if config.excluded_providers:
            candidates = [
                m for m in candidates
                if m.provider not in config.excluded_providers
            ]
        
        if config.excluded_models:
            candidates = [
                m for m in candidates
                if m.id not in config.excluded_models
            ]
        
        # Apply preferences (boost score)
        if config.preferred_providers:
            candidates.sort(
                key=lambda m: (
                    0 if m.provider in config.preferred_providers else 1,
                    -m.task_scores.get(context.task_type, 0),
                )
            )
        
        if config.preferred_models:
            # Move preferred models to front
            preferred = [m for m in candidates if m.id in config.preferred_models]
            others = [m for m in candidates if m.id not in config.preferred_models]
            candidates = preferred + others
        
        # Filter by health
        candidates = [
            m for m in candidates
            if self._model_health.get(m.id, 1.0) > 0.5
        ]
        
        return candidates
    
    def _select_model(
        self,
        candidates: List[ModelInfo],
        context: RequestContext,
        config: RoutingConfig,
    ) -> ModelInfo:
        """Select the primary model."""
        if not candidates:
            raise ValueError("No candidates available")
        
        if config.strategy == RoutingStrategy.BEST_QUALITY:
            # Select highest quality model
            return max(candidates, key=lambda m: (
                {"low": 0, "medium": 1, "high": 2, "premium": 3}.get(m.quality_tier, 1),
                m.task_scores.get(context.task_type, 0),
            ))
        
        elif config.strategy == RoutingStrategy.LOWEST_COST:
            # Select cheapest model
            return min(candidates, key=lambda m: (
                (m.pricing.input_cost_per_1k + m.pricing.output_cost_per_1k) / 2
                if m.pricing else float("inf")
            ))
        
        elif config.strategy == RoutingStrategy.LOWEST_LATENCY:
            # Select fastest model
            latency_order = {"fast": 0, "medium": 1, "slow": 2}
            return min(candidates, key=lambda m: latency_order.get(m.latency_tier, 1))
        
        elif config.strategy == RoutingStrategy.ROUND_ROBIN:
            # Round-robin across candidates
            idx = self._round_robin_index.get(context.task_type, 0)
            model = candidates[idx % len(candidates)]
            self._round_robin_index[context.task_type] = idx + 1
            return model
        
        else:  # BALANCED
            # Score based on multiple factors
            def score(m: ModelInfo) -> float:
                task_score = m.task_scores.get(context.task_type, 0.5)
                quality_score = {"low": 0.25, "medium": 0.5, "high": 0.75, "premium": 1.0}.get(m.quality_tier, 0.5)
                latency_score = {"fast": 1.0, "medium": 0.6, "slow": 0.3}.get(m.latency_tier, 0.5)
                health_score = self._model_health.get(m.id, 1.0)
                
                # Cost factor (lower is better)
                cost_factor = 1.0
                if m.pricing:
                    avg_cost = (m.pricing.input_cost_per_1k + m.pricing.output_cost_per_1k) / 2
                    cost_factor = max(0.1, 1.0 - (avg_cost / 0.02))  # Normalize to ~$0.02
                
                # Preference boost
                preference_boost = 1.2 if context.quality_preference == "premium" and m.quality_tier == "premium" else 1.0
                if context.quality_preference == "economy" and m.pricing:
                    preference_boost = 1.5 if m.pricing.input_cost_per_1k < 0.001 else 1.0
                
                return (
                    task_score * 0.3 +
                    quality_score * 0.25 +
                    latency_score * 0.15 +
                    cost_factor * 0.2 +
                    health_score * 0.1
                ) * preference_boost
            
            return max(candidates, key=score)
    
    def _select_fallbacks(
        self,
        candidates: List[ModelInfo],
        primary: ModelInfo,
        config: RoutingConfig,
    ) -> List[ModelInfo]:
        """Select fallback models."""
        if not config.enable_fallback:
            return []
        
        # Get models from different providers for diversity
        fallbacks = []
        used_providers = {primary.provider}
        
        for model in candidates:
            if model.id == primary.id:
                continue
            
            # Prefer different providers for fallbacks
            if model.provider not in used_providers:
                fallbacks.append(model)
                used_providers.add(model.provider)
            elif len(fallbacks) < config.max_fallback_attempts:
                fallbacks.append(model)
            
            if len(fallbacks) >= config.max_fallback_attempts:
                break
        
        return fallbacks
    
    def report_success(self, model_id: str, latency_ms: int) -> None:
        """Report successful model call."""
        current = self._model_health.get(model_id, 1.0)
        # Increase health slightly
        self._model_health[model_id] = min(1.0, current + 0.05)
    
    def report_failure(self, model_id: str, error: str) -> None:
        """Report failed model call."""
        current = self._model_health.get(model_id, 1.0)
        # Decrease health
        self._model_health[model_id] = max(0.0, current - 0.2)
        logger.warning(f"Model {model_id} health decreased: {error}")
    
    def on_route_selected(self, callback: Callable) -> None:
        """Register callback for route selection."""
        self._on_route_selected.append(callback)
    
    def on_fallback(self, callback: Callable) -> None:
        """Register callback for fallback events."""
        self._on_fallback.append(callback)
