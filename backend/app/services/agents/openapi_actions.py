"""OpenAPI Actions support for agents.

Enables agents to call external APIs defined by OpenAPI/Swagger specs.
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any
import json

import httpx
import structlog

from app.services.agents.security import (
    AgentSecurityContext,
    ActionType,
    AccessDecision,
)

logger = structlog.get_logger()


class AuthType(str, Enum):
    """Authentication types for OpenAPI actions."""

    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"
    OAUTH2 = "oauth2"


class ParameterLocation(str, Enum):
    """Where parameters are placed in the request."""

    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    COOKIE = "cookie"
    BODY = "body"


@dataclass
class OpenAPIParameter:
    """Parameter definition for an OpenAPI operation."""

    name: str
    location: ParameterLocation
    required: bool = False
    description: str | None = None
    schema_type: str = "string"
    default: Any = None
    enum: list[Any] | None = None


@dataclass
class OpenAPIOperation:
    """A single operation (endpoint) from an OpenAPI spec."""

    operation_id: str
    method: str  # GET, POST, PUT, DELETE, etc.
    path: str
    summary: str | None = None
    description: str | None = None
    parameters: list[OpenAPIParameter] = field(default_factory=list)
    request_body_schema: dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None
    tags: list[str] = field(default_factory=list)
    security: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class OpenAPIAction:
    """An OpenAPI-based action that agents can invoke."""

    action_id: str
    name: str
    description: str
    base_url: str
    operations: list[OpenAPIOperation]
    auth_type: AuthType = AuthType.NONE
    auth_config: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    rate_limit: int = 60  # requests per minute
    timeout: float = 30.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionExecutionResult:
    """Result of executing an OpenAPI action."""

    success: bool
    operation_id: str
    status_code: int | None = None
    response_data: Any = None
    response_headers: dict[str, str] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    error: str | None = None


class OpenAPIActionRegistry:
    """Registry for OpenAPI actions available to agents."""

    def __init__(self):
        self._actions: dict[str, OpenAPIAction] = {}

    def register(self, action: OpenAPIAction) -> None:
        """Register an OpenAPI action."""
        self._actions[action.action_id] = action
        logger.info(
            "OpenAPI action registered",
            action_id=action.action_id,
            operations=len(action.operations),
        )

    def unregister(self, action_id: str) -> bool:
        """Unregister an OpenAPI action."""
        if action_id in self._actions:
            del self._actions[action_id]
            return True
        return False

    def get(self, action_id: str) -> OpenAPIAction | None:
        """Get an action by ID."""
        return self._actions.get(action_id)

    def list_actions(self) -> list[OpenAPIAction]:
        """List all registered actions."""
        return list(self._actions.values())

    def get_operation(
        self,
        action_id: str,
        operation_id: str,
    ) -> tuple[OpenAPIAction, OpenAPIOperation] | None:
        """Get a specific operation from an action."""
        action = self._actions.get(action_id)
        if not action:
            return None

        for op in action.operations:
            if op.operation_id == operation_id:
                return action, op

        return None

    @classmethod
    def from_openapi_spec(
        cls,
        spec: dict[str, Any],
        action_id: str,
        action_name: str,
        base_url: str | None = None,
        auth_type: AuthType = AuthType.NONE,
        auth_config: dict[str, Any] | None = None,
    ) -> OpenAPIAction:
        """Create an OpenAPIAction from an OpenAPI specification."""
        # Extract base URL from spec if not provided
        if not base_url:
            servers = spec.get("servers", [])
            if servers:
                base_url = servers[0].get("url", "")
            else:
                base_url = ""

        # Parse paths into operations
        operations = []
        paths = spec.get("paths", {})

        for path, path_item in paths.items():
            for method in ["get", "post", "put", "delete", "patch", "options", "head"]:
                if method not in path_item:
                    continue

                op_spec = path_item[method]
                operation_id = op_spec.get("operationId", f"{method}_{path.replace('/', '_')}")

                # Parse parameters
                parameters = []
                for param in op_spec.get("parameters", []) + path_item.get("parameters", []):
                    parameters.append(OpenAPIParameter(
                        name=param.get("name", ""),
                        location=ParameterLocation(param.get("in", "query")),
                        required=param.get("required", False),
                        description=param.get("description"),
                        schema_type=param.get("schema", {}).get("type", "string"),
                        default=param.get("schema", {}).get("default"),
                        enum=param.get("schema", {}).get("enum"),
                    ))

                # Parse request body
                request_body_schema = None
                if "requestBody" in op_spec:
                    content = op_spec["requestBody"].get("content", {})
                    if "application/json" in content:
                        request_body_schema = content["application/json"].get("schema")

                # Parse response schema
                response_schema = None
                responses = op_spec.get("responses", {})
                for status in ["200", "201", "default"]:
                    if status in responses:
                        content = responses[status].get("content", {})
                        if "application/json" in content:
                            response_schema = content["application/json"].get("schema")
                            break

                operations.append(OpenAPIOperation(
                    operation_id=operation_id,
                    method=method.upper(),
                    path=path,
                    summary=op_spec.get("summary"),
                    description=op_spec.get("description"),
                    parameters=parameters,
                    request_body_schema=request_body_schema,
                    response_schema=response_schema,
                    tags=op_spec.get("tags", []),
                    security=op_spec.get("security", []),
                ))

        return OpenAPIAction(
            action_id=action_id,
            name=action_name,
            description=spec.get("info", {}).get("description", ""),
            base_url=base_url,
            operations=operations,
            auth_type=auth_type,
            auth_config=auth_config or {},
        )


class OpenAPIActionExecutor:
    """Executes OpenAPI actions with security enforcement."""

    def __init__(
        self,
        registry: OpenAPIActionRegistry,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.registry = registry
        self._client = http_client

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def execute(
        self,
        action_id: str,
        operation_id: str,
        parameters: dict[str, Any] | None = None,
        body: Any = None,
        security_context: AgentSecurityContext | None = None,
    ) -> ActionExecutionResult:
        """Execute an OpenAPI operation."""
        start_time = datetime.now(UTC)

        # Get action and operation
        result = self.registry.get_operation(action_id, operation_id)
        if not result:
            return ActionExecutionResult(
                success=False,
                operation_id=operation_id,
                error=f"Operation '{operation_id}' not found in action '{action_id}'",
            )

        action, operation = result

        if not action.enabled:
            return ActionExecutionResult(
                success=False,
                operation_id=operation_id,
                error=f"Action '{action_id}' is disabled",
            )

        # Security check
        if security_context:
            access = security_context.check_domain_access(
                action.base_url,
                ActionType.HTTP_REQUEST,
            )
            if not access.allowed:
                return ActionExecutionResult(
                    success=False,
                    operation_id=operation_id,
                    error=f"Access denied: {access.reason}",
                )

        # Build request
        try:
            url, headers, query_params = self._build_request(
                action, operation, parameters or {}
            )

            client = await self._get_client()

            # Execute request
            response = await client.request(
                method=operation.method,
                url=url,
                headers=headers,
                params=query_params,
                json=body if body and operation.method in ["POST", "PUT", "PATCH"] else None,
                timeout=action.timeout,
            )

            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = response.text

            execution_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

            logger.info(
                "OpenAPI action executed",
                action_id=action_id,
                operation_id=operation_id,
                status_code=response.status_code,
                execution_time_ms=execution_time,
            )

            return ActionExecutionResult(
                success=200 <= response.status_code < 300,
                operation_id=operation_id,
                status_code=response.status_code,
                response_data=response_data,
                response_headers=dict(response.headers),
                execution_time_ms=execution_time,
            )

        except httpx.TimeoutException:
            return ActionExecutionResult(
                success=False,
                operation_id=operation_id,
                error="Request timed out",
                execution_time_ms=(datetime.now(UTC) - start_time).total_seconds() * 1000,
            )
        except Exception as e:
            logger.error(
                "OpenAPI action failed",
                action_id=action_id,
                operation_id=operation_id,
                error=str(e),
            )
            return ActionExecutionResult(
                success=False,
                operation_id=operation_id,
                error=str(e),
                execution_time_ms=(datetime.now(UTC) - start_time).total_seconds() * 1000,
            )

    def _build_request(
        self,
        action: OpenAPIAction,
        operation: OpenAPIOperation,
        parameters: dict[str, Any],
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        """Build the HTTP request from operation and parameters."""
        # Start with base URL and path
        path = operation.path
        query_params = {}
        headers = dict(action.headers)

        # Add authentication
        headers.update(self._get_auth_headers(action))

        # Process parameters
        for param in operation.parameters:
            value = parameters.get(param.name, param.default)

            if value is None:
                if param.required:
                    raise ValueError(f"Required parameter '{param.name}' not provided")
                continue

            if param.location == ParameterLocation.PATH:
                path = path.replace(f"{{{param.name}}}", str(value))
            elif param.location == ParameterLocation.QUERY:
                query_params[param.name] = value
            elif param.location == ParameterLocation.HEADER:
                headers[param.name] = str(value)

        url = f"{action.base_url.rstrip('/')}{path}"

        return url, headers, query_params

    def _get_auth_headers(self, action: OpenAPIAction) -> dict[str, str]:
        """Get authentication headers based on auth type."""
        headers = {}

        if action.auth_type == AuthType.API_KEY:
            key_name = action.auth_config.get("header_name", "X-API-Key")
            key_value = action.auth_config.get("api_key", "")
            if key_value:
                headers[key_name] = key_value

        elif action.auth_type == AuthType.BEARER:
            token = action.auth_config.get("token", "")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif action.auth_type == AuthType.BASIC:
            import base64
            username = action.auth_config.get("username", "")
            password = action.auth_config.get("password", "")
            if username:
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"

        return headers

    def get_tools_schema(self, action_id: str) -> list[dict[str, Any]]:
        """Get OpenAI-compatible tool schemas for an action's operations."""
        action = self.registry.get(action_id)
        if not action:
            return []

        tools = []
        for operation in action.operations:
            # Build parameter schema
            properties = {}
            required = []

            for param in operation.parameters:
                prop = {
                    "type": param.schema_type,
                    "description": param.description or f"Parameter: {param.name}",
                }
                if param.enum:
                    prop["enum"] = param.enum
                properties[param.name] = prop

                if param.required:
                    required.append(param.name)

            # Add request body if present
            if operation.request_body_schema:
                properties["request_body"] = {
                    "type": "object",
                    "description": "Request body",
                }

            tool = {
                "type": "function",
                "function": {
                    "name": f"{action_id}_{operation.operation_id}",
                    "description": operation.description or operation.summary or operation.operation_id,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            }
            tools.append(tool)

        return tools


# Example pre-built actions
def create_github_action(token: str) -> OpenAPIAction:
    """Create a GitHub API action."""
    return OpenAPIAction(
        action_id="github",
        name="GitHub API",
        description="Interact with GitHub repositories, issues, and pull requests",
        base_url="https://api.github.com",
        operations=[
            OpenAPIOperation(
                operation_id="get_repo",
                method="GET",
                path="/repos/{owner}/{repo}",
                summary="Get a repository",
                parameters=[
                    OpenAPIParameter(name="owner", location=ParameterLocation.PATH, required=True),
                    OpenAPIParameter(name="repo", location=ParameterLocation.PATH, required=True),
                ],
            ),
            OpenAPIOperation(
                operation_id="list_issues",
                method="GET",
                path="/repos/{owner}/{repo}/issues",
                summary="List repository issues",
                parameters=[
                    OpenAPIParameter(name="owner", location=ParameterLocation.PATH, required=True),
                    OpenAPIParameter(name="repo", location=ParameterLocation.PATH, required=True),
                    OpenAPIParameter(name="state", location=ParameterLocation.QUERY, default="open"),
                ],
            ),
            OpenAPIOperation(
                operation_id="create_issue",
                method="POST",
                path="/repos/{owner}/{repo}/issues",
                summary="Create an issue",
                parameters=[
                    OpenAPIParameter(name="owner", location=ParameterLocation.PATH, required=True),
                    OpenAPIParameter(name="repo", location=ParameterLocation.PATH, required=True),
                ],
                request_body_schema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["title"],
                },
            ),
        ],
        auth_type=AuthType.BEARER,
        auth_config={"token": token},
        headers={"Accept": "application/vnd.github.v3+json"},
    )


def create_jira_action(base_url: str, email: str, api_token: str) -> OpenAPIAction:
    """Create a Jira API action."""
    import base64
    credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()

    return OpenAPIAction(
        action_id="jira",
        name="Jira API",
        description="Interact with Jira issues and projects",
        base_url=base_url,
        operations=[
            OpenAPIOperation(
                operation_id="get_issue",
                method="GET",
                path="/rest/api/3/issue/{issueIdOrKey}",
                summary="Get issue details",
                parameters=[
                    OpenAPIParameter(name="issueIdOrKey", location=ParameterLocation.PATH, required=True),
                ],
            ),
            OpenAPIOperation(
                operation_id="search_issues",
                method="POST",
                path="/rest/api/3/search",
                summary="Search for issues using JQL",
                request_body_schema={
                    "type": "object",
                    "properties": {
                        "jql": {"type": "string"},
                        "maxResults": {"type": "integer"},
                    },
                },
            ),
        ],
        auth_type=AuthType.BASIC,
        auth_config={"username": email, "password": api_token},
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
