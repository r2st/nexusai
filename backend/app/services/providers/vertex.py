"""Google Vertex AI provider."""

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


class GoogleVertexProvider(BaseAIProvider):
    """Google Vertex AI provider for Gemini models."""

    provider_name = "google_vertex"
    supported_models = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-pro",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.project_id = config.extra.get("project_id")
        self.location = config.extra.get("location", "us-central1")

    def _get_url(self, model: str) -> str:
        """Get the API URL."""
        return (
            f"https://{self.location}-aiplatform.googleapis.com/v1/"
            f"projects/{self.project_id}/locations/{self.location}/"
            f"publishers/google/models/{model}:streamGenerateContent"
        )

    def _format_contents(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        """Format messages for Vertex AI."""
        contents = []
        system_instruction = None

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_instruction = msg.content
            elif msg.role == MessageRole.USER:
                contents.append({
                    "role": "user",
                    "parts": [{"text": msg.content}],
                })
            elif msg.role == MessageRole.ASSISTANT:
                contents.append({
                    "role": "model",
                    "parts": [{"text": msg.content}],
                })

        return contents, system_instruction

    async def _get_access_token(self) -> str:
        """Get Google Cloud access token."""
        if self.config.api_key:
            return self.config.api_key

        # Try to get from metadata server or default credentials
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
                    headers={"Metadata-Flavor": "Google"},
                    timeout=5,
                )
                if response.status_code == 200:
                    return response.json().get("access_token")
        except Exception:
            pass

        # Fall back to gcloud credentials
        try:
            import google.auth
            credentials, _ = google.auth.default()
            credentials.refresh(google.auth.transport.requests.Request())
            return credentials.token
        except Exception as e:
            logger.error("Failed to get access token", error=str(e))
            raise

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> ChatResponse:
        """Send a chat completion request to Vertex AI."""
        model_id = model or self.config.default_model or self.supported_models[0]
        access_token = await self._get_access_token()

        contents, system_instruction = self._format_contents(messages)

        async with httpx.AsyncClient() as client:
            try:
                payload: dict[str, Any] = {
                    "contents": contents,
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens or 8192,
                    },
                }

                if system_instruction:
                    payload["systemInstruction"] = {
                        "parts": [{"text": system_instruction}]
                    }

                if tools:
                    payload["tools"] = [{
                        "functionDeclarations": [
                            {
                                "name": t["function"]["name"],
                                "description": t["function"].get("description", ""),
                                "parameters": t["function"].get("parameters", {}),
                            }
                            for t in tools
                        ]
                    }]

                response = await client.post(
                    self._get_url(model_id),
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                data = response.json()

                # Parse response
                candidates = data.get("candidates", [])
                if candidates:
                    content_parts = candidates[0].get("content", {}).get("parts", [])
                    content = "".join(p.get("text", "") for p in content_parts)

                    usage_metadata = data.get("usageMetadata", {})

                    return ChatResponse(
                        content=content,
                        role=MessageRole.ASSISTANT,
                        model=model_id,
                        finish_reason=candidates[0].get("finishReason"),
                        usage=TokenUsage(
                            prompt_tokens=usage_metadata.get("promptTokenCount", 0),
                            completion_tokens=usage_metadata.get("candidatesTokenCount", 0),
                            total_tokens=usage_metadata.get("totalTokenCount", 0),
                        ),
                    )

                return ChatResponse(content="", model=model_id)

            except Exception as e:
                logger.error("Vertex AI chat failed", error=str(e))
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
        """Stream a chat completion from Vertex AI."""
        model_id = model or self.config.default_model or self.supported_models[0]
        access_token = await self._get_access_token()

        contents, system_instruction = self._format_contents(messages)

        async with httpx.AsyncClient() as client:
            payload: dict[str, Any] = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens or 8192,
                },
            }

            if system_instruction:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_instruction}]
                }

            async with client.stream(
                "POST",
                self._get_url(model_id),
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.config.timeout,
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json
                        try:
                            # Vertex AI returns JSON array chunks
                            if line.startswith("["):
                                data = json.loads(line.rstrip(","))
                            else:
                                data = json.loads(line.rstrip(","))

                            if isinstance(data, list):
                                for item in data:
                                    for text in self._extract_text(item):
                                        yield text
                            else:
                                for text in self._extract_text(data):
                                    yield text
                        except json.JSONDecodeError:
                            continue

    def _extract_text(self, data: dict) -> list[str]:
        """Extract text from response data."""
        texts = []
        candidates = data.get("candidates", [])
        for candidate in candidates:
            parts = candidate.get("content", {}).get("parts", [])
            for part in parts:
                if "text" in part:
                    texts.append(part["text"])
        return texts
