"""AI Provider Manager for unified access to all providers."""

from typing import Any

import structlog

from app.core.config import settings
from app.services.providers.base import BaseAIProvider, ProviderConfig
from app.services.providers.azure import AzureOpenAIProvider
from app.services.providers.bedrock import AWSBedrockProvider
from app.services.providers.vertex import GoogleVertexProvider
from app.services.providers.groq import GroqProvider
from app.services.providers.mistral import MistralProvider
from app.services.providers.cohere import CohereProvider
from app.services.providers.together import TogetherAIProvider
from app.services.providers.openrouter import OpenRouterProvider
from app.services.providers.deepseek import DeepSeekProvider
from app.services.providers.perplexity import PerplexityProvider

logger = structlog.get_logger()


class AIProviderManager:
    """Manager for all AI providers."""

    # Provider class mapping
    PROVIDER_CLASSES: dict[str, type[BaseAIProvider]] = {
        "azure_openai": AzureOpenAIProvider,
        "aws_bedrock": AWSBedrockProvider,
        "google_vertex": GoogleVertexProvider,
        "groq": GroqProvider,
        "mistral": MistralProvider,
        "cohere": CohereProvider,
        "together": TogetherAIProvider,
        "openrouter": OpenRouterProvider,
        "deepseek": DeepSeekProvider,
        "perplexity": PerplexityProvider,
    }

    def __init__(self):
        self._providers: dict[str, BaseAIProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize all configured providers."""
        # Azure OpenAI
        if settings.AZURE_OPENAI_API_KEY:
            self._providers["azure_openai"] = AzureOpenAIProvider(
                ProviderConfig(
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_base=settings.AZURE_OPENAI_ENDPOINT,
                    extra={
                        "api_version": settings.AZURE_OPENAI_API_VERSION,
                        "deployment_name": settings.AZURE_OPENAI_DEPLOYMENT,
                    },
                )
            )

        # AWS Bedrock
        if settings.AWS_ACCESS_KEY_ID:
            self._providers["aws_bedrock"] = AWSBedrockProvider(
                ProviderConfig(
                    extra={
                        "region": settings.AWS_REGION,
                        "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
                        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
                    },
                )
            )

        # Google Vertex AI
        if settings.GOOGLE_VERTEX_PROJECT_ID:
            self._providers["google_vertex"] = GoogleVertexProvider(
                ProviderConfig(
                    api_key=settings.GOOGLE_VERTEX_API_KEY,
                    extra={
                        "project_id": settings.GOOGLE_VERTEX_PROJECT_ID,
                        "location": settings.GOOGLE_VERTEX_LOCATION,
                    },
                )
            )

        # Groq
        if settings.GROQ_API_KEY:
            self._providers["groq"] = GroqProvider(
                ProviderConfig(
                    api_key=settings.GROQ_API_KEY,
                    default_model="llama-3.3-70b-versatile",
                )
            )

        # Mistral
        if settings.MISTRAL_API_KEY:
            self._providers["mistral"] = MistralProvider(
                ProviderConfig(
                    api_key=settings.MISTRAL_API_KEY,
                    default_model="mistral-large-latest",
                )
            )

        # Cohere
        if settings.COHERE_API_KEY:
            self._providers["cohere"] = CohereProvider(
                ProviderConfig(
                    api_key=settings.COHERE_API_KEY,
                    default_model="command-r-plus",
                )
            )

        # Together AI
        if settings.TOGETHER_API_KEY:
            self._providers["together"] = TogetherAIProvider(
                ProviderConfig(
                    api_key=settings.TOGETHER_API_KEY,
                    default_model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
                )
            )

        # OpenRouter
        if settings.OPENROUTER_API_KEY:
            self._providers["openrouter"] = OpenRouterProvider(
                ProviderConfig(
                    api_key=settings.OPENROUTER_API_KEY,
                    default_model="anthropic/claude-3.5-sonnet",
                )
            )

        # DeepSeek
        if settings.DEEPSEEK_API_KEY:
            self._providers["deepseek"] = DeepSeekProvider(
                ProviderConfig(
                    api_key=settings.DEEPSEEK_API_KEY,
                    default_model="deepseek-chat",
                )
            )

        # Perplexity
        if settings.PERPLEXITY_API_KEY:
            self._providers["perplexity"] = PerplexityProvider(
                ProviderConfig(
                    api_key=settings.PERPLEXITY_API_KEY,
                    default_model="llama-3.1-sonar-large-128k-online",
                )
            )

        logger.info(
            "AI providers initialized",
            providers=list(self._providers.keys()),
        )

    def get_provider(self, provider_name: str) -> BaseAIProvider | None:
        """Get a specific provider."""
        return self._providers.get(provider_name)

    def list_providers(self) -> list[str]:
        """List available providers."""
        return list(self._providers.keys())

    def list_all_models(self) -> dict[str, list[str]]:
        """List all models from all providers."""
        return {
            name: provider.list_models()
            for name, provider in self._providers.items()
        }

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all providers."""
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception:
                results[name] = False
        return results

    def get_provider_info(self) -> list[dict[str, Any]]:
        """Get information about all providers."""
        return [
            {
                "name": name,
                "display_name": provider.provider_name,
                "models": provider.list_models(),
            }
            for name, provider in self._providers.items()
        ]


# Global provider manager
_provider_manager: AIProviderManager | None = None


def get_provider_manager() -> AIProviderManager:
    """Get the global provider manager."""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = AIProviderManager()
    return _provider_manager
