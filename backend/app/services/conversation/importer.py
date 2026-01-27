"""Conversation import service."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import Conversation, Message, MessageRole, ModelProvider


def _get_default_model_for_provider(provider: str) -> str:
    """Get the default model name for a given provider from settings."""
    provider_lower = provider.lower()
    if provider_lower == "openai":
        return settings.OPENAI_DEFAULT_MODEL
    elif provider_lower == "anthropic":
        return settings.ANTHROPIC_DEFAULT_MODEL
    elif provider_lower == "google":
        return settings.GOOGLE_DEFAULT_MODEL
    return settings.OPENAI_DEFAULT_MODEL

logger = structlog.get_logger()


class ImportFormat(str, Enum):
    """Supported import formats."""

    NEXUSAI = "nexusai"
    LIBRECHAT = "librechat"
    CHATGPT = "chatgpt"
    CHATBOT_UI = "chatbot_ui"
    OPENAI_HISTORY = "openai_history"


@dataclass
class ImportResult:
    """Result of conversation import."""

    success: bool
    conversation_id: str | None = None
    message_count: int = 0
    errors: list[str] = field(default_factory=list)


class ConversationImporter:
    """Service for importing conversations from various formats."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def import_conversation(
        self,
        user_id: str,
        data: str | dict,
        format: ImportFormat = ImportFormat.NEXUSAI,
    ) -> ImportResult:
        """Import a conversation from external format."""
        try:
            # Parse data if string
            if isinstance(data, str):
                parsed_data = json.loads(data)
            else:
                parsed_data = data

            # Import based on format
            if format == ImportFormat.NEXUSAI:
                return await self._import_nexusai(user_id, parsed_data)
            elif format == ImportFormat.LIBRECHAT:
                return await self._import_librechat(user_id, parsed_data)
            elif format == ImportFormat.CHATGPT:
                return await self._import_chatgpt(user_id, parsed_data)
            elif format == ImportFormat.CHATBOT_UI:
                return await self._import_chatbot_ui(user_id, parsed_data)
            elif format == ImportFormat.OPENAI_HISTORY:
                return await self._import_openai_history(user_id, parsed_data)
            else:
                return ImportResult(
                    success=False,
                    errors=[f"Unsupported format: {format}"],
                )

        except json.JSONDecodeError as e:
            return ImportResult(
                success=False,
                errors=[f"Invalid JSON: {str(e)}"],
            )
        except Exception as e:
            logger.error("Import failed", error=str(e))
            return ImportResult(
                success=False,
                errors=[f"Import failed: {str(e)}"],
            )

    async def import_multiple(
        self,
        user_id: str,
        data: str | list,
        format: ImportFormat = ImportFormat.NEXUSAI,
    ) -> list[ImportResult]:
        """Import multiple conversations."""
        try:
            if isinstance(data, str):
                parsed_data = json.loads(data)
            else:
                parsed_data = data

            if not isinstance(parsed_data, list):
                parsed_data = [parsed_data]

            results = []
            for item in parsed_data:
                result = await self.import_conversation(user_id, item, format)
                results.append(result)

            return results

        except Exception as e:
            return [ImportResult(success=False, errors=[str(e)])]

    async def _import_nexusai(
        self,
        user_id: str,
        data: dict,
    ) -> ImportResult:
        """Import NexusAI native format."""
        errors = []

        try:
            # Create conversation
            conversation = Conversation(
                id=str(uuid4()),  # Generate new ID
                user_id=user_id,
                title=data.get("title", "Imported Conversation"),
                model_provider=data.get("model_provider", settings.DEFAULT_AI_PROVIDER),
                model_name=data.get("model_name", _get_default_model_for_provider(data.get("model_provider", settings.DEFAULT_AI_PROVIDER))),
                system_prompt=data.get("system_prompt"),
            )

            self.db.add(conversation)

            # Add messages
            messages_data = data.get("messages", [])
            message_count = 0

            for i, msg_data in enumerate(messages_data):
                message = Message(
                    id=str(uuid4()),
                    conversation_id=conversation.id,
                    role=msg_data.get("role", MessageRole.USER.value),
                    content=msg_data.get("content", ""),
                    model_name=msg_data.get("model_name"),
                    position=i,
                    prompt_tokens=msg_data.get("prompt_tokens"),
                    completion_tokens=msg_data.get("completion_tokens"),
                )

                self.db.add(message)
                message_count += 1

            conversation.message_count = message_count
            await self.db.flush()

            return ImportResult(
                success=True,
                conversation_id=conversation.id,
                message_count=message_count,
            )

        except Exception as e:
            errors.append(str(e))
            return ImportResult(success=False, errors=errors)

    async def _import_librechat(
        self,
        user_id: str,
        data: dict,
    ) -> ImportResult:
        """Import LibreChat format."""
        errors = []

        try:
            # Map endpoint to provider
            endpoint = data.get("endpoint", "openAI")
            provider_map = {
                "openAI": ModelProvider.OPENAI.value,
                "anthropic": ModelProvider.ANTHROPIC.value,
                "google": ModelProvider.GOOGLE.value,
            }
            provider = provider_map.get(endpoint, settings.DEFAULT_AI_PROVIDER)

            conversation = Conversation(
                id=str(uuid4()),
                user_id=user_id,
                title=data.get("title", "Imported from LibreChat"),
                model_provider=provider,
                model_name=data.get("model", _get_default_model_for_provider(provider)),
            )

            self.db.add(conversation)

            messages_data = data.get("messages", [])
            message_count = 0

            for i, msg_data in enumerate(messages_data):
                message = Message(
                    id=str(uuid4()),
                    conversation_id=conversation.id,
                    role=msg_data.get("role", MessageRole.USER.value),
                    content=msg_data.get("content", ""),
                    model_name=msg_data.get("model"),
                    position=i,
                )

                self.db.add(message)
                message_count += 1

            conversation.message_count = message_count
            await self.db.flush()

            return ImportResult(
                success=True,
                conversation_id=conversation.id,
                message_count=message_count,
            )

        except Exception as e:
            errors.append(str(e))
            return ImportResult(success=False, errors=errors)

    async def _import_chatgpt(
        self,
        user_id: str,
        data: dict,
    ) -> ImportResult:
        """Import ChatGPT export format."""
        errors = []

        try:
            conversation = Conversation(
                id=str(uuid4()),
                user_id=user_id,
                title=data.get("title", "Imported from ChatGPT"),
                model_provider=ModelProvider.OPENAI.value,
                model_name=settings.OPENAI_DEFAULT_MODEL,
            )

            self.db.add(conversation)

            # ChatGPT uses a mapping structure
            mapping = data.get("mapping", {})
            messages = []

            # Extract messages from mapping
            for node_id, node in mapping.items():
                msg = node.get("message")
                if msg and msg.get("content", {}).get("parts"):
                    author = msg.get("author", {})
                    role = author.get("role", "user")

                    if role in ("user", "assistant", "system"):
                        content_parts = msg["content"]["parts"]
                        content = "\n".join(str(p) for p in content_parts if p)

                        if content:
                            messages.append({
                                "role": role,
                                "content": content,
                                "create_time": msg.get("create_time", 0),
                            })

            # Sort by creation time
            messages.sort(key=lambda m: m.get("create_time", 0))

            message_count = 0
            for i, msg_data in enumerate(messages):
                message = Message(
                    id=str(uuid4()),
                    conversation_id=conversation.id,
                    role=msg_data["role"],
                    content=msg_data["content"],
                    position=i,
                )

                self.db.add(message)
                message_count += 1

            conversation.message_count = message_count
            await self.db.flush()

            return ImportResult(
                success=True,
                conversation_id=conversation.id,
                message_count=message_count,
            )

        except Exception as e:
            errors.append(str(e))
            return ImportResult(success=False, errors=errors)

    async def _import_chatbot_ui(
        self,
        user_id: str,
        data: dict,
    ) -> ImportResult:
        """Import Chatbot UI format."""
        errors = []

        try:
            conversation = Conversation(
                id=str(uuid4()),
                user_id=user_id,
                title=data.get("name", "Imported from Chatbot UI"),
                model_provider=ModelProvider.OPENAI.value,
                model_name=data.get("model", {}).get("id", settings.OPENAI_DEFAULT_MODEL),
                system_prompt=data.get("prompt"),
            )

            self.db.add(conversation)

            messages_data = data.get("messages", [])
            message_count = 0

            for i, msg_data in enumerate(messages_data):
                message = Message(
                    id=str(uuid4()),
                    conversation_id=conversation.id,
                    role=msg_data.get("role", MessageRole.USER.value),
                    content=msg_data.get("content", ""),
                    position=i,
                )

                self.db.add(message)
                message_count += 1

            conversation.message_count = message_count
            await self.db.flush()

            return ImportResult(
                success=True,
                conversation_id=conversation.id,
                message_count=message_count,
            )

        except Exception as e:
            errors.append(str(e))
            return ImportResult(success=False, errors=errors)

    async def _import_openai_history(
        self,
        user_id: str,
        data: dict,
    ) -> ImportResult:
        """Import OpenAI conversation history format."""
        # This is similar to ChatGPT format
        return await self._import_chatgpt(user_id, data)

    def detect_format(self, data: dict) -> ImportFormat:
        """Auto-detect the import format."""
        # Check for ChatGPT mapping structure
        if "mapping" in data:
            return ImportFormat.CHATGPT

        # Check for LibreChat endpoint field
        if "endpoint" in data:
            return ImportFormat.LIBRECHAT

        # Check for Chatbot UI structure
        if "model" in data and isinstance(data.get("model"), dict):
            return ImportFormat.CHATBOT_UI

        # Default to NexusAI format
        return ImportFormat.NEXUSAI
