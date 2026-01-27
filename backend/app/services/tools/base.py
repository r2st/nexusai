"""
Tool Base Classes

Defines the abstract interface for all tools in the platform.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel, Field
import uuid


class ParameterType(str, Enum):
    """Supported parameter types for tools."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolCategory(str, Enum):
    """Tool categories for organization and routing."""
    CODE = "code"
    SEARCH = "search"
    ANALYSIS = "analysis"
    INTEGRATION = "integration"
    DOCUMENTATION = "documentation"
    SECURITY = "security"
    CI_CD = "ci_cd"
    OBSERVABILITY = "observability"
    COMMUNICATION = "communication"
    DATA = "data"


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None  # Regex for string validation
    items_type: Optional[ParameterType] = None  # For array types


@dataclass
class ToolMetadata:
    """Metadata describing a tool's capabilities and requirements."""
    name: str
    description: str
    category: ToolCategory
    version: str = "1.0.0"
    
    # Parameters
    parameters: List[ToolParameter] = field(default_factory=list)
    
    # Permissions
    required_permissions: List[str] = field(default_factory=list)
    min_role: str = "user"  # Minimum role required
    
    # Execution constraints
    timeout_seconds: int = 30
    max_retries: int = 3
    is_idempotent: bool = False
    requires_confirmation: bool = False  # Human-in-the-loop
    
    # Rate limiting
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_hour: Optional[int] = None
    
    # Cost tracking
    estimated_cost_per_call: float = 0.0
    cost_unit: str = "credits"
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # Other tool names
    
    # Documentation
    examples: List[Dict[str, Any]] = field(default_factory=list)
    long_description: Optional[str] = None


class ToolResultStatus(str, Enum):
    """Status of a tool execution result."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    PERMISSION_DENIED = "permission_denied"
    VALIDATION_ERROR = "validation_error"
    PENDING_APPROVAL = "pending_approval"


@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool_name: str
    status: ToolResultStatus
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    # Execution metadata
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    # Cost tracking
    tokens_used: int = 0
    cost_incurred: float = 0.0
    
    # For streaming results
    is_partial: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool_name": self.tool_name,
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code,
            "execution_id": self.execution_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "cost_incurred": self.cost_incurred,
            "is_partial": self.is_partial,
        }
    
    @classmethod
    def success(cls, tool_name: str, data: Any, **kwargs) -> "ToolResult":
        """Create a successful result."""
        return cls(
            tool_name=tool_name,
            status=ToolResultStatus.SUCCESS,
            data=data,
            completed_at=datetime.utcnow(),
            **kwargs,
        )
    
    @classmethod
    def error(cls, tool_name: str, error: str, error_code: str = "UNKNOWN", **kwargs) -> "ToolResult":
        """Create an error result."""
        return cls(
            tool_name=tool_name,
            status=ToolResultStatus.ERROR,
            error=error,
            error_code=error_code,
            completed_at=datetime.utcnow(),
            **kwargs,
        )


T = TypeVar("T", bound="Tool")


class Tool(ABC):
    """
    Abstract base class for all tools.
    
    Tools are the building blocks for LLM function calling.
    Each tool must:
    - Define its metadata (name, description, parameters)
    - Implement the execute method
    - Handle errors gracefully
    """
    
    @classmethod
    @abstractmethod
    def get_metadata(cls) -> ToolMetadata:
        """Return the tool's metadata."""
        pass
    
    @abstractmethod
    async def execute(
        self,
        params: Dict[str, Any],
        context: "ExecutionContext",
    ) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            params: Validated parameters from the LLM
            context: Execution context with tenant/user info
            
        Returns:
            ToolResult with success/error status and data
        """
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """
        Validate parameters against metadata.
        
        Returns None if valid, or error message if invalid.
        Override for custom validation.
        """
        metadata = self.get_metadata()
        
        for param in metadata.parameters:
            value = params.get(param.name)
            
            # Check required
            if param.required and value is None:
                return f"Missing required parameter: {param.name}"
            
            if value is not None:
                # Type validation
                if param.type == ParameterType.STRING and not isinstance(value, str):
                    return f"Parameter {param.name} must be a string"
                elif param.type == ParameterType.INTEGER and not isinstance(value, int):
                    return f"Parameter {param.name} must be an integer"
                elif param.type == ParameterType.NUMBER and not isinstance(value, (int, float)):
                    return f"Parameter {param.name} must be a number"
                elif param.type == ParameterType.BOOLEAN and not isinstance(value, bool):
                    return f"Parameter {param.name} must be a boolean"
                elif param.type == ParameterType.ARRAY and not isinstance(value, list):
                    return f"Parameter {param.name} must be an array"
                elif param.type == ParameterType.OBJECT and not isinstance(value, dict):
                    return f"Parameter {param.name} must be an object"
                
                # Enum validation
                if param.enum and value not in param.enum:
                    return f"Parameter {param.name} must be one of: {param.enum}"
                
                # Range validation
                if param.min_value is not None and value < param.min_value:
                    return f"Parameter {param.name} must be >= {param.min_value}"
                if param.max_value is not None and value > param.max_value:
                    return f"Parameter {param.name} must be <= {param.max_value}"
        
        return None
    
    def to_openai_function(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        metadata = self.get_metadata()
        
        properties = {}
        required = []
        
        for param in metadata.parameters:
            prop = {
                "type": param.type.value,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
                
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "name": metadata.name,
            "description": metadata.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }
    
    def to_anthropic_tool(self) -> Dict[str, Any]:
        """Convert to Anthropic tool calling format."""
        metadata = self.get_metadata()
        
        input_schema = {
            "type": "object",
            "properties": {},
            "required": [],
        }
        
        for param in metadata.parameters:
            prop = {
                "type": param.type.value,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
                
            input_schema["properties"][param.name] = prop
            
            if param.required:
                input_schema["required"].append(param.name)
        
        return {
            "name": metadata.name,
            "description": metadata.description,
            "input_schema": input_schema,
        }


# Type alias for tool classes
ToolClass = Type[Tool]


class ExecutionContext(BaseModel):
    """Context for tool execution with tenant/user information."""
    
    # Identity
    tenant_id: str
    user_id: str
    organization_id: Optional[str] = None
    
    # Session
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: Optional[str] = None
    
    # User context
    user_role: str = "user"
    user_permissions: List[str] = Field(default_factory=list)
    
    # Request context
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str = "api"  # api, chat, agent, scheduled
    
    # Execution options
    dry_run: bool = False
    debug_mode: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        arbitrary_types_allowed = True
