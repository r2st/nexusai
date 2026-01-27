"""Cohere provider."""

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


class CohereProvider(BaseAIProvider):
    """Cohere provider for Command models."""

    provider_name = "cohere"
    supported_models = [
        "command-r-plus",
        "command-r",
        "command",
        "command-light",
        "command-nightly",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.api_base or "https://api.cohere.ai/v1"

    def _format_for_cohere(
        self,
        messages: list[ChatMessage],
    ) -> tuple[str, list[dict[str, str]], str | None]:
        """Format messages for Cohere's chat endpoint."""
        preamble = None
        chat_history = []
        message = ""

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                preamble = msg.content
            elif msg.role == MessageRole.USER:
                if message:  # Previous user message, add to history
                    chat_history.append({"role": "USER", "message": message})
                message = msg.content
            elif msg.role == MessageRole.ASSISTANT:
                if message:  # Add pending user message
                    chat_history.append({"role": "USER", "message": message})
                    message = ""
                chat_history.append({"role": "CHATBOT", "message": msg.content})

        return message, chat_history, preamble

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> ChatResponse:
        """Send a chat completion request to Cohere."""
        model_id = self.get_model(model)
        message, chat_history, preamble = self._format_for_cohere(messages)

        async with httpx.AsyncClient() as client:
            try:
                payload: dict[str, Any] = {
                    "model": model_id,
                    "message": message,
                    "temperature": temperature,
                }

                if chat_history:
                    payload["chat_history"] = chat_history

                if preamble:
                    payload["preamble"] = preamble

                if max_tokens:
                    payload["max_tokens"] = max_tokens

                if tools:
                    payload["tools"] = [
                        {
                            "name": t["function"]["name"],
                            "description": t["function"].get("description", ""),
                            "parameter_definitions": {
                                k: {"type": v.get("type", "string"), "required": k in t["function"].get("parameters", {}).get("required", [])}
                                for k, v in t["function"].get("parameters", {}).get("properties", {}).items()
                            },
                        }
                        for t in tools
                    ]

                response = await client.post(
                    f"{self.base_url}/chat",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                data = response.json()

                meta = data.get("meta", {})
                tokens = meta.get("tokens", {})

                return ChatResponse(
                    content=data.get("text", ""),
                    role=MessageRole.ASSISTANT,
                    model=model_id,
                    finish_reason=data.get("finish_reason"),
                    usage=TokenUsage(
                        prompt_tokens=tokens.get("input_tokens", 0),
                        completion_tokens=tokens.get("output_tokens", 0),
                        total_tokens=tokens.get("input_tokens", 0) + tokens.get("output_tokens", 0),
                    ),
                )

            except Exception as e:
                logger.error("Cohere chat failed", error=str(e))
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
        """Stream a chat completion from Cohere."""
        model_id = self.get_model(model)
        message, chat_history, preamble = self._format_for_cohere(messages)

        async with httpx.AsyncClient() as client:
            payload: dict[str, Any] = {
                "model": model_id,
                "message": message,
                "temperature": temperature,
                "stream": True,
            }

            if chat_history:
                payload["chat_history"] = chat_history

            if preamble:
                payload["preamble"] = preamble

            if max_tokens:
                payload["max_tokens"] = max_tokens

            async with client.stream(
                "POST",
                f"{self.base_url}/chat",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.config.timeout,
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json
                        try:
                            data = json.loads(line)
                            if data.get("event_type") == "text-generation":
                                text = data.get("text", "")
                                if text:
                                    yield text
                        except json.JSONDecodeError:
                            continue
