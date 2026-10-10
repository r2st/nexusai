"""Base classes for AI providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class MessageRole(str, Enum):
    """Message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ChatMessage:
    """A chat message."""

    role: MessageRole
    content: str
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


@dataclass
class TokenUsage:
    """Token usage statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ChatResponse:
    """Response from a chat completion."""

    content: str
    role: MessageRole = MessageRole.ASSISTANT
    model: str | None = None
    finish_reason: str | None = None
    usage: TokenUsage | None = None
    tool_calls: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ProviderConfig(BaseModel):
    """Configuration for an AI provider."""

    api_key: str | None = None
    api_base: str | None = None
    organization_id: str | None = None
    default_model: str | None = None
    timeout: int = 120
    max_retries: int = 3
    extra: dict[str, Any] = {}


class BaseAIProvider(ABC):
    """Base class for all AI providers."""

    provider_name: str = "base"
    supported_models: list[str] = []

    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> ChatResponse:
        """Send a chat completion request."""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Send a streaming chat completion request."""
        pass

    def get_model(self, model: str | None = None) -> str:
        """Get the model to use."""
        return model or self.config.default_model or self.supported_models[0]

    async def health_check(self) -> bool:
        """Check if the provider is available."""
        try:
            response = await self.chat(
                messages=[ChatMessage(role=MessageRole.USER, content="Hi")],
                max_tokens=5,
            )
            return bool(response.content)
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """List available models."""
        return self.supported_models

    def _format_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        """Format messages for the API."""
        formatted = []
        for msg in messages:
            message: dict[str, Any] = {
                "role": msg.role.value,
                "content": msg.content,
            }

            if msg.name:
                message["name"] = msg.name

            if msg.tool_calls:
                message["tool_calls"] = msg.tool_calls

            if msg.tool_call_id:
                message["tool_call_id"] = msg.tool_call_id

            formatted.append(message)

        return formatted
