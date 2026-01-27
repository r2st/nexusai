"""OpenRouter provider for multi-model access."""

from collections.abc import AsyncGenerator
from typing import Any

import httpx
import structlog

from app.services.providers.base import (
    BaseAIProvider,
    ChatMessage,
    ChatResponse,
    MessageRole,
    ProviderConfig,
    TokenUsage,
)

logger = structlog.get_logger()


class OpenRouterProvider(BaseAIProvider):
    """OpenRouter provider for accessing multiple AI models."""

    provider_name = "openrouter"
    supported_models = [
        "anthropic/claude-3.5-sonnet",
        "anthropic/claude-3-opus",
        "openai/gpt-4o",
        "openai/gpt-4-turbo",
        "google/gemini-pro-1.5",
        "meta-llama/llama-3.1-405b-instruct",
        "mistralai/mistral-large",
        "deepseek/deepseek-chat",
        "qwen/qwen-2.5-72b-instruct",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.api_base or "https://openrouter.ai/api/v1"
        self.site_url = config.extra.get("site_url", "https://nexusai.dev")
        self.site_name = config.extra.get("site_name", "NexusAI")

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> ChatResponse:
        """Send a chat completion request to OpenRouter."""
        model_id = self.get_model(model)

        async with httpx.AsyncClient() as client:
            try:
                payload: dict[str, Any] = {
                    "model": model_id,
                    "messages": self._format_messages(messages),
                    "temperature": temperature,
                }

                if max_tokens:
                    payload["max_tokens"] = max_tokens

                if tools:
                    payload["tools"] = tools

                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": self.site_url,
                        "X-Title": self.site_name,
                    },
                    json=payload,
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                data = response.json()

                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                usage = data.get("usage", {})

                return ChatResponse(
                    content=message.get("content", ""),
                    role=MessageRole(message.get("role", "assistant")),
                    model=data.get("model"),
                    finish_reason=choice.get("finish_reason"),
                    usage=TokenUsage(
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        total_tokens=usage.get("total_tokens", 0),
                    ),
                    tool_calls=message.get("tool_calls"),
                )

            except Exception as e:
                logger.error("OpenRouter chat failed", error=str(e))
                raise

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion from OpenRouter."""
        model_id = self.get_model(model)

        async with httpx.AsyncClient() as client:
            payload: dict[str, Any] = {
                "model": model_id,
                "messages": self._format_messages(messages),
                "temperature": temperature,
                "stream": True,
            }

            if max_tokens:
                payload["max_tokens"] = max_tokens

            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.site_name,
                },
                json=payload,
                timeout=self.config.timeout,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break

                        import json
                        try:
                            data = json.loads(data_str)
                            choice = data.get("choices", [{}])[0]
                            delta = choice.get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

    async def list_available_models(self) -> list[dict[str, Any]]:
        """List all available models on OpenRouter."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                return [
                    {
                        "id": m.get("id"),
                        "name": m.get("name"),
                        "pricing": m.get("pricing"),
                        "context_length": m.get("context_length"),
                    }
                    for m in data.get("data", [])
                ]

            except Exception as e:
                logger.error("Failed to list OpenRouter models", error=str(e))
                return []
