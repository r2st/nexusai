"""Azure OpenAI provider."""

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


class AzureOpenAIProvider(BaseAIProvider):
    """Azure OpenAI Service provider."""

    provider_name = "azure_openai"
    supported_models = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-35-turbo",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_version = config.extra.get("api_version", "2024-02-15-preview")
        self.deployment_name = config.extra.get("deployment_name")

    def _get_url(self, deployment: str) -> str:
        """Get the API URL for a deployment."""
        return f"{self.config.api_base}/openai/deployments/{deployment}/chat/completions?api-version={self.api_version}"

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> ChatResponse:
        """Send a chat completion request to Azure OpenAI."""
        deployment = self.deployment_name or model or self.supported_models[0]

        async with httpx.AsyncClient() as client:
            try:
                payload: dict[str, Any] = {
                    "messages": self._format_messages(messages),
                    "temperature": temperature,
                }

                if max_tokens:
                    payload["max_tokens"] = max_tokens

                if tools:
                    payload["tools"] = tools

                response = await client.post(
                    self._get_url(deployment),
                    headers={
                        "api-key": self.config.api_key,
                        "Content-Type": "application/json",
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
                logger.error("Azure OpenAI chat failed", error=str(e))
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
        """Stream a chat completion from Azure OpenAI."""
        deployment = self.deployment_name or model or self.supported_models[0]

        async with httpx.AsyncClient() as client:
            payload: dict[str, Any] = {
                "messages": self._format_messages(messages),
                "temperature": temperature,
                "stream": True,
            }

            if max_tokens:
                payload["max_tokens"] = max_tokens

            if tools:
                payload["tools"] = tools

            async with client.stream(
                "POST",
                self._get_url(deployment),
                headers={
                    "api-key": self.config.api_key,
                    "Content-Type": "application/json",
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
