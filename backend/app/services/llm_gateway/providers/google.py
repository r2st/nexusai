"""Google Gemini provider implementation."""

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


class GoogleProvider(BaseAIProvider):
    """Google Gemini API provider."""

    provider_name = "google"
    supported_models = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro",
        "gemini-pro-vision",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self.api_base = config.api_base or "https://generativelanguage.googleapis.com/v1beta"
        self.client = httpx.AsyncClient(
            timeout=config.timeout,
            headers={
                "Content-Type": "application/json",
            },
        )

    def _convert_messages(self, messages: list[ChatMessage]) -> tuple[str | None, list[dict]]:
        """Convert messages to Gemini format."""
        system_instruction = None
        contents = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_instruction = msg.content
            else:
                role = "user" if msg.role == MessageRole.USER else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.content}],
                })

        return system_instruction, contents

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> ChatResponse:
        """Send a chat completion request to Google Gemini."""
        model = self.get_model(model)
        system_instruction, contents = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            },
        }

        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        if tools:
            # Convert to Gemini tool format
            gemini_tools = []
            for tool in tools:
                if tool.get("type") == "function":
                    func = tool["function"]
                    gemini_tools.append({
                        "function_declarations": [{
                            "name": func["name"],
                            "description": func.get("description", ""),
                            "parameters": func.get("parameters", {}),
                        }]
                    })
            if gemini_tools:
                payload["tools"] = gemini_tools

        url = f"{self.api_base}/models/{model}:generateContent?key={self.api_key}"
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        # Extract content
        content = ""
        tool_calls = None
        candidates = data.get("candidates", [])

        if candidates:
            candidate = candidates[0]
            for part in candidate.get("content", {}).get("parts", []):
                if "text" in part:
                    content += part["text"]
                elif "functionCall" in part:
                    if tool_calls is None:
                        tool_calls = []
                    fc = part["functionCall"]
                    tool_calls.append({
                        "type": "function",
                        "function": {
                            "name": fc["name"],
                            "arguments": fc.get("args", {}),
                        },
                    })

        # Token usage
        usage_meta = data.get("usageMetadata", {})

        return ChatResponse(
            content=content,
            role=MessageRole.ASSISTANT,
            model=model,
            finish_reason=candidates[0].get("finishReason") if candidates else None,
            usage=TokenUsage(
                prompt_tokens=usage_meta.get("promptTokenCount", 0),
                completion_tokens=usage_meta.get("candidatesTokenCount", 0),
                total_tokens=usage_meta.get("totalTokenCount", 0),
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
        """Stream a chat completion from Google Gemini."""
        model = self.get_model(model)
        system_instruction, contents = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            },
        }

        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        url = f"{self.api_base}/models/{model}:streamGenerateContent?key={self.api_key}&alt=sse"

        async with self.client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        import json
                        data = json.loads(data_str)
                        candidates = data.get("candidates", [])
                        if candidates:
                            for part in candidates[0].get("content", {}).get("parts", []):
                                if "text" in part:
                                    yield part["text"]
                    except (json.JSONDecodeError, KeyError, IndexError) as e:
                        logger.debug("Skipping malformed SSE chunk", error=str(e))
                        continue

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
