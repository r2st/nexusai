"""AI provider integrations with support for multiple backends."""

from app.services.providers.base import (
    BaseAIProvider,
    ProviderConfig,
    ChatMessage,
    ChatResponse,
)
from app.services.providers.manager import (
    AIProviderManager,
    get_provider_manager,
)
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

__all__ = [
    "BaseAIProvider",
    "ProviderConfig",
    "ChatMessage",
    "ChatResponse",
    "AIProviderManager",
    "get_provider_manager",
    "AzureOpenAIProvider",
    "AWSBedrockProvider",
    "GoogleVertexProvider",
    "GroqProvider",
    "MistralProvider",
    "CohereProvider",
    "TogetherAIProvider",
    "OpenRouterProvider",
    "DeepSeekProvider",
    "PerplexityProvider",
]
