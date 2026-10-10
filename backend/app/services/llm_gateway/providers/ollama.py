"""Ollama local LLM provider implementation."""

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


class OllamaProvider(BaseAIProvider):
    """Ollama local LLM provider."""

    provider_name = "ollama"
    supported_models = [
        "llama3",
        "llama3:8b",
        "llama3:70b",
        "llama3.1",
        "llama3.2",
        "mistral",
        "mistral:7b",
        "mixtral",
        "mixtral:8x7b",
        "codellama",
        "codellama:7b",
        "codellama:13b",
        "codellama:34b",
        "phi3",
        "phi3:mini",
        "gemma",
        "gemma:7b",
        "qwen2",
        "qwen2:7b",
        "deepseek-coder",
        "starcoder2",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not config.api_base:
            raise ValueError("OLLAMA_BASE_URL must be configured to use Ollama provider")
        self.api_base = config.api_base
        self.client = httpx.AsyncClient(
            timeout=config.timeout or 300,  # Longer timeout for local models
            headers={
                "Content-Type": "application/json",
            },
        )

    async def health_check(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = await self.client.get(f"{self.api_base}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def list_local_models(self) -> list[str]:
        """List models available locally in Ollama."""
        try:
            response = await self.client.get(f"{self.api_base}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.warning("Failed to list Ollama models", error=str(e))
        return []

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> ChatResponse:
        """Send a chat completion request to Ollama."""
        model = self.get_model(model)
        formatted_messages = self._format_messages(messages)

        payload: dict[str, Any] = {
            "model": model,
            "messages": formatted_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        if tools:
            # Ollama supports function calling for some models
            payload["tools"] = tools

        response = await self.client.post(
            f"{self.api_base}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        message = data.get("message", {})

        # Calculate token usage (Ollama provides these in response)
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)

        return ChatResponse(
            content=message.get("content", ""),
            role=MessageRole.ASSISTANT,
            model=model,
            finish_reason="stop" if data.get("done") else None,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            tool_calls=message.get("tool_calls"),
            metadata={
                "total_duration": data.get("total_duration"),
                "load_duration": data.get("load_duration"),
                "eval_duration": data.get("eval_duration"),
            },
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
        """Stream a chat completion from Ollama."""
        model = self.get_model(model)
        formatted_messages = self._format_messages(messages)

        payload: dict[str, Any] = {
            "model": model,
            "messages": formatted_messages,
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with self.client.stream(
            "POST",
            f"{self.api_base}/api/chat",
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    try:
                        import json
                        data = json.loads(line)
                        message = data.get("message", {})
                        content = message.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.debug("Skipping malformed streaming chunk", error=str(e))
                        continue

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> str:
        """Generate text completion (non-chat mode)."""
        model = self.get_model(model)

        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        response = await self.client.post(
            f"{self.api_base}/api/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        return data.get("response", "")

    async def embed(
        self,
        text: str | list[str],
        model: str = "nomic-embed-text",
    ) -> list[list[float]]:
        """Generate embeddings using Ollama."""
        texts = [text] if isinstance(text, str) else text

        embeddings = []
        for t in texts:
            response = await self.client.post(
                f"{self.api_base}/api/embeddings",
                json={
                    "model": model,
                    "prompt": t,
                },
            )
            response.raise_for_status()
            data = response.json()
            embeddings.append(data.get("embedding", []))

        return embeddings

    async def pull_model(self, model: str) -> bool:
        """Pull a model from Ollama library."""
        try:
            response = await self.client.post(
                f"{self.api_base}/api/pull",
                json={"name": model},
                timeout=600,  # 10 minutes for large models
            )
            return response.status_code == 200
        except Exception as e:
            logger.error("Failed to pull model", model=model, error=str(e))
            return False

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
