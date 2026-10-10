"""Anthropic Claude provider implementation."""

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


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude API provider."""

    provider_name = "anthropic"
    supported_models = [
        # Claude 4 models (latest - 2025)
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        # Claude 3.5 models
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        # Claude 3 models (legacy)
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    # Model aliases for convenience
    MODEL_ALIASES = {
        # Claude 4 aliases (recommended)
        "claude-4-sonnet": "claude-sonnet-4-20250514",
        "claude-sonnet-4": "claude-sonnet-4-20250514",
        "claude-4-opus": "claude-opus-4-20250514",
        "claude-opus-4": "claude-opus-4-20250514",
        # Claude 3.5 aliases
        "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
        "claude-3.5-sonnet": "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku": "claude-3-5-haiku-20241022",
        "claude-3.5-haiku": "claude-3-5-haiku-20241022",
        # Claude 3 aliases (legacy)
        "claude-3-opus": "claude-3-opus-20240229",
        "claude-3-sonnet": "claude-3-sonnet-20240229",
        "claude-3-haiku": "claude-3-haiku-20240307",
    }

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self.api_base = config.api_base or "https://api.anthropic.com"
        self.client = httpx.AsyncClient(
            timeout=config.timeout,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )

    def get_model(self, model: str | None = None) -> str:
        """Get model name, resolving aliases."""
        model = model or self.config.default_model or self.supported_models[0]
        return self.MODEL_ALIASES.get(model, model)

    def _convert_messages(self, messages: list[ChatMessage]) -> tuple[str | None, list[dict]]:
        """Convert messages to Anthropic format (system separate)."""
        system_message = None
        converted = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_message = msg.content
            else:
                role = "user" if msg.role == MessageRole.USER else "assistant"
                converted.append({
                    "role": role,
                    "content": msg.content,
                })

        return system_message, converted

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> ChatResponse:
        """Send a chat completion request to Anthropic."""
        model = self.get_model(model)
        system_message, converted_messages = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "model": model,
            "messages": converted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }

        if system_message:
            payload["system"] = system_message

        if tools:
            # Convert OpenAI tool format to Anthropic format
            anthropic_tools = []
            for tool in tools:
                if tool.get("type") == "function":
                    func = tool["function"]
                    anthropic_tools.append({
                        "name": func["name"],
                        "description": func.get("description", ""),
                        "input_schema": func.get("parameters", {}),
                    })
            if anthropic_tools:
                payload["tools"] = anthropic_tools

        response = await self.client.post(
            f"{self.api_base}/v1/messages",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        # Extract content
        content = ""
        tool_calls = None

        for block in data.get("content", []):
            if block["type"] == "text":
                content += block["text"]
            elif block["type"] == "tool_use":
                if tool_calls is None:
                    tool_calls = []
                tool_calls.append({
                    "id": block["id"],
                    "type": "function",
                    "function": {
                        "name": block["name"],
                        "arguments": block["input"],
                    },
                })

        usage = data.get("usage", {})

        return ChatResponse(
            content=content,
            role=MessageRole.ASSISTANT,
            model=model,
            finish_reason=data.get("stop_reason"),
            usage=TokenUsage(
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                total_tokens=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            ),
            tool_calls=tool_calls,
        )

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion from Anthropic."""
        model = self.get_model(model)
        system_message, converted_messages = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "model": model,
            "messages": converted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            "stream": True,
        }

        if system_message:
            payload["system"] = system_message

        async with self.client.stream(
            "POST",
            f"{self.api_base}/v1/messages",
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        import json
                        data = json.loads(data_str)
                        event_type = data.get("type")

                        if event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield delta.get("text", "")
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.debug("Skipping malformed SSE chunk", error=str(e))
                        continue

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
