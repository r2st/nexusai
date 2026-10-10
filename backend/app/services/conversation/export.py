"""Conversation export service."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from uuid import uuid4

import aiofiles
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import Conversation, Message

logger = structlog.get_logger()


class ExportFormat(str, Enum):
    """Supported export formats."""

    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"
    HTML = "html"
    LIBRECHAT = "librechat"
    CHATGPT = "chatgpt"


@dataclass
class ExportResult:
    """Result of conversation export."""

    format: ExportFormat
    content: str
    filename: str
    file_path: str | None = None


class ConversationExporter:
    """Service for exporting conversations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.export_dir = Path(settings.UPLOAD_DIR) / "exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)

    async def export_conversation(
        self,
        conversation_id: str,
        user_id: str,
        format: ExportFormat = ExportFormat.JSON,
        save_to_disk: bool = True,
    ) -> ExportResult | None:
        """Export a single conversation."""
        # Get conversation
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            logger.error("Conversation not found", conversation_id=conversation_id)
            return None

        # Get messages
        messages_result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.position)
        )
        messages = list(messages_result.scalars().all())

        # Export based on format
        if format == ExportFormat.JSON:
            content = self._export_json(conversation, messages)
            extension = "json"
        elif format == ExportFormat.MARKDOWN:
            content = self._export_markdown(conversation, messages)
            extension = "md"
        elif format == ExportFormat.TEXT:
            content = self._export_text(conversation, messages)
            extension = "txt"
        elif format == ExportFormat.HTML:
            content = self._export_html(conversation, messages)
            extension = "html"
        elif format == ExportFormat.LIBRECHAT:
            content = self._export_librechat(conversation, messages)
            extension = "json"
        elif format == ExportFormat.CHATGPT:
            content = self._export_chatgpt(conversation, messages)
            extension = "json"
        else:
            content = self._export_json(conversation, messages)
            extension = "json"

        filename = f"{conversation.title[:50].replace(' ', '_')}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.{extension}"

        export_result = ExportResult(
            format=format,
            content=content,
            filename=filename,
        )

        # Save to disk if requested
        if save_to_disk:
            file_path = self.export_dir / filename
            async with aiofiles.open(file_path, "w") as f:
                await f.write(content)
            export_result.file_path = str(file_path)

        return export_result

    async def export_multiple(
        self,
        user_id: str,
        conversation_ids: list[str] | None = None,
        format: ExportFormat = ExportFormat.JSON,
    ) -> ExportResult | None:
        """Export multiple conversations."""
        # Get conversations
        query = select(Conversation).where(Conversation.user_id == user_id)

        if conversation_ids:
            query = query.where(Conversation.id.in_(conversation_ids))

        result = await self.db.execute(query.order_by(Conversation.created_at.desc()).limit(500))
        conversations = list(result.scalars().all())

        if not conversations:
            return None

        # Export all
        all_exports = []
        for conv in conversations:
            messages_result = await self.db.execute(
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(Message.position)
            )
            messages = list(messages_result.scalars().all())

            all_exports.append({
                "conversation": conv,
                "messages": messages,
            })

        # Create combined export
        if format == ExportFormat.JSON:
            content = json.dumps(
                [
                    {
                        "id": e["conversation"].id,
                        "title": e["conversation"].title,
                        "model": e["conversation"].model_name,
                        "created_at": e["conversation"].created_at.isoformat(),
                        "messages": [
                            {
                                "role": m.role,
                                "content": m.content,
                                "created_at": m.created_at.isoformat(),
                            }
                            for m in e["messages"]
                        ],
                    }
                    for e in all_exports
                ],
                indent=2,
            )
            extension = "json"
        else:
            # Markdown format for multiple conversations
            content = "\n\n---\n\n".join([
                self._export_markdown(e["conversation"], e["messages"])
                for e in all_exports
            ])
            extension = "md"

        filename = f"nexusai_export_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.{extension}"

        return ExportResult(
            format=format,
            content=content,
            filename=filename,
        )

    def _export_json(
        self,
        conversation: Conversation,
        messages: list[Message],
    ) -> str:
        """Export to JSON format."""
        data = {
            "id": conversation.id,
            "title": conversation.title,
            "model_provider": conversation.model_provider,
            "model_name": conversation.model_name,
            "system_prompt": conversation.system_prompt,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "message_count": conversation.message_count,
            "total_tokens": conversation.total_tokens,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "model_name": m.model_name,
                    "created_at": m.created_at.isoformat(),
                    "prompt_tokens": m.prompt_tokens,
                    "completion_tokens": m.completion_tokens,
                }
                for m in messages
            ],
        }
        return json.dumps(data, indent=2)

    def _export_markdown(
        self,
        conversation: Conversation,
        messages: list[Message],
    ) -> str:
        """Export to Markdown format."""
        lines = [
            f"# {conversation.title}",
            "",
            f"**Model:** {conversation.model_provider}/{conversation.model_name}",
            f"**Created:** {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        if conversation.system_prompt:
            lines.extend([
                "## System Prompt",
                "",
                f"> {conversation.system_prompt}",
                "",
            ])

        lines.extend([
            "## Conversation",
            "",
        ])

        for msg in messages:
            role_emoji = "👤" if msg.role == "user" else "🤖" if msg.role == "assistant" else "⚙️"
            role_name = msg.role.title()

            lines.extend([
                f"### {role_emoji} {role_name}",
                "",
                msg.content,
                "",
            ])

        return "\n".join(lines)

    def _export_text(
        self,
        conversation: Conversation,
        messages: list[Message],
    ) -> str:
        """Export to plain text format."""
        lines = [
            f"Title: {conversation.title}",
            f"Model: {conversation.model_provider}/{conversation.model_name}",
            f"Created: {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "=" * 50,
            "",
        ]

        for msg in messages:
            lines.extend([
                f"[{msg.role.upper()}]",
                msg.content,
                "",
                "-" * 30,
                "",
            ])

        return "\n".join(lines)

    def _export_html(
        self,
        conversation: Conversation,
        messages: list[Message],
    ) -> str:
        """Export to HTML format."""
        messages_html = ""
        for msg in messages:
            role_class = f"message-{msg.role}"
            messages_html += f"""
            <div class="message {role_class}">
                <div class="role">{msg.role.title()}</div>
                <div class="content">{msg.content}</div>
                <div class="time">{msg.created_at.strftime('%H:%M')}</div>
            </div>
            """

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{conversation.title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ border-bottom: 2px solid #333; padding-bottom: 10px; }}
        .meta {{ color: #666; margin-bottom: 20px; }}
        .message {{ padding: 15px; margin: 10px 0; border-radius: 10px; }}
        .message-user {{ background: #e3f2fd; }}
        .message-assistant {{ background: #f5f5f5; }}
        .message-system {{ background: #fff3e0; }}
        .role {{ font-weight: bold; margin-bottom: 5px; }}
        .content {{ white-space: pre-wrap; }}
        .time {{ color: #999; font-size: 12px; margin-top: 5px; }}
    </style>
</head>
<body>
    <h1>{conversation.title}</h1>
    <div class="meta">
        <p>Model: {conversation.model_provider}/{conversation.model_name}</p>
        <p>Created: {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <div class="messages">
        {messages_html}
    </div>
</body>
</html>
        """
        return html

    def _export_librechat(
        self,
        conversation: Conversation,
        messages: list[Message],
    ) -> str:
        """Export to LibreChat format."""
        data = {
            "conversationId": conversation.id,
            "title": conversation.title,
            "endpoint": conversation.model_provider,
            "model": conversation.model_name,
            "createdAt": conversation.created_at.isoformat(),
            "updatedAt": conversation.updated_at.isoformat(),
            "messages": [
                {
                    "messageId": m.id,
                    "parentMessageId": m.parent_id,
                    "role": m.role,
                    "content": m.content,
                    "model": m.model_name,
                    "createdAt": m.created_at.isoformat(),
                }
                for m in messages
            ],
        }
        return json.dumps(data, indent=2)

    def _export_chatgpt(
        self,
        conversation: Conversation,
        messages: list[Message],
    ) -> str:
        """Export to ChatGPT format."""
        mapping = {}
        current_node = None

        for i, msg in enumerate(messages):
            node_id = str(uuid4())
            mapping[node_id] = {
                "id": node_id,
                "message": {
                    "id": msg.id,
                    "author": {"role": msg.role},
                    "content": {"parts": [msg.content]},
                    "create_time": msg.created_at.timestamp(),
                },
                "parent": current_node,
                "children": [],
            }

            if current_node and current_node in mapping:
                mapping[current_node]["children"].append(node_id)

            current_node = node_id

        data = {
            "title": conversation.title,
            "create_time": conversation.created_at.timestamp(),
            "update_time": conversation.updated_at.timestamp(),
            "mapping": mapping,
            "current_node": current_node,
        }

        return json.dumps(data, indent=2)
