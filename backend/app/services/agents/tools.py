"""Tool system for agents."""

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable

import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


@dataclass
class ToolResult:
    """Result from tool execution."""

    success: bool
    output: Any
    error: str | None = None
    execution_time_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolParameter(BaseModel):
    """Tool parameter definition."""

    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    default: Any = None
    enum: list[str] | None = None


class ToolDefinition(BaseModel):
    """Tool definition for function calling."""

    name: str
    description: str
    parameters: list[ToolParameter] = []

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert to OpenAI function calling schema."""
        properties = {}
        required = []

        for param in self.parameters:
            prop: dict[str, Any] = {"type": param.type}
            if param.description:
                prop["description"] = param.description
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_anthropic_schema(self) -> dict[str, Any]:
        """Convert to Anthropic tool schema."""
        properties = {}
        required = []

        for param in self.parameters:
            prop: dict[str, Any] = {"type": param.type}
            if param.description:
                prop["description"] = param.description
            if param.enum:
                prop["enum"] = param.enum

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


class BaseTool(ABC):
    """Base class for all tools."""

    name: str
    description: str
    parameters: list[ToolParameter] = []

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def get_definition(self) -> ToolDefinition:
        """Get the tool definition."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )


class FunctionTool(BaseTool):
    """Tool wrapping a Python function."""

    def __init__(
        self,
        func: Callable,
        name: str | None = None,
        description: str | None = None,
    ):
        self.func = func
        self.name = name or func.__name__
        self.description = description or func.__doc__ or ""
        self.parameters = self._extract_parameters()

    def _extract_parameters(self) -> list[ToolParameter]:
        """Extract parameters from function signature."""
        sig = inspect.signature(self.func)
        params = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls", "kwargs", "args"):
                continue

            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == list:
                    param_type = "array"
                elif param.annotation == dict:
                    param_type = "object"

            params.append(
                ToolParameter(
                    name=param_name,
                    type=param_type,
                    required=param.default == inspect.Parameter.empty,
                    default=None if param.default == inspect.Parameter.empty else param.default,
                )
            )

        return params

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the wrapped function."""
        start_time = datetime.now(UTC)

        try:
            if inspect.iscoroutinefunction(self.func):
                result = await self.func(**kwargs)
            else:
                result = self.func(**kwargs)

            execution_time = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

            return ToolResult(
                success=True,
                output=result,
                execution_time_ms=execution_time,
            )

        except Exception as e:
            execution_time = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            logger.error("Tool execution failed", tool=self.name, error=str(e))

            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                execution_time_ms=execution_time,
            )


class ToolRegistry:
    """Registry for managing tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._builtin_tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        logger.info("Tool registered", tool=tool.name)

    def register_builtin(self, tool: BaseTool) -> None:
        """Register a built-in tool."""
        self._builtin_tools[tool.name] = tool
        logger.info("Built-in tool registered", tool=tool.name)

    def register_function(
        self,
        func: Callable,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Register a function as a tool."""
        tool = FunctionTool(func, name, description)
        self.register(tool)

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name) or self._builtin_tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        """List all registered tools."""
        all_tools = {**self._builtin_tools, **self._tools}
        return [tool.get_definition() for tool in all_tools.values()]

    def get_openai_schemas(self) -> list[dict[str, Any]]:
        """Get all tools in OpenAI format."""
        return [tool.to_openai_schema() for tool in self.list_tools()]

    def get_anthropic_schemas(self) -> list[dict[str, Any]]:
        """Get all tools in Anthropic format."""
        return [tool.to_anthropic_schema() for tool in self.list_tools()]

    async def execute(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                output=None,
                error=f"Tool not found: {name}",
            )

        return await tool.execute(**kwargs)

    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def clear(self) -> None:
        """Clear all registered tools (except built-ins)."""
        self._tools.clear()


# Global tool registry
tool_registry = ToolRegistry()


# Decorator for registering tools
def tool(name: str | None = None, description: str | None = None):
    """Decorator to register a function as a tool."""

    def decorator(func: Callable) -> Callable:
        tool_registry.register_function(func, name, description)
        return func

    return decorator


# Built-in tools
class GetCurrentTimeTool(BaseTool):
    """Tool to get current time."""

    name = "get_current_time"
    description = "Get the current date and time"
    parameters = [
        ToolParameter(
            name="timezone",
            type="string",
            description="Timezone (e.g., UTC, America/New_York)",
            required=False,
            default="UTC",
        ),
    ]

    async def execute(self, timezone: str = "UTC") -> ToolResult:
        """Get current time in the specified timezone."""
        from zoneinfo import ZoneInfo

        try:
            tz = ZoneInfo(timezone)
            current_time = datetime.now(tz)

            return ToolResult(
                success=True,
                output={
                    "datetime": current_time.isoformat(),
                    "timezone": timezone,
                },
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )


class CalculatorTool(BaseTool):
    """Tool for basic calculations."""

    name = "calculator"
    description = "Perform basic mathematical calculations"
    parameters = [
        ToolParameter(
            name="expression",
            type="string",
            description="Mathematical expression to evaluate (e.g., '2 + 2 * 3')",
            required=True,
        ),
    ]

    async def execute(self, expression: str) -> ToolResult:
        """Evaluate a mathematical expression safely."""
        import ast
        import operator

        # Safe operators
        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
        }

        def eval_node(node):
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.BinOp):
                left = eval_node(node.left)
                right = eval_node(node.right)
                return ops[type(node.op)](left, right)
            elif isinstance(node, ast.UnaryOp):
                operand = eval_node(node.operand)
                return ops[type(node.op)](operand)
            else:
                raise ValueError(f"Unsupported operation: {type(node)}")

        try:
            tree = ast.parse(expression, mode="eval")
            result = eval_node(tree.body)

            return ToolResult(
                success=True,
                output={"expression": expression, "result": result},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )


# Register built-in tools
tool_registry.register_builtin(GetCurrentTimeTool())
tool_registry.register_builtin(CalculatorTool())
