"""AWS Bedrock provider."""

import json
from collections.abc import AsyncGenerator
from typing import Any

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


class AWSBedrockProvider(BaseAIProvider):
    """AWS Bedrock provider for Claude and other models."""

    provider_name = "aws_bedrock"
    supported_models = [
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "anthropic.claude-3-5-haiku-20241022-v1:0",
        "anthropic.claude-3-opus-20240229-v1:0",
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
        "amazon.titan-text-premier-v1:0",
        "amazon.titan-text-express-v1",
        "meta.llama3-1-70b-instruct-v1:0",
        "meta.llama3-1-8b-instruct-v1:0",
        "mistral.mistral-large-2402-v1:0",
        "cohere.command-r-plus-v1:0",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.region = config.extra.get("region", "us-east-1")
        self._client = None

    def _get_client(self):
        """Get or create the Bedrock client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "bedrock-runtime",
                    region_name=self.region,
                    aws_access_key_id=self.config.extra.get("aws_access_key_id"),
                    aws_secret_access_key=self.config.extra.get("aws_secret_access_key"),
                )
            except ImportError:
                logger.error("boto3 not installed")
                raise

        return self._client

    def _format_for_claude(
        self,
        messages: list[ChatMessage],
        max_tokens: int | None = None,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Format request for Claude models on Bedrock."""
        # Extract system message if present
        system_prompt = None
        chat_messages = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_prompt = msg.content
            else:
                chat_messages.append({
                    "role": msg.role.value,
                    "content": msg.content,
                })

        payload: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": chat_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }

        if system_prompt:
            payload["system"] = system_prompt

        return payload

    def _format_for_titan(
        self,
        messages: list[ChatMessage],
        max_tokens: int | None = None,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Format request for Amazon Titan models."""
        # Combine messages into a single prompt
        prompt_parts = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == MessageRole.USER:
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == MessageRole.ASSISTANT:
                prompt_parts.append(f"Assistant: {msg.content}")

        prompt_parts.append("Assistant:")

        return {
            "inputText": "\n\n".join(prompt_parts),
            "textGenerationConfig": {
                "maxTokenCount": max_tokens or 4096,
                "temperature": temperature,
            },
        }

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> ChatResponse:
        """Send a chat completion request to AWS Bedrock."""
        import asyncio

        model_id = model or self.config.default_model or self.supported_models[0]

        try:
            client = self._get_client()

            # Format based on model
            if model_id.startswith("anthropic.claude"):
                body = self._format_for_claude(messages, max_tokens, temperature)

                if tools:
                    body["tools"] = [
                        {
                            "name": t["function"]["name"],
                            "description": t["function"].get("description", ""),
                            "input_schema": t["function"].get("parameters", {}),
                        }
                        for t in tools
                    ]
            elif model_id.startswith("amazon.titan"):
                body = self._format_for_titan(messages, max_tokens, temperature)
            else:
                # Default Claude-like format
                body = self._format_for_claude(messages, max_tokens, temperature)

            # Run in executor to not block
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json",
                ),
            )

            response_body = json.loads(response["body"].read())

            # Parse response based on model
            if model_id.startswith("anthropic.claude"):
                content = ""
                for block in response_body.get("content", []):
                    if block.get("type") == "text":
                        content += block.get("text", "")

                usage = response_body.get("usage", {})

                return ChatResponse(
                    content=content,
                    role=MessageRole.ASSISTANT,
                    model=model_id,
                    finish_reason=response_body.get("stop_reason"),
                    usage=TokenUsage(
                        prompt_tokens=usage.get("input_tokens", 0),
                        completion_tokens=usage.get("output_tokens", 0),
                        total_tokens=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                    ),
                )
            elif model_id.startswith("amazon.titan"):
                results = response_body.get("results", [{}])
                content = results[0].get("outputText", "") if results else ""

                return ChatResponse(
                    content=content,
                    role=MessageRole.ASSISTANT,
                    model=model_id,
                    finish_reason=results[0].get("completionReason") if results else None,
                )
            else:
                return ChatResponse(
                    content=str(response_body),
                    role=MessageRole.ASSISTANT,
                    model=model_id,
                )

        except Exception as e:
            logger.error("Bedrock chat failed", error=str(e), model=model_id)
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
        """Stream a chat completion from AWS Bedrock."""
        import asyncio

        model_id = model or self.config.default_model or self.supported_models[0]

        try:
            client = self._get_client()

            if model_id.startswith("anthropic.claude"):
                body = self._format_for_claude(messages, max_tokens, temperature)
            else:
                body = self._format_for_claude(messages, max_tokens, temperature)

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.invoke_model_with_response_stream(
                    modelId=model_id,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json",
                ),
            )

            stream = response.get("body")
            if stream:
                for event in stream:
                    chunk = event.get("chunk")
                    if chunk:
                        chunk_data = json.loads(chunk.get("bytes").decode())

                        if chunk_data.get("type") == "content_block_delta":
                            delta = chunk_data.get("delta", {})
                            text = delta.get("text", "")
                            if text:
                                yield text

        except Exception as e:
            logger.error("Bedrock stream failed", error=str(e), model=model_id)
            raise
