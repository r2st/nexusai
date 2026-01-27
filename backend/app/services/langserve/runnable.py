"""
LangServe Runnable Wrapper for NexusAI Chat Service

Exposes ChatService as a LangChain Runnable for LangServe deployment.
"""

from typing import Any, AsyncIterator
from uuid import uuid4

from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.services.chat import ChatService
from app.models.conversation import ModelProvider
from app.services.agents.mcp import MCPServerConfig, MCPTransport

logger = structlog.get_logger()


class ChatRunnable(Runnable):
    """
    LangChain Runnable wrapper for NexusAI ChatService.
    
    This allows the chat service to be deployed via LangServe as a standard
    LangChain runnable with streaming support.
    """

    def __init__(
        self,
        db: AsyncSession,
        user_id: str,
        conversation_id: str | None = None,
        model_provider: ModelProvider | None = None,
        model_name: str | None = None,
        enable_mcp_tools: bool = True,
        mcp_servers: list[MCPServerConfig] | None = None,
    ):
        """Initialize the chat runnable.
        
        Args:
            db: Database session
            user_id: User ID for the chat session
            conversation_id: Optional conversation ID (creates new if None)
            model_provider: LLM provider to use
            model_name: Specific model name
            enable_mcp_tools: Whether to enable MCP tools
            mcp_servers: Optional external MCP server configs
        """
        self.db = db
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.model_provider = model_provider
        self.model_name = model_name
        self.enable_mcp_tools = enable_mcp_tools
        self.mcp_servers = mcp_servers or []
        
        # Initialize chat service
        self.chat_service = ChatService(
            db=db,
            user_id=user_id,
            mcp_servers=mcp_servers if mcp_servers else None,
            enable_builtin_tools=enable_mcp_tools,
        )

    async def ainvoke(
        self,
        input: dict[str, Any] | str | BaseMessage,
        config: RunnableConfig | None = None,
    ) -> dict[str, Any]:
        """Invoke the runnable (non-streaming).
        
        Args:
            input: Can be:
                - dict with 'message' key (optionally 'conversation_id')
                - str (message text)
                - BaseMessage (LangChain message)
            config: Runnable configuration
            
        Returns:
            Response dictionary with 'content' and metadata
        """
        # Extract message and conversation_id from input
        message = self._extract_message(input)
        if isinstance(input, dict) and "conversation_id" in input:
            self.conversation_id = input["conversation_id"]
        
        # Get or create conversation
        conversation = await self._get_or_create_conversation()
        
        # Initialize MCP if needed
        if self.enable_mcp_tools:
            await self.chat_service.initialize_mcp()
        
        try:
            # Get conversation messages for context
            messages = await self.chat_service.get_messages(conversation.id)
            
            # Call chat service (non-streaming)
            response_message = await self.chat_service.chat(
                conversation=conversation,
                user_message=message,
                temperature=0.7,
                max_tokens=4096,
            )
            
            await self.db.commit()
            
            return {
                "content": response_message.content,
                "message_id": str(response_message.id),
                "conversation_id": str(conversation.id),
                "model_name": response_message.model_name,
                "created_at": response_message.created_at.isoformat(),
            }
        finally:
            if self.enable_mcp_tools:
                await self.chat_service.cleanup_mcp()

    async def astream(
        self,
        input: dict[str, Any] | str | BaseMessage,
        config: RunnableConfig | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream the runnable response.
        
        Args:
            input: Can be:
                - dict with 'message' key (optionally 'conversation_id')
                - str (message text)
                - BaseMessage (LangChain message)
            config: Runnable configuration
            
        Yields:
            Chunks of the response as dicts with 'content' key
        """
        # Extract message and conversation_id from input
        message = self._extract_message(input)
        if isinstance(input, dict) and "conversation_id" in input:
            self.conversation_id = input["conversation_id"]
        
        # Get or create conversation
        conversation = await self._get_or_create_conversation()
        
        # Initialize MCP if needed
        if self.enable_mcp_tools:
            await self.chat_service.initialize_mcp()
        
        try:
            # Stream response
            full_content = ""
            async for chunk in self.chat_service.chat_stream(
                conversation=conversation,
                user_message=message,
                temperature=0.7,
                max_tokens=4096,
                use_mcp_tools=self.enable_mcp_tools,
            ):
                full_content += chunk
                yield {
                    "content": chunk,
                    "type": "content",
                }
            
            await self.db.commit()
            
            # Yield final message
            yield {
                "content": "",
                "type": "end",
                "full_content": full_content,
            }
        finally:
            if self.enable_mcp_tools:
                await self.chat_service.cleanup_mcp()

    def _extract_message(self, input: dict[str, Any] | str | BaseMessage) -> str:
        """Extract message text from various input formats."""
        if isinstance(input, str):
            return input
        elif isinstance(input, BaseMessage):
            if hasattr(input, 'content'):
                return str(input.content)
            return str(input)
        elif isinstance(input, dict):
            # Handle various dict formats
            if "message" in input:
                return str(input["message"])
            elif "content" in input:
                return str(input["content"])
            elif "input" in input:
                # Nested input
                return self._extract_message(input["input"])
            elif len(input) == 1 and "text" in input:
                # LangChain message format
                return str(input["text"])
            else:
                # Try to get first string value
                for value in input.values():
                    if isinstance(value, str):
                        return value
                raise ValueError(f"Could not extract message from dict: {input}")
        else:
            raise ValueError(f"Unsupported input type: {type(input)}")

    async def _get_or_create_conversation(self):
        """Get existing conversation or create a new one."""
        if self.conversation_id:
            conversation = await self.chat_service.get_conversation(
                self.conversation_id,
                self.user_id,
            )
            if conversation:
                return conversation
        
        # Create new conversation
        from app.api.chat import get_default_provider
        
        provider = self.model_provider or get_default_provider()
        
        conversation = await self.chat_service.create_conversation(
            user_id=self.user_id,
            title="LangServe Chat",
            model_provider=provider,
            model_name=self.model_name,
        )
        
        self.conversation_id = str(conversation.id)
        return conversation

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return the input schema for LangServe."""
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The user's message",
                },
                "conversation_id": {
                    "type": "string",
                    "description": "Optional conversation ID to continue a conversation",
                },
                "temperature": {
                    "type": "number",
                    "description": "Temperature for response generation",
                    "default": 0.7,
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens in response",
                    "default": 4096,
                },
            },
            "required": ["message"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        """Return the output schema for LangServe."""
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The assistant's response",
                },
                "message_id": {
                    "type": "string",
                    "description": "Message ID",
                },
                "conversation_id": {
                    "type": "string",
                    "description": "Conversation ID",
                },
                "model_name": {
                    "type": "string",
                    "description": "Model used for generation",
                },
            },
        }
