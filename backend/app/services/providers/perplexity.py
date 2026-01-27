"""Perplexity provider."""

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


class PerplexityProvider(BaseAIProvider):
    """Perplexity provider for search-augmented AI."""

    provider_name = "perplexity"
    supported_models = [
        "llama-3.1-sonar-large-128k-online",
        "llama-3.1-sonar-small-128k-online",
        "llama-3.1-sonar-large-128k-chat",
        "llama-3.1-sonar-small-128k-chat",
        "llama-3.1-8b-instruct",
        "llama-3.1-70b-instruct",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.api_base or "https://api.perplexity.ai"

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> ChatResponse:
        """Send a chat completion request to Perplexity."""
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

                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
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

                # Perplexity includes citations
                citations = data.get("citations", [])

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
                    metadata={"citations": citations} if citations else {},
                )

            except Exception as e:
                logger.error("Perplexity chat failed", error=str(e))
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
        """Stream a chat completion from Perplexity."""
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
