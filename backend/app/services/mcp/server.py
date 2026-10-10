"""
MCP Server Implementation

Exposes NexusAI capabilities as MCP tools and resources.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type
import asyncio
import json
import logging

from .protocol import (
    MCPRequest,
    MCPResponse,
    MCPTool,
    MCPResource,
    MCPResourceContent,
    MCPPrompt,
    MCPServerCapabilities,
    MCPServerInfo,
    MCPError,
    MCPErrorCode,
    MCPMessageType,
)

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for MCP server."""
    name: str = "NexusAI"
    version: str = "1.0.0"
    
    # Enabled features
    enable_tools: bool = True
    enable_resources: bool = True
    enable_prompts: bool = True
    enable_logging: bool = True
    
    # Security
    require_auth: bool = True
    allowed_origins: List[str] = field(default_factory=list)
    
    # Limits
    max_concurrent_requests: int = 100
    request_timeout: int = 30


class MCPToolHandler(ABC):
    """Handler for an MCP tool."""
    
    @property
    @abstractmethod
    def tool(self) -> MCPTool:
        """Return the tool definition."""
        pass
    
    @abstractmethod
    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """Execute the tool."""
        pass


class MCPResourceHandler(ABC):
    """Handler for MCP resources."""
    
    @property
    @abstractmethod
    def resource(self) -> MCPResource:
        """Return the resource definition."""
        pass
    
    @abstractmethod
    async def read(self, uri: str, context: Dict[str, Any]) -> MCPResourceContent:
        """Read the resource content."""
        pass


class MCPServer:
    """
    MCP Server that exposes NexusAI capabilities.
    
    Implements the MCP protocol to allow external LLM clients
    (Claude, Cursor, etc.) to use NexusAI tools.
    """
    
    def __init__(self, config: Optional[MCPServerConfig] = None):
        self.config = config or MCPServerConfig()
        
        # Handlers
        self._tools: Dict[str, MCPToolHandler] = {}
        self._resources: Dict[str, MCPResourceHandler] = {}
        self._prompts: Dict[str, MCPPrompt] = {}
        
        # State
        self._initialized = False
        self._client_info: Optional[Dict[str, Any]] = None
    
    @property
    def capabilities(self) -> MCPServerCapabilities:
        """Get server capabilities."""
        return MCPServerCapabilities(
            tools=self.config.enable_tools and len(self._tools) > 0,
            resources=self.config.enable_resources and len(self._resources) > 0,
            prompts=self.config.enable_prompts and len(self._prompts) > 0,
            logging=self.config.enable_logging,
        )
    
    @property
    def server_info(self) -> MCPServerInfo:
        """Get server info."""
        return MCPServerInfo(
            name=self.config.name,
            version=self.config.version,
        )
    
    def register_tool(self, handler: MCPToolHandler) -> None:
        """Register a tool handler."""
        tool = handler.tool
        self._tools[tool.name] = handler
        logger.info(f"Registered MCP tool: {tool.name}")
    
    def register_resource(self, handler: MCPResourceHandler) -> None:
        """Register a resource handler."""
        resource = handler.resource
        self._resources[resource.uri] = handler
        logger.info(f"Registered MCP resource: {resource.uri}")
    
    def register_prompt(self, prompt: MCPPrompt) -> None:
        """Register a prompt."""
        self._prompts[prompt.name] = prompt
        logger.info(f"Registered MCP prompt: {prompt.name}")
    
    async def handle_request(
        self,
        request: MCPRequest,
        context: Optional[Dict[str, Any]] = None,
    ) -> MCPResponse:
        """
        Handle an incoming MCP request.
        
        Args:
            request: The MCP request
            context: Request context (auth, tenant, etc.)
            
        Returns:
            MCPResponse
        """
        context = context or {}
        
        try:
            method = request.method
            params = request.params
            
            # Route to handler
            if method == MCPMessageType.INITIALIZE:
                return await self._handle_initialize(request.id, params)
            
            # Require initialization for other methods
            if not self._initialized and method != MCPMessageType.INITIALIZE:
                return MCPResponse.error(
                    request.id,
                    MCPErrorCode.INVALID_REQUEST,
                    "Server not initialized",
                )
            
            if method == MCPMessageType.TOOLS_LIST:
                return await self._handle_tools_list(request.id)
            
            elif method == MCPMessageType.TOOLS_CALL:
                return await self._handle_tools_call(request.id, params, context)
            
            elif method == MCPMessageType.RESOURCES_LIST:
                return await self._handle_resources_list(request.id)
            
            elif method == MCPMessageType.RESOURCES_READ:
                return await self._handle_resources_read(request.id, params, context)
            
            elif method == MCPMessageType.PROMPTS_LIST:
                return await self._handle_prompts_list(request.id)
            
            elif method == MCPMessageType.PROMPTS_GET:
                return await self._handle_prompts_get(request.id, params)
            
            elif method == MCPMessageType.SHUTDOWN:
                return await self._handle_shutdown(request.id)
            
            else:
                return MCPResponse.error(
                    request.id,
                    MCPErrorCode.METHOD_NOT_FOUND,
                    f"Unknown method: {method}",
                )
                
        except Exception as e:
            logger.exception(f"Error handling MCP request: {e}")
            return MCPResponse.error(
                request.id,
                MCPErrorCode.INTERNAL_ERROR,
                str(e),
            )
    
    async def _handle_initialize(
        self,
        id: Any,
        params: Dict[str, Any],
    ) -> MCPResponse:
        """Handle initialize request."""
        self._client_info = params.get("clientInfo")
        self._initialized = True
        
        logger.info(f"MCP client initialized: {self._client_info}")
        
        return MCPResponse.success(id, {
            "protocolVersion": "2024-11-05",
            "capabilities": self.capabilities.to_dict(),
            "serverInfo": self.server_info.to_dict(),
        })
    
    async def _handle_tools_list(self, id: Any) -> MCPResponse:
        """Handle tools/list request."""
        tools = [handler.tool.to_dict() for handler in self._tools.values()]
        return MCPResponse.success(id, {"tools": tools})
    
    async def _handle_tools_call(
        self,
        id: Any,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> MCPResponse:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            return MCPResponse.error(
                id,
                MCPErrorCode.INVALID_PARAMS,
                "Missing tool name",
            )
        
        handler = self._tools.get(tool_name)
        if not handler:
            return MCPResponse.error(
                id,
                MCPErrorCode.INVALID_PARAMS,
                f"Unknown tool: {tool_name}",
            )
        
        try:
            result = await asyncio.wait_for(
                handler.execute(arguments, context),
                timeout=self.config.request_timeout,
            )
            
            # Format result as content array
            if isinstance(result, str):
                content = [{"type": "text", "text": result}]
            elif isinstance(result, dict):
                content = [{"type": "text", "text": json.dumps(result, indent=2)}]
            elif isinstance(result, list):
                content = result
            else:
                content = [{"type": "text", "text": str(result)}]
            
            return MCPResponse.success(id, {"content": content})
            
        except asyncio.TimeoutError:
            return MCPResponse.error(
                id,
                MCPErrorCode.INTERNAL_ERROR,
                "Tool execution timed out",
            )
        except Exception as e:
            logger.exception(f"Tool execution error: {e}")
            return MCPResponse.error(
                id,
                MCPErrorCode.INTERNAL_ERROR,
                f"Tool execution failed: {str(e)}",
            )
    
    async def _handle_resources_list(self, id: Any) -> MCPResponse:
        """Handle resources/list request."""
        resources = [handler.resource.to_dict() for handler in self._resources.values()]
        return MCPResponse.success(id, {"resources": resources})
    
    async def _handle_resources_read(
        self,
        id: Any,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> MCPResponse:
        """Handle resources/read request."""
        uri = params.get("uri")
        
        if not uri:
            return MCPResponse.error(
                id,
                MCPErrorCode.INVALID_PARAMS,
                "Missing resource URI",
            )
        
        # Find matching handler
        handler = None
        for pattern, h in self._resources.items():
            if uri.startswith(pattern.rstrip("*")):
                handler = h
                break
        
        if not handler:
            return MCPResponse.error(
                id,
                MCPErrorCode.INVALID_PARAMS,
                f"Unknown resource: {uri}",
            )
        
        try:
            content = await handler.read(uri, context)
            return MCPResponse.success(id, {
                "contents": [content.to_dict()],
            })
            
        except Exception as e:
            logger.exception(f"Resource read error: {e}")
            return MCPResponse.error(
                id,
                MCPErrorCode.INTERNAL_ERROR,
                f"Resource read failed: {str(e)}",
            )
    
    async def _handle_prompts_list(self, id: Any) -> MCPResponse:
        """Handle prompts/list request."""
        prompts = [prompt.to_dict() for prompt in self._prompts.values()]
        return MCPResponse.success(id, {"prompts": prompts})
    
    async def _handle_prompts_get(
        self,
        id: Any,
        params: Dict[str, Any],
    ) -> MCPResponse:
        """Handle prompts/get request."""
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not name:
            return MCPResponse.error(
                id,
                MCPErrorCode.INVALID_PARAMS,
                "Missing prompt name",
            )
        
        prompt = self._prompts.get(name)
        if not prompt:
            return MCPResponse.error(
                id,
                MCPErrorCode.INVALID_PARAMS,
                f"Unknown prompt: {name}",
            )
        
        # Generate prompt messages (would use template engine)
        messages = [
            {
                "role": "user",
                "content": {"type": "text", "text": f"Prompt: {name}"},
            }
        ]
        
        return MCPResponse.success(id, {
            "description": prompt.description,
            "messages": messages,
        })
    
    async def _handle_shutdown(self, id: Any) -> MCPResponse:
        """Handle shutdown request."""
        self._initialized = False
        logger.info("MCP server shutting down")
        return MCPResponse.success(id, {})


# =============================================================================
# Built-in Tool Handlers
# =============================================================================

class CodeSearchToolHandler(MCPToolHandler):
    """MCP handler for code search."""
    
    def __init__(self, search_service):
        self.search_service = search_service
    
    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="search_code",
            description="Search for code across repositories using semantic or keyword search",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "repo": {
                        "type": "string",
                        "description": "Repository to search (optional)",
                    },
                    "language": {
                        "type": "string",
                        "description": "Filter by programming language",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results (default 10)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        )
    
    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        # Would call actual search service
        return {
            "results": [
                {
                    "file": "src/auth/login.py",
                    "line": 42,
                    "content": "def authenticate_user(...):",
                    "score": 0.95,
                }
            ]
        }


class FileReadToolHandler(MCPToolHandler):
    """MCP handler for reading files."""
    
    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="read_file",
            description="Read contents of a file from a repository",
            input_schema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository (owner/repo)",
                    },
                    "path": {
                        "type": "string",
                        "description": "File path",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch (default: main)",
                        "default": "main",
                    },
                },
                "required": ["repo", "path"],
            },
        )
    
    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        # Would call file service
        return "# File contents here..."


class CILogsToolHandler(MCPToolHandler):
    """MCP handler for CI/CD logs."""
    
    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="get_ci_logs",
            description="Get CI/CD build logs and test results",
            input_schema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository",
                    },
                    "build_id": {
                        "type": "string",
                        "description": "Build ID (optional, gets latest if omitted)",
                    },
                    "log_type": {
                        "type": "string",
                        "enum": ["all", "failed", "tests"],
                        "description": "Type of logs to retrieve",
                        "default": "failed",
                    },
                },
                "required": ["repo"],
            },
        )
    
    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        # Would call CI service
        return {
            "status": "failed",
            "failed_tests": [
                {"name": "test_auth", "error": "AssertionError"}
            ]
        }
