"""
MCP Protocol Types

Defines the core MCP protocol types for communication.
Based on the Model Context Protocol specification.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import json


class MCPMessageType(str, Enum):
    """MCP message types."""
    # Lifecycle
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"
    SHUTDOWN = "shutdown"
    
    # Tools
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    
    # Resources
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    
    # Prompts
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"
    
    # Completion
    COMPLETION = "completion/complete"
    
    # Sampling
    SAMPLING_CREATE = "sampling/createMessage"
    
    # Logging
    LOGGING_SET_LEVEL = "logging/setLevel"
    
    # Notifications
    NOTIFICATION = "notification"


@dataclass
class MCPToolParameter:
    """Parameter definition for an MCP tool."""
    name: str
    type: str
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Any = None


@dataclass
class MCPTool:
    """An MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPTool":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            input_schema=data.get("inputSchema", {}),
        )


@dataclass
class MCPResource:
    """An MCP resource definition."""
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "uri": self.uri,
            "name": self.name,
        }
        if self.description:
            result["description"] = self.description
        if self.mime_type:
            result["mimeType"] = self.mime_type
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPResource":
        return cls(
            uri=data["uri"],
            name=data["name"],
            description=data.get("description"),
            mime_type=data.get("mimeType"),
        )


@dataclass
class MCPResourceContent:
    """Content of an MCP resource."""
    uri: str
    mime_type: str
    text: Optional[str] = None
    blob: Optional[str] = None  # Base64 encoded
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "uri": self.uri,
            "mimeType": self.mime_type,
        }
        if self.text is not None:
            result["text"] = self.text
        if self.blob is not None:
            result["blob"] = self.blob
        return result


@dataclass
class MCPPromptArgument:
    """Argument for an MCP prompt."""
    name: str
    description: Optional[str] = None
    required: bool = False


@dataclass
class MCPPrompt:
    """An MCP prompt definition."""
    name: str
    description: Optional[str] = None
    arguments: List[MCPPromptArgument] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"name": self.name}
        if self.description:
            result["description"] = self.description
        if self.arguments:
            result["arguments"] = [
                {
                    "name": arg.name,
                    "description": arg.description,
                    "required": arg.required,
                }
                for arg in self.arguments
            ]
        return result


@dataclass
class MCPMessage:
    """An MCP message content item."""
    type: str  # "text" or "image"
    text: Optional[str] = None
    data: Optional[str] = None  # Base64 for images
    mime_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"type": self.type}
        if self.text:
            result["text"] = self.text
        if self.data:
            result["data"] = self.data
        if self.mime_type:
            result["mimeType"] = self.mime_type
        return result


@dataclass
class MCPRequest:
    """An MCP JSON-RPC request."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        data = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
        }
        if self.id is not None:
            data["id"] = self.id
        if self.params:
            data["params"] = self.params
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, data: str) -> "MCPRequest":
        parsed = json.loads(data)
        return cls(
            jsonrpc=parsed.get("jsonrpc", "2.0"),
            id=parsed.get("id"),
            method=parsed.get("method", ""),
            params=parsed.get("params", {}),
        )


@dataclass
class MCPError:
    """An MCP error."""
    code: int
    message: str
    data: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "code": self.code,
            "message": self.message,
        }
        if self.data is not None:
            result["data"] = self.data
        return result


# Standard error codes
class MCPErrorCode:
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


@dataclass
class MCPResponse:
    """An MCP JSON-RPC response."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[MCPError] = None
    
    def to_json(self) -> str:
        data = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            data["id"] = self.id
        if self.error:
            data["error"] = self.error.to_dict()
        else:
            data["result"] = self.result
        return json.dumps(data)
    
    @classmethod
    def success(cls, id: Union[str, int], result: Any) -> "MCPResponse":
        return cls(id=id, result=result)
    
    @classmethod
    def error(
        cls,
        id: Optional[Union[str, int]],
        code: int,
        message: str,
        data: Any = None,
    ) -> "MCPResponse":
        return cls(id=id, error=MCPError(code=code, message=message, data=data))


@dataclass
class MCPServerCapabilities:
    """Capabilities advertised by an MCP server."""
    tools: bool = False
    resources: bool = False
    prompts: bool = False
    logging: bool = False
    
    # Resource capabilities
    resource_subscriptions: bool = False
    resource_list_changed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        caps = {}
        if self.tools:
            caps["tools"] = {}
        if self.resources:
            res_caps = {}
            if self.resource_subscriptions:
                res_caps["subscribe"] = True
            if self.resource_list_changed:
                res_caps["listChanged"] = True
            caps["resources"] = res_caps if res_caps else {}
        if self.prompts:
            caps["prompts"] = {}
        if self.logging:
            caps["logging"] = {}
        return caps


@dataclass
class MCPClientCapabilities:
    """Capabilities sent by an MCP client."""
    roots: bool = False
    sampling: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        caps = {}
        if self.roots:
            caps["roots"] = {"listChanged": True}
        if self.sampling:
            caps["sampling"] = {}
        return caps


@dataclass
class MCPServerInfo:
    """Information about an MCP server."""
    name: str
    version: str
    protocol_version: str = "2024-11-05"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "protocolVersion": self.protocol_version,
        }


@dataclass
class MCPClientInfo:
    """Information about an MCP client."""
    name: str
    version: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
        }
