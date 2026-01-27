"""
MCP Client Implementation

Connects to external MCP servers to consume their tools.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import asyncio
import json
import logging
import uuid

from .protocol import (
    MCPRequest,
    MCPResponse,
    MCPTool,
    MCPResource,
    MCPMessageType,
    MCPClientInfo,
    MCPClientCapabilities,
)

logger = logging.getLogger(__name__)


@dataclass
class MCPClientConfig:
    """Configuration for MCP client."""
    name: str = "NexusAI-Client"
    version: str = "1.0.0"
    
    # Connection
    connect_timeout: int = 10
    request_timeout: int = 30
    
    # Retry
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class MCPServerConnection:
    """A connection to an MCP server."""
    server_name: str
    server_version: str
    protocol_version: str
    capabilities: Dict[str, Any]
    tools: List[MCPTool] = field(default_factory=list)
    resources: List[MCPResource] = field(default_factory=list)


class MCPTransport:
    """Abstract transport for MCP communication."""
    
    async def send(self, message: str) -> None:
        raise NotImplementedError
    
    async def receive(self) -> str:
        raise NotImplementedError
    
    async def close(self) -> None:
        raise NotImplementedError


class StdioTransport(MCPTransport):
    """Transport over stdio (for local MCP servers)."""
    
    def __init__(self, process: asyncio.subprocess.Process):
        self.process = process
    
    async def send(self, message: str) -> None:
        if self.process.stdin:
            self.process.stdin.write((message + "\n").encode())
            await self.process.stdin.drain()
    
    async def receive(self) -> str:
        if self.process.stdout:
            line = await self.process.stdout.readline()
            return line.decode().strip()
        return ""
    
    async def close(self) -> None:
        self.process.terminate()
        await self.process.wait()


class WebSocketTransport(MCPTransport):
    """Transport over WebSocket (for remote MCP servers)."""
    
    def __init__(self, websocket):
        self.websocket = websocket
    
    async def send(self, message: str) -> None:
        await self.websocket.send(message)
    
    async def receive(self) -> str:
        return await self.websocket.recv()
    
    async def close(self) -> None:
        await self.websocket.close()


class MCPClient:
    """
    MCP Client for connecting to external MCP servers.
    
    Features:
    - Connect to stdio or WebSocket MCP servers
    - Discover and use tools
    - Access resources
    - Route through NexusAI's tool system
    """
    
    def __init__(self, config: Optional[MCPClientConfig] = None):
        self.config = config or MCPClientConfig()
        self._transport: Optional[MCPTransport] = None
        self._connection: Optional[MCPServerConnection] = None
        self._request_id = 0
        self._pending: Dict[int, asyncio.Future] = {}
        self._receive_task: Optional[asyncio.Task] = None
    
    @property
    def client_info(self) -> MCPClientInfo:
        return MCPClientInfo(
            name=self.config.name,
            version=self.config.version,
        )
    
    @property
    def is_connected(self) -> bool:
        return self._connection is not None
    
    @property
    def tools(self) -> List[MCPTool]:
        return self._connection.tools if self._connection else []
    
    @property
    def resources(self) -> List[MCPResource]:
        return self._connection.resources if self._connection else []
    
    async def connect_stdio(self, command: List[str]) -> MCPServerConnection:
        """Connect to an MCP server via stdio."""
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        self._transport = StdioTransport(process)
        return await self._initialize()
    
    async def connect_websocket(self, url: str) -> MCPServerConnection:
        """Connect to an MCP server via WebSocket."""
        try:
            import websockets
            
            websocket = await websockets.connect(
                url,
                close_timeout=self.config.connect_timeout,
            )
            
            self._transport = WebSocketTransport(websocket)
            return await self._initialize()
            
        except ImportError:
            raise RuntimeError("websockets package required for WebSocket transport")
    
    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if self._transport:
            # Send shutdown
            try:
                await self._send_request(MCPMessageType.SHUTDOWN, {})
            except Exception:
                pass
            
            await self._transport.close()
            self._transport = None
        
        self._connection = None
    
    async def _initialize(self) -> MCPServerConnection:
        """Initialize the connection with the server."""
        # Start receive loop
        self._receive_task = asyncio.create_task(self._receive_loop())
        
        # Send initialize
        response = await self._send_request(
            MCPMessageType.INITIALIZE,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": MCPClientCapabilities().to_dict(),
                "clientInfo": self.client_info.to_dict(),
            },
        )
        
        if response.error:
            raise RuntimeError(f"Initialize failed: {response.error.message}")
        
        result = response.result
        
        # Create connection info
        server_info = result.get("serverInfo", {})
        self._connection = MCPServerConnection(
            server_name=server_info.get("name", "unknown"),
            server_version=server_info.get("version", "unknown"),
            protocol_version=result.get("protocolVersion", "unknown"),
            capabilities=result.get("capabilities", {}),
        )
        
        # Discover tools and resources
        if self._connection.capabilities.get("tools"):
            await self._discover_tools()
        
        if self._connection.capabilities.get("resources"):
            await self._discover_resources()
        
        logger.info(
            f"Connected to MCP server: {self._connection.server_name} "
            f"({len(self._connection.tools)} tools, {len(self._connection.resources)} resources)"
        )
        
        return self._connection
    
    async def _discover_tools(self) -> None:
        """Discover available tools."""
        response = await self._send_request(MCPMessageType.TOOLS_LIST, {})
        
        if response.result:
            self._connection.tools = [
                MCPTool.from_dict(t)
                for t in response.result.get("tools", [])
            ]
    
    async def _discover_resources(self) -> None:
        """Discover available resources."""
        response = await self._send_request(MCPMessageType.RESOURCES_LIST, {})
        
        if response.result:
            self._connection.resources = [
                MCPResource.from_dict(r)
                for r in response.result.get("resources", [])
            ]
    
    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """Call a tool on the MCP server."""
        response = await self._send_request(
            MCPMessageType.TOOLS_CALL,
            {
                "name": name,
                "arguments": arguments,
            },
        )
        
        if response.error:
            raise RuntimeError(f"Tool call failed: {response.error.message}")
        
        # Extract content
        content = response.result.get("content", [])
        if len(content) == 1 and content[0].get("type") == "text":
            text = content[0].get("text", "")
            # Try to parse as JSON
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        
        return content
    
    async def read_resource(self, uri: str) -> Any:
        """Read a resource from the MCP server."""
        response = await self._send_request(
            MCPMessageType.RESOURCES_READ,
            {"uri": uri},
        )
        
        if response.error:
            raise RuntimeError(f"Resource read failed: {response.error.message}")
        
        contents = response.result.get("contents", [])
        if contents:
            return contents[0]
        return None
    
    async def _send_request(
        self,
        method: str,
        params: Dict[str, Any],
    ) -> MCPResponse:
        """Send a request and wait for response."""
        if not self._transport:
            raise RuntimeError("Not connected")
        
        self._request_id += 1
        request_id = self._request_id
        
        request = MCPRequest(
            id=request_id,
            method=method,
            params=params,
        )
        
        # Create future for response
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future
        
        try:
            # Send request
            await self._transport.send(request.to_json())
            
            # Wait for response
            response = await asyncio.wait_for(
                future,
                timeout=self.config.request_timeout,
            )
            
            return response
            
        except asyncio.TimeoutError:
            del self._pending[request_id]
            raise RuntimeError("Request timed out")
        finally:
            if request_id in self._pending:
                del self._pending[request_id]
    
    async def _receive_loop(self) -> None:
        """Receive and dispatch responses."""
        while self._transport:
            try:
                message = await self._transport.receive()
                if not message:
                    continue
                
                data = json.loads(message)
                
                # Check if it's a response
                if "id" in data and data["id"] in self._pending:
                    response = MCPResponse(
                        id=data["id"],
                        result=data.get("result"),
                        error=data.get("error"),
                    )
                    self._pending[data["id"]].set_result(response)
                
                # Could also handle notifications here
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Receive error: {e}")


class MCPServerRegistry:
    """
    Registry of configured MCP servers.
    
    Manages connections to multiple MCP servers and provides
    unified access to their tools.
    """
    
    def __init__(self):
        self._servers: Dict[str, Dict[str, Any]] = {}
        self._clients: Dict[str, MCPClient] = {}
    
    def register(
        self,
        name: str,
        type: str,  # "stdio" or "websocket"
        connection: str,  # command or URL
        **kwargs,
    ) -> None:
        """Register an MCP server."""
        self._servers[name] = {
            "type": type,
            "connection": connection,
            **kwargs,
        }
        logger.info(f"Registered MCP server: {name}")
    
    async def connect(self, name: str) -> MCPClient:
        """Connect to a registered MCP server."""
        if name in self._clients:
            return self._clients[name]
        
        if name not in self._servers:
            raise ValueError(f"Unknown MCP server: {name}")
        
        config = self._servers[name]
        client = MCPClient()
        
        if config["type"] == "stdio":
            command = config["connection"]
            if isinstance(command, str):
                command = command.split()
            await client.connect_stdio(command)
        elif config["type"] == "websocket":
            await client.connect_websocket(config["connection"])
        else:
            raise ValueError(f"Unknown connection type: {config['type']}")
        
        self._clients[name] = client
        return client
    
    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        for client in self._clients.values():
            await client.disconnect()
        self._clients.clear()
    
    def list_all_tools(self) -> Dict[str, List[MCPTool]]:
        """List all tools from all connected servers."""
        return {
            name: client.tools
            for name, client in self._clients.items()
        }


# Global registry
mcp_server_registry = MCPServerRegistry()
