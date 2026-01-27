"""LLM Gateway Service - Main service class."""

import asyncio
import time
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

import structlog

from app.services.llm_gateway.config import (
    GatewayConfig,
    RouteStrategy,
    get_gateway_config,
)
from app.services.llm_gateway.cost_tracker import CostTracker
from app.services.llm_gateway.models import (
    GatewayStatus,
    HallucinationCheckResult,
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
    Message,
    MessageRole,
    ProviderStatus,
    RateLimitInfo,
    UsageStats,
)
from app.services.llm_gateway.router import ProviderRouter
from app.services.providers.base import (
    BaseAIProvider,
    ChatMessage,
    ChatResponse,
    MessageRole as ProviderMessageRole,
    ProviderConfig,
    TokenUsage,
)

logger = structlog.get_logger()

# Try to import Phoenix for hallucination detection
try:
    from app.services.observability.phoenix_client import (
        PhoenixClient,
        HallucinationResult,
        get_phoenix_client,
    )
    from app.services.observability.config import get_observability_config
    PHOENIX_AVAILABLE = True
except ImportError:
    PHOENIX_AVAILABLE = False
    PhoenixClient = None
    get_phoenix_client = None
    get_observability_config = None


class LLMGateway:
    """
    Unified LLM Gateway with intelligent routing, failover, and cost tracking.

    Features:
    - Multi-provider support with automatic failover
    - Intelligent routing strategies
    - Cost tracking and budget enforcement
    - Rate limiting
    - Request metrics and health monitoring
    """

    def __init__(self, config: GatewayConfig | None = None):
        self.config = config or get_gateway_config()
        self.router = ProviderRouter(self.config)
        self.cost_tracker = CostTracker(self.config)
        self._providers: dict[str, BaseAIProvider] = {}
        self._rate_limits: dict[str, list[datetime]] = {}
        self._phoenix_client: PhoenixClient | None = None
        self._observability_config = None

        # Initialize providers
        self._init_providers()

        # Initialize Phoenix for hallucination detection
        if PHOENIX_AVAILABLE:
            self._observability_config = get_observability_config()

    def _init_providers(self):
        """Initialize LLM provider instances."""
        from app.core.config import settings

        # Import providers dynamically based on configuration
        provider_initializers = {
            "openai": self._init_openai,
            "anthropic": self._init_anthropic,
            "google": self._init_google,
            "ollama": self._init_ollama,
            "groq": self._init_groq,
            "mistral": self._init_mistral,
        }

        for provider_config in self.config.providers:
            if provider_config.enabled and provider_config.name in provider_initializers:
                try:
                    provider = provider_initializers[provider_config.name]()
                    if provider:
                        self._providers[provider_config.name] = provider
                        logger.info(
                            "Initialized LLM provider",
                            provider=provider_config.name,
                            models=provider_config.models,
                        )
                except Exception as e:
                    logger.warning(
                        "Failed to initialize provider",
                        provider=provider_config.name,
                        error=str(e),
                    )

    def _init_openai(self) -> BaseAIProvider | None:
        """Initialize OpenAI provider."""
        from app.core.config import settings

        if not getattr(settings, "OPENAI_API_KEY", None):
            return None

        from app.services.llm_gateway.providers.openai import OpenAIProvider

        return OpenAIProvider(
            ProviderConfig(
                api_key=settings.OPENAI_API_KEY,
                default_model=settings.OPENAI_DEFAULT_MODEL,
            )
        )

    def _init_anthropic(self) -> BaseAIProvider | None:
        """Initialize Anthropic provider."""
        from app.core.config import settings

        if not getattr(settings, "ANTHROPIC_API_KEY", None):
            return None

        from app.services.llm_gateway.providers.anthropic import AnthropicProvider

        return AnthropicProvider(
            ProviderConfig(
                api_key=settings.ANTHROPIC_API_KEY,
                default_model=settings.ANTHROPIC_DEFAULT_MODEL,
            )
        )

    def _init_google(self) -> BaseAIProvider | None:
        """Initialize Google provider."""
        from app.core.config import settings

        if not getattr(settings, "GOOGLE_API_KEY", None):
            return None

        from app.services.llm_gateway.providers.google import GoogleProvider

        return GoogleProvider(
            ProviderConfig(
                api_key=settings.GOOGLE_API_KEY,
                default_model=settings.GOOGLE_DEFAULT_MODEL,
            )
        )

    def _init_ollama(self) -> BaseAIProvider | None:
        """Initialize Ollama provider."""
        from app.core.config import settings

        ollama_url = getattr(settings, "OLLAMA_BASE_URL", None)
        if not ollama_url:
            return None

        from app.services.llm_gateway.providers.ollama import OllamaProvider

        return OllamaProvider(
            ProviderConfig(
                api_base=ollama_url,
                default_model=settings.OLLAMA_DEFAULT_MODEL,
            )
        )

    def _init_groq(self) -> BaseAIProvider | None:
        """Initialize Groq provider."""
        from app.core.config import settings

        if not getattr(settings, "GROQ_API_KEY", None):
            return None

        from app.services.providers.groq import GroqProvider

        return GroqProvider(
            ProviderConfig(
                api_key=settings.GROQ_API_KEY,
                default_model=settings.GROQ_DEFAULT_MODEL,
            )
        )

    def _init_mistral(self) -> BaseAIProvider | None:
        """Initialize Mistral provider."""
        from app.core.config import settings

        if not getattr(settings, "MISTRAL_API_KEY", None):
            return None

        from app.services.providers.mistral import MistralProvider

        return MistralProvider(
            ProviderConfig(
                api_key=settings.MISTRAL_API_KEY,
                default_model=settings.MISTRAL_DEFAULT_MODEL,
            )
        )

    def _check_rate_limit(self, user_id: str | None) -> RateLimitInfo:
        """Check rate limit for user."""
        if not user_id:
            return RateLimitInfo(is_limited=False)

        now = datetime.utcnow()
        minute_ago = now.replace(second=0, microsecond=0)

        # Get user's requests in the last minute
        if user_id not in self._rate_limits:
            self._rate_limits[user_id] = []

        # Clean old entries
        self._rate_limits[user_id] = [
            t for t in self._rate_limits[user_id] if t > minute_ago
        ]

        requests_count = len(self._rate_limits[user_id])
        limit = self.config.user_rate_limit_per_minute

        return RateLimitInfo(
            user_id=user_id,
            requests_remaining=max(0, limit - requests_count),
            requests_limit=limit,
            is_limited=requests_count >= limit,
        )

    def _record_rate_limit(self, user_id: str | None):
        """Record a request for rate limiting."""
        if user_id:
            if user_id not in self._rate_limits:
                self._rate_limits[user_id] = []
            self._rate_limits[user_id].append(datetime.utcnow())

    def _convert_messages(self, messages: list[Message]) -> list[ChatMessage]:
        """Convert gateway messages to provider messages."""
        return [
            ChatMessage(
                role=ProviderMessageRole(msg.role.value),
                content=msg.content,
                name=msg.name,
                tool_calls=msg.tool_calls,
                tool_call_id=msg.tool_call_id,
            )
            for msg in messages
        ]

    async def _get_phoenix_client(self) -> PhoenixClient | None:
        """Get or initialize Phoenix client for hallucination detection."""
        if not PHOENIX_AVAILABLE:
            return None

        if self._phoenix_client is None:
            try:
                self._phoenix_client = await get_phoenix_client(self._observability_config)
            except Exception as e:
                logger.warning("Failed to initialize Phoenix client", error=str(e))
                return None

        return self._phoenix_client

    async def _check_hallucination(
        self,
        query: str,
        response: str,
        context: list[str] | None = None,
    ) -> HallucinationCheckResult:
        """
        Check a response for hallucinations.

        Args:
            query: The user's query
            response: The LLM response
            context: Optional RAG context documents

        Returns:
            HallucinationCheckResult with detection details
        """
        result = HallucinationCheckResult(checked=False)

        try:
            client = await self._get_phoenix_client()
            if not client:
                return result

            # Check if hallucination detection is enabled
            if not self._observability_config or not self._observability_config.hallucination_detection_enabled:
                return result

            # Perform hallucination check
            hal_result = await client.check_hallucination(
                query=query,
                response=response,
                context=context,
            )

            result = HallucinationCheckResult(
                checked=True,
                is_hallucination=hal_result.is_hallucination,
                hallucination_score=hal_result.hallucination_score,
                grounding_score=hal_result.grounding_score,
                relevance_score=hal_result.relevance_score,
                factuality_score=hal_result.factuality_score,
                confidence=hal_result.confidence,
                explanation=hal_result.explanation,
                issues=hal_result.detected_issues,
            )

            logger.debug(
                "Hallucination check completed",
                is_hallucination=result.is_hallucination,
                score=result.hallucination_score,
            )

        except Exception as e:
            logger.warning("Hallucination check failed", error=str(e))
            result.issues.append(f"Check failed: {str(e)}")

        return result

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """
        Complete a chat request with automatic routing and failover.

        Args:
            request: The LLM request

        Returns:
            LLMResponse with the completion
        """
        start_time = time.time()

        # Check rate limit
        rate_info = self._check_rate_limit(request.user_id)
        if rate_info.is_limited:
            raise Exception(f"Rate limit exceeded. Try again in 60 seconds.")

        # Check budget
        within_budget, reason = self.cost_tracker.check_budget(request.user_id)
        if not within_budget:
            raise Exception(f"Budget exceeded: {reason}")

        # Route to provider
        provider_name, model = self.router.select_provider(
            model=request.model,
            preferred_provider=request.provider,
        )

        provider = self._providers.get(provider_name)
        if not provider:
            raise Exception(f"Provider {provider_name} not available")

        # Attempt request with failover
        attempted_providers = []
        last_error = None

        while len(attempted_providers) < self.config.max_retries:
            try:
                # Make the request
                messages = self._convert_messages(request.messages)
                response = await provider.chat(
                    messages=messages,
                    model=model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    tools=request.tools,
                )

                # Calculate timing
                latency_ms = (time.time() - start_time) * 1000

                # Record metrics
                self.router.record_request(
                    provider=provider_name,
                    latency_ms=latency_ms,
                    success=True,
                )
                self._record_rate_limit(request.user_id)

                # Calculate and record cost
                usage = response.usage or TokenUsage()
                cost_entry = self.cost_tracker.record_usage(
                    request_id=str(request.request_id),
                    user_id=request.user_id,
                    tenant_id=request.tenant_id,
                    model=model,
                    provider=provider_name,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                )

                # Perform hallucination check if requested
                hallucination_check = None
                if request.check_hallucination:
                    # Extract query from messages
                    query = ""
                    for msg in reversed(request.messages):
                        if msg.role == MessageRole.USER:
                            query = msg.content
                            break

                    hallucination_check = await self._check_hallucination(
                        query=query,
                        response=response.content,
                        context=request.rag_context,
                    )

                return LLMResponse(
                    request_id=request.request_id,
                    model=model,
                    provider=provider_name,
                    content=response.content,
                    role=MessageRole(response.role.value),
                    finish_reason=response.finish_reason,
                    tool_calls=response.tool_calls,
                    usage=UsageStats(
                        prompt_tokens=usage.prompt_tokens,
                        completion_tokens=usage.completion_tokens,
                        total_tokens=usage.total_tokens,
                        cost_usd=cost_entry.cost_usd,
                    ),
                    latency_ms=latency_ms,
                    metadata=request.metadata,
                    hallucination_check=hallucination_check,
                )

            except Exception as e:
                last_error = e
                attempted_providers.append(provider_name)

                # Record failure
                self.router.record_request(
                    provider=provider_name,
                    latency_ms=(time.time() - start_time) * 1000,
                    success=False,
                    error=str(e),
                )

                logger.warning(
                    "Provider request failed",
                    provider=provider_name,
                    error=str(e),
                    attempt=len(attempted_providers),
                )

                # Check if we should failover
                if self.router.should_failover(provider_name, e):
                    failover = self.router.get_failover_provider(
                        provider_name, model, attempted_providers
                    )
                    if failover:
                        provider_name, model = failover
                        provider = self._providers.get(provider_name)
                        if provider:
                            logger.info(
                                "Failing over to provider",
                                from_provider=attempted_providers[-1],
                                to_provider=provider_name,
                            )
                            continue

                # No more failover options
                break

        raise Exception(f"All providers failed. Last error: {last_error}")

    async def stream(self, request: LLMRequest) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Stream a chat completion.

        Args:
            request: The LLM request (stream=True recommended)

        Yields:
            LLMStreamChunk for each token/chunk
        """
        start_time = time.time()

        # Check rate limit
        rate_info = self._check_rate_limit(request.user_id)
        if rate_info.is_limited:
            raise Exception("Rate limit exceeded")

        # Route to provider
        provider_name, model = self.router.select_provider(
            model=request.model,
            preferred_provider=request.provider,
        )

        provider = self._providers.get(provider_name)
        if not provider:
            raise Exception(f"Provider {provider_name} not available")

        # Stream the response
        messages = self._convert_messages(request.messages)
        content_buffer = ""

        try:
            async for chunk in provider.chat_stream(
                messages=messages,
                model=model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=request.tools,
            ):
                content_buffer += chunk
                yield LLMStreamChunk(
                    request_id=request.request_id,
                    content=chunk,
                    is_final=False,
                )

            # Final chunk with usage
            latency_ms = (time.time() - start_time) * 1000

            # Estimate tokens for streaming (actual tracking requires provider support)
            estimated_prompt_tokens = sum(len(m.content.split()) * 1.3 for m in request.messages)
            estimated_completion_tokens = len(content_buffer.split()) * 1.3

            cost_entry = self.cost_tracker.record_usage(
                request_id=str(request.request_id),
                user_id=request.user_id,
                tenant_id=request.tenant_id,
                model=model,
                provider=provider_name,
                prompt_tokens=int(estimated_prompt_tokens),
                completion_tokens=int(estimated_completion_tokens),
            )

            self.router.record_request(
                provider=provider_name,
                latency_ms=latency_ms,
                success=True,
            )
            self._record_rate_limit(request.user_id)

            yield LLMStreamChunk(
                request_id=request.request_id,
                content="",
                is_final=True,
                usage=UsageStats(
                    prompt_tokens=int(estimated_prompt_tokens),
                    completion_tokens=int(estimated_completion_tokens),
                    total_tokens=int(estimated_prompt_tokens + estimated_completion_tokens),
                    cost_usd=cost_entry.cost_usd,
                ),
            )

        except Exception as e:
            self.router.record_request(
                provider=provider_name,
                latency_ms=(time.time() - start_time) * 1000,
                success=False,
                error=str(e),
            )
            raise

    async def get_status(self) -> GatewayStatus:
        """Get gateway status."""
        providers = self.router.get_all_provider_status()
        cache_hits = 0  # TODO: Implement when cache is added
        cache_total = 1  # Avoid division by zero

        return GatewayStatus(
            healthy=any(p.health.value == "healthy" for p in providers),
            providers=providers,
            total_requests_today=len(self.cost_tracker.entries),
            total_cost_today_usd=self.cost_tracker.get_today_cost(),
            cache_hit_rate=cache_hits / cache_total,
            avg_latency_ms=sum(
                p.avg_latency_ms for p in providers
            ) / max(len(providers), 1),
        )

    def list_models(self) -> dict[str, list[str]]:
        """List available models by provider."""
        result = {}
        for provider_name, provider in self._providers.items():
            result[provider_name] = provider.list_models()
        return result

    async def health_check(self) -> dict[str, bool]:
        """Check health of all providers."""
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception:
                results[name] = False
        return results

    async def check_response_hallucination(
        self,
        query: str,
        response: str,
        context: list[str] | None = None,
    ) -> HallucinationCheckResult:
        """
        Check a response for hallucinations (standalone method).

        This can be used to check any response, not just ones generated
        through this gateway.

        Args:
            query: The user's query/question
            response: The response to check
            context: Optional context documents for RAG grounding

        Returns:
            HallucinationCheckResult with detection details
        """
        return await self._check_hallucination(query, response, context)

    async def complete_with_hallucination_check(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """
        Complete a request with mandatory hallucination checking.

        This is a convenience method that ensures hallucination checking
        is always performed regardless of the request settings.

        Args:
            request: The LLM request

        Returns:
            LLMResponse with hallucination check results
        """
        # Force hallucination checking
        request.check_hallucination = True
        return await self.complete(request)

    def get_hallucination_metrics(self) -> dict[str, Any]:
        """
        Get hallucination detection metrics.

        Returns:
            Dictionary with hallucination metrics
        """
        if not self._phoenix_client:
            return {"status": "Phoenix client not initialized"}

        return self._phoenix_client.get_metrics()


# Global gateway instance
_gateway: LLMGateway | None = None


def get_gateway() -> LLMGateway:
    """Get the global gateway instance."""
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway
