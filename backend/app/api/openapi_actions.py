"""API endpoints for OpenAPI Actions management and execution."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, Field
import structlog

from app.core.config import settings

from app.api.deps import get_current_user
from app.models.user import User
from app.services.agents.openapi_actions import (
    OpenAPIAction,
    OpenAPIActionRegistry,
    OpenAPIActionExecutor,
    OpenAPIOperation,
    AuthType,
)
from app.services.agents.security import AgentSecurityContext


logger = structlog.get_logger()

router = APIRouter(prefix="/actions", tags=["openapi-actions"])

# Global registry (in production, this would be persisted)
_registry = OpenAPIActionRegistry()
_executor = OpenAPIActionExecutor(_registry)


# ======================
# Request/Response Models
# ======================

class ActionRegisterRequest(BaseModel):
    """Request to register an OpenAPI action."""

    action_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    base_url: str
    auth_type: str = "none"  # none, api_key, bearer, basic, oauth2
    auth_config: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    operations: list[dict[str, Any]] = Field(default_factory=list)
    rate_limit: int = 60
    timeout: float = 30.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActionExecuteRequest(BaseModel):
    """Request to execute an OpenAPI action."""

    operation_id: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    body: Any = None


class ActionResponse(BaseModel):
    """Response for an action."""

    action_id: str
    name: str
    description: str
    base_url: str
    auth_type: str
    operation_count: int
    enabled: bool
    rate_limit: int
    timeout: float


class OperationResponse(BaseModel):
    """Response for an operation."""

    operation_id: str
    method: str
    path: str
    summary: str | None
    description: str | None
    parameter_count: int
    tags: list[str]


class ExecutionResponse(BaseModel):
    """Response for action execution."""

    success: bool
    operation_id: str
    status_code: int | None
    response_data: Any
    execution_time_ms: float
    error: str | None


# ======================
# Endpoints
# ======================

@router.get("/health", summary="Check OpenAPI actions service health")
async def health_check():
    """Check OpenAPI actions service health."""
    return {
        "status": "healthy" if settings.OPENAPI_ACTIONS_ENABLED else "disabled",
        "registered_actions": len(_registry.list_actions()),
    }


@router.post("/register", response_model=ActionResponse, status_code=status.HTTP_201_CREATED)
async def register_action(
    request: ActionRegisterRequest,
    current_user: User = Depends(get_current_user),
):
    """Register a new OpenAPI action."""
    if not settings.OPENAPI_ACTIONS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAPI actions are disabled",
        )

    # Check if already exists
    if _registry.get(request.action_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Action '{request.action_id}' already exists",
        )

    # Map auth type
    auth_type_map = {
        "none": AuthType.NONE,
        "api_key": AuthType.API_KEY,
        "bearer": AuthType.BEARER,
        "basic": AuthType.BASIC,
        "oauth2": AuthType.OAUTH2,
    }
    auth_type = auth_type_map.get(request.auth_type.lower(), AuthType.NONE)

    # Parse operations
    operations = []
    for op_data in request.operations:
        from app.services.agents.openapi_actions import OpenAPIParameter, ParameterLocation

        parameters = []
        for param in op_data.get("parameters", []):
            parameters.append(OpenAPIParameter(
                name=param.get("name", ""),
                location=ParameterLocation(param.get("in", "query")),
                required=param.get("required", False),
                description=param.get("description"),
                schema_type=param.get("schema_type", "string"),
            ))

        operations.append(OpenAPIOperation(
            operation_id=op_data.get("operation_id", ""),
            method=op_data.get("method", "GET").upper(),
            path=op_data.get("path", "/"),
            summary=op_data.get("summary"),
            description=op_data.get("description"),
            parameters=parameters,
            request_body_schema=op_data.get("request_body_schema"),
            response_schema=op_data.get("response_schema"),
            tags=op_data.get("tags", []),
        ))

    action = OpenAPIAction(
        action_id=request.action_id,
        name=request.name,
        description=request.description,
        base_url=request.base_url,
        operations=operations,
        auth_type=auth_type,
        auth_config=request.auth_config,
        headers=request.headers,
        rate_limit=request.rate_limit,
        timeout=request.timeout,
        metadata=request.metadata,
    )

    _registry.register(action)

    return ActionResponse(
        action_id=action.action_id,
        name=action.name,
        description=action.description,
        base_url=action.base_url,
        auth_type=action.auth_type.value,
        operation_count=len(action.operations),
        enabled=action.enabled,
        rate_limit=action.rate_limit,
        timeout=action.timeout,
    )


@router.post("/register/openapi-spec", status_code=status.HTTP_201_CREATED)
async def register_from_spec(
    action_id: str,
    action_name: str,
    file: UploadFile = File(...),
    base_url: str | None = None,
    auth_type: str = "none",
    current_user: User = Depends(get_current_user),
):
    """Register an action from an OpenAPI specification file."""
    if not settings.OPENAPI_ACTIONS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAPI actions are disabled",
        )

    import json
    import yaml

    # Read file
    content = await file.read()

    # Parse spec (JSON or YAML)
    try:
        if file.filename.endswith(".json"):
            spec = json.loads(content)
        else:
            spec = yaml.safe_load(content)
    except Exception as e:
        logger.warning("Failed to parse OpenAPI spec", filename=file.filename, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to parse OpenAPI spec. Please provide a valid JSON or YAML file.",
        )

    # Map auth type
    auth_type_map = {
        "none": AuthType.NONE,
        "api_key": AuthType.API_KEY,
        "bearer": AuthType.BEARER,
        "basic": AuthType.BASIC,
    }

    # Create action from spec
    action = OpenAPIActionRegistry.from_openapi_spec(
        spec=spec,
        action_id=action_id,
        action_name=action_name,
        base_url=base_url,
        auth_type=auth_type_map.get(auth_type.lower(), AuthType.NONE),
    )

    _registry.register(action)

    return {
        "action_id": action.action_id,
        "name": action.name,
        "operation_count": len(action.operations),
        "operations": [op.operation_id for op in action.operations],
    }


@router.get("", response_model=list[ActionResponse])
async def list_actions(
    current_user: User = Depends(get_current_user),
):
    """List all registered OpenAPI actions."""
    actions = _registry.list_actions()

    return [
        ActionResponse(
            action_id=a.action_id,
            name=a.name,
            description=a.description,
            base_url=a.base_url,
            auth_type=a.auth_type.value,
            operation_count=len(a.operations),
            enabled=a.enabled,
            rate_limit=a.rate_limit,
            timeout=a.timeout,
        )
        for a in actions
    ]


@router.get("/{action_id}")
async def get_action(
    action_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific action."""
    action = _registry.get(action_id)
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action '{action_id}' not found",
        )

    return {
        "action_id": action.action_id,
        "name": action.name,
        "description": action.description,
        "base_url": action.base_url,
        "auth_type": action.auth_type.value,
        "enabled": action.enabled,
        "rate_limit": action.rate_limit,
        "timeout": action.timeout,
        "headers": action.headers,
        "operations": [
            {
                "operation_id": op.operation_id,
                "method": op.method,
                "path": op.path,
                "summary": op.summary,
                "description": op.description,
                "parameters": [
                    {
                        "name": p.name,
                        "in": p.location.value,
                        "required": p.required,
                        "type": p.schema_type,
                    }
                    for p in op.parameters
                ],
                "tags": op.tags,
            }
            for op in action.operations
        ],
    }


@router.get("/{action_id}/operations", response_model=list[OperationResponse])
async def list_operations(
    action_id: str,
    current_user: User = Depends(get_current_user),
):
    """List operations for an action."""
    action = _registry.get(action_id)
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action '{action_id}' not found",
        )

    return [
        OperationResponse(
            operation_id=op.operation_id,
            method=op.method,
            path=op.path,
            summary=op.summary,
            description=op.description,
            parameter_count=len(op.parameters),
            tags=op.tags,
        )
        for op in action.operations
    ]


@router.post("/{action_id}/execute", response_model=ExecutionResponse)
async def execute_action(
    action_id: str,
    request: ActionExecuteRequest,
    current_user: User = Depends(get_current_user),
):
    """Execute an OpenAPI action operation."""
    if not settings.OPENAPI_ACTIONS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAPI actions are disabled",
        )

    action = _registry.get(action_id)
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action '{action_id}' not found",
        )

    if not action.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Action '{action_id}' is disabled",
        )

    # Create security context
    security_context = AgentSecurityContext(
        agent_id=f"user-{current_user.id}",
        tenant_id=str(current_user.organization_id) if hasattr(current_user, 'organization_id') else "default",
        user_id=str(current_user.id),
        max_requests_per_minute=action.rate_limit,
    )

    # Execute
    result = await _executor.execute(
        action_id=action_id,
        operation_id=request.operation_id,
        parameters=request.parameters,
        body=request.body,
        security_context=security_context,
    )

    return ExecutionResponse(
        success=result.success,
        operation_id=result.operation_id,
        status_code=result.status_code,
        response_data=result.response_data,
        execution_time_ms=result.execution_time_ms,
        error=result.error,
    )


@router.delete("/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_action(
    action_id: str,
    current_user: User = Depends(get_current_user),
):
    """Unregister an OpenAPI action."""
    if not _registry.get(action_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action '{action_id}' not found",
        )

    _registry.unregister(action_id)


@router.post("/{action_id}/enable")
async def enable_action(
    action_id: str,
    current_user: User = Depends(get_current_user),
):
    """Enable an action."""
    action = _registry.get(action_id)
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action '{action_id}' not found",
        )

    action.enabled = True
    return {"status": "enabled", "action_id": action_id}


@router.post("/{action_id}/disable")
async def disable_action(
    action_id: str,
    current_user: User = Depends(get_current_user),
):
    """Disable an action."""
    action = _registry.get(action_id)
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action '{action_id}' not found",
        )

    action.enabled = False
    return {"status": "disabled", "action_id": action_id}


@router.get("/{action_id}/tools-schema")
async def get_tools_schema(
    action_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get OpenAI-compatible tool schemas for an action."""
    tools = _executor.get_tools_schema(action_id)
    if not tools:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action '{action_id}' not found or has no operations",
        )

    return {"tools": tools}


@router.post("/{action_id}/validate")
async def validate_action(
    action_id: str,
    current_user: User = Depends(get_current_user),
):
    """Validate an action configuration."""
    action = _registry.get(action_id)
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action '{action_id}' not found",
        )

    issues = []

    # Check base URL
    if not action.base_url:
        issues.append("Missing base_url")

    # Check operations
    if not action.operations:
        issues.append("No operations defined")

    for op in action.operations:
        if not op.operation_id:
            issues.append(f"Operation missing operation_id at path {op.path}")
        if not op.path:
            issues.append(f"Operation '{op.operation_id}' missing path")

    # Check auth
    if action.auth_type != AuthType.NONE:
        if action.auth_type == AuthType.API_KEY and not action.auth_config.get("api_key"):
            issues.append("API key auth configured but api_key not provided")
        if action.auth_type == AuthType.BEARER and not action.auth_config.get("token"):
            issues.append("Bearer auth configured but token not provided")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "action_id": action_id,
    }


# ======================
# Pre-built Actions
# ======================

@router.post("/prebuilt/github", status_code=status.HTTP_201_CREATED)
async def register_github_action(
    token: str,
    current_user: User = Depends(get_current_user),
):
    """Register pre-built GitHub API action."""
    from app.services.agents.openapi_actions import create_github_action

    action = create_github_action(token)
    _registry.register(action)

    return {
        "action_id": action.action_id,
        "name": action.name,
        "operation_count": len(action.operations),
    }


@router.post("/prebuilt/jira", status_code=status.HTTP_201_CREATED)
async def register_jira_action(
    base_url: str,
    email: str,
    api_token: str,
    current_user: User = Depends(get_current_user),
):
    """Register pre-built Jira API action."""
    from app.services.agents.openapi_actions import create_jira_action

    action = create_jira_action(base_url, email, api_token)
    _registry.register(action)

    return {
        "action_id": action.action_id,
        "name": action.name,
        "operation_count": len(action.operations),
    }
