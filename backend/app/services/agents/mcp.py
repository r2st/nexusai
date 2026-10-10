"""Model Context Protocol (MCP) client and server implementation."""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

import httpx
import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


class MCPTransport(str, Enum):
    """MCP transport types."""

    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"
    WEBSOCKET = "websocket"


class MCPMessageType(str, Enum):
    """MCP message types."""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class MCPTool:
    """MCP tool definition."""

    name: str
    description: str
    input_schema: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class MCPResource:
    """MCP resource definition."""

    uri: str
    name: str
    description: str | None = None
    mime_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


@dataclass
class MCPPrompt:
    """MCP prompt definition."""

    name: str
    description: str | None = None
    arguments: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments,
        }


class MCPServerConfig(BaseModel):
    """MCP server configuration."""

    name: str
    transport: MCPTransport = MCPTransport.HTTP
    url: str | None = None
    command: str | None = None
    args: list[str] = []
    env: dict[str, str] = {}
    headers: dict[str, str] = {}
    timeout_seconds: int = 30


class MCPClient:
    """MCP client for connecting to MCP servers."""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self._http_client: httpx.AsyncClient | None = None
        self._websocket = None
        self._tools: dict[str, MCPTool] = {}
        self._resources: dict[str, MCPResource] = {}
        self._prompts: dict[str, MCPPrompt] = {}
        self._connected = False

    async def connect(self) -> bool:
        """Connect to the MCP server."""
        try:
            if self.config.transport == MCPTransport.HTTP:
                self._http_client = httpx.AsyncClient(
                    base_url=self.config.url,
                    headers=self.config.headers,
                    timeout=self.config.timeout_seconds,
                )
                # Initialize connection
                await self._initialize()
                self._connected = True
                return True

            elif self.config.transport == MCPTransport.SSE:
                # SSE transport
                self._http_client = httpx.AsyncClient(
                    base_url=self.config.url,
                    headers=self.config.headers,
                    timeout=None,  # SSE can be long-lived
                )
                await self._initialize()
                self._connected = True
                return True

            elif self.config.transport == MCPTransport.WEBSOCKET:
                # WebSocket transport - would need websockets library
                import websockets
                self._websocket = await websockets.connect(
                    self.config.url,
                    extra_headers=self.config.headers,
                )
                await self._initialize()
                self._connected = True
                return True

            elif self.config.transport == MCPTransport.STDIO:
                # STDIO transport for local processes
                # This would spawn a subprocess
                logger.warning("STDIO transport not fully implemented")
                return False

            return False

        except Exception as e:
            logger.error("Failed to connect to MCP server", error=str(e), server=self.config.name)
            return False

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        if self._websocket:
            await self._websocket.close()
            self._websocket = None

        self._connected = False

    async def _initialize(self) -> None:
        """Initialize the MCP connection and discover capabilities."""
        # List tools
        tools_response = await self._send_request("tools/list", {})
        if tools_response and "tools" in tools_response:
            for tool_data in tools_response["tools"]:
                tool = MCPTool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                )
                self._tools[tool.name] = tool

        # List resources
        resources_response = await self._send_request("resources/list", {})
        if resources_response and "resources" in resources_response:
            for res_data in resources_response["resources"]:
                resource = MCPResource(
                    uri=res_data["uri"],
                    name=res_data["name"],
                    description=res_data.get("description"),
                    mime_type=res_data.get("mimeType"),
                )
                self._resources[resource.uri] = resource

        # List prompts
        prompts_response = await self._send_request("prompts/list", {})
        if prompts_response and "prompts" in prompts_response:
            for prompt_data in prompts_response["prompts"]:
                prompt = MCPPrompt(
                    name=prompt_data["name"],
                    description=prompt_data.get("description"),
                    arguments=prompt_data.get("arguments", []),
                )
                self._prompts[prompt.name] = prompt

        logger.info(
            "MCP server initialized",
            server=self.config.name,
            tools=len(self._tools),
            resources=len(self._resources),
            prompts=len(self._prompts),
        )

    async def _send_request(
        self,
        method: str,
        params: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Send a JSON-RPC request to the MCP server."""
        request_id = str(uuid4())

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        try:
            if self._http_client:
                response = await self._http_client.post("/", json=payload)
                response.raise_for_status()
                result = response.json()

                if "error" in result:
                    logger.error(
                        "MCP request error",
                        method=method,
                        error=result["error"],
                    )
                    return None

                return result.get("result")

            elif self._websocket:
                await self._websocket.send(json.dumps(payload))
                response = await self._websocket.recv()
                result = json.loads(response)

                if "error" in result:
                    logger.error(
                        "MCP request error",
                        method=method,
                        error=result["error"],
                    )
                    return None

                return result.get("result")

            return None

        except Exception as e:
            logger.error(
                "MCP request failed",
                method=method,
                error=str(e),
            )
            return None

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Call a tool on the MCP server."""
        if not self._connected:
            logger.error("MCP client not connected")
            return None

        if tool_name not in self._tools:
            logger.error("Tool not found", tool=tool_name)
            return None

        return await self._send_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
        )

    async def read_resource(self, uri: str) -> dict[str, Any] | None:
        """Read a resource from the MCP server."""
        if not self._connected:
            return None

        return await self._send_request("resources/read", {"uri": uri})

    async def get_prompt(
        self,
        prompt_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Get a prompt from the MCP server."""
        if not self._connected:
            return None

        return await self._send_request(
            "prompts/get",
            {
                "name": prompt_name,
                "arguments": arguments or {},
            },
        )

    def list_tools(self) -> list[MCPTool]:
        """List available tools."""
        return list(self._tools.values())

    def list_resources(self) -> list[MCPResource]:
        """List available resources."""
        return list(self._resources.values())

    def list_prompts(self) -> list[MCPPrompt]:
        """List available prompts."""
        return list(self._prompts.values())

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    async def __aenter__(self) -> "MCPClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()


class MCPServer:
    """Simple MCP server implementation."""

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self._tools: dict[str, tuple[MCPTool, Callable]] = {}
        self._resources: dict[str, MCPResource] = {}
        self._prompts: dict[str, MCPPrompt] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Callable,
    ) -> None:
        """Register a tool with its handler."""
        tool = MCPTool(
            name=name,
            description=description,
            input_schema=input_schema,
        )
        self._tools[name] = (tool, handler)
        logger.info("MCP tool registered", tool=name)

    def register_resource(self, resource: MCPResource) -> None:
        """Register a resource."""
        self._resources[resource.uri] = resource
        logger.info("MCP resource registered", uri=resource.uri)

    def register_prompt(self, prompt: MCPPrompt) -> None:
        """Register a prompt."""
        self._prompts[prompt.name] = prompt
        logger.info("MCP prompt registered", prompt=prompt.name)

    async def handle_request(
        self,
        method: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle an incoming MCP request."""
        handlers = {
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "prompts/list": self._handle_prompts_list,
            "prompts/get": self._handle_prompts_get,
            "initialize": self._handle_initialize,
        }

        handler = handlers.get(method)
        if not handler:
            return {"error": {"code": -32601, "message": f"Method not found: {method}"}}

        try:
            return await handler(params)
        except Exception as e:
            logger.error("MCP handler error", method=method, error=str(e))
            return {"error": {"code": -32603, "message": "Internal error processing request"}}

    async def _handle_initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request."""
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": self.name,
                "version": self.version,
            },
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True},
                "prompts": {"listChanged": True},
            },
        }

    async def _handle_tools_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tools/list request."""
        return {
            "tools": [tool.to_dict() for tool, _ in self._tools.values()]
        }

    async def _handle_tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self._tools:
            return {"error": {"code": -32602, "message": f"Tool not found: {tool_name}"}}

        _, handler = self._tools[tool_name]

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result) if not isinstance(result, str) else result,
                    }
                ]
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True,
            }

    async def _handle_resources_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle resources/list request."""
        return {
            "resources": [res.to_dict() for res in self._resources.values()]
        }

    async def _handle_resources_read(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri")

        if uri not in self._resources:
            return {"error": {"code": -32602, "message": f"Resource not found: {uri}"}}

        # For now, return empty content - real implementation would fetch the resource
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": self._resources[uri].mime_type or "text/plain",
                    "text": "",
                }
            ]
        }

    async def _handle_prompts_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle prompts/list request."""
        return {
            "prompts": [prompt.to_dict() for prompt in self._prompts.values()]
        }

    async def _handle_prompts_get(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle prompts/get request."""
        prompt_name = params.get("name")

        if prompt_name not in self._prompts:
            return {"error": {"code": -32602, "message": f"Prompt not found: {prompt_name}"}}

        prompt = self._prompts[prompt_name]

        # Return the prompt template
        return {
            "description": prompt.description,
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Prompt: {prompt_name}",
                    },
                }
            ],
        }


# MCP client manager for multi-user support
class MCPClientManager:
    """Manager for multiple MCP client connections."""

    def __init__(self):
        self._clients: dict[str, dict[str, MCPClient]] = {}  # user_id -> {server_name -> client}

    async def connect_server(
        self,
        user_id: str,
        config: MCPServerConfig,
    ) -> bool:
        """Connect a user to an MCP server."""
        if user_id not in self._clients:
            self._clients[user_id] = {}

        client = MCPClient(config)
        success = await client.connect()

        if success:
            self._clients[user_id][config.name] = client

        return success

    async def disconnect_server(self, user_id: str, server_name: str) -> None:
        """Disconnect a user from an MCP server."""
        if user_id in self._clients and server_name in self._clients[user_id]:
            await self._clients[user_id][server_name].disconnect()
            del self._clients[user_id][server_name]

    async def disconnect_all(self, user_id: str) -> None:
        """Disconnect a user from all MCP servers."""
        if user_id in self._clients:
            for client in self._clients[user_id].values():
                await client.disconnect()
            del self._clients[user_id]

    def get_client(self, user_id: str, server_name: str) -> MCPClient | None:
        """Get an MCP client for a user."""
        return self._clients.get(user_id, {}).get(server_name)

    def list_connected_servers(self, user_id: str) -> list[str]:
        """List connected servers for a user."""
        return list(self._clients.get(user_id, {}).keys())

    async def call_tool(
        self,
        user_id: str,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Call a tool on an MCP server."""
        client = self.get_client(user_id, server_name)
        if not client:
            return None

        return await client.call_tool(tool_name, arguments)


# Global MCP client manager
mcp_manager = MCPClientManager()
