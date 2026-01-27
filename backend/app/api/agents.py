"""API endpoints for agent management and execution."""

from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.agents.service import AgentService
from app.services.agents.models import AgentCapability, AgentCreate as ServiceAgentCreate

router = APIRouter(prefix="/agents", tags=["agents"])


def _get_default_model_for_provider() -> str:
    """Get the default model name based on the configured DEFAULT_AI_PROVIDER."""
    provider = settings.DEFAULT_AI_PROVIDER.lower()
    if provider == "google":
        return settings.GOOGLE_DEFAULT_MODEL
    elif provider == "anthropic":
        return settings.ANTHROPIC_DEFAULT_MODEL
    elif provider == "openai":
        return settings.OPENAI_DEFAULT_MODEL
    elif provider == "groq":
        return settings.GROQ_DEFAULT_MODEL
    elif provider == "ollama":
        return settings.OLLAMA_DEFAULT_MODEL
    elif provider == "mistral":
        return settings.MISTRAL_DEFAULT_MODEL
    return settings.GOOGLE_DEFAULT_MODEL


# ======================
# Request/Response Models
# ======================

class AgentCreate(BaseModel):
    """Request model for creating an agent."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    system_prompt: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    tools_config: dict[str, Any] = Field(default_factory=dict)
    mcp_servers: list[dict[str, Any]] = Field(default_factory=list)
    actions_config: list[dict[str, Any]] = Field(default_factory=list)
    model_provider: str = Field(default_factory=lambda: settings.DEFAULT_AI_PROVIDER)
    model_name: str = Field(default_factory=_get_default_model_for_provider)
    temperature: float = 0.7
    max_tokens: int = 4096
    is_public: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    """Request model for updating an agent."""

    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    capabilities: list[str] | None = None
    tools_config: dict[str, Any] | None = None
    mcp_servers: list[dict[str, Any]] | None = None
    actions_config: list[dict[str, Any]] | None = None
    model_provider: str | None = None
    model_name: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    is_public: bool | None = None
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


class AgentResponse(BaseModel):
    """Response model for an agent."""

    id: str
    name: str
    description: str | None
    system_prompt: str | None
    capabilities: list[str]
    tools_config: dict[str, Any]
    mcp_servers: list[dict[str, Any]]
    actions_config: list[dict[str, Any]]
    model_provider: str
    model_name: str
    model_config: dict[str, Any] = {}
    is_public: bool
    status: str
    creator_id: str
    organization_id: str | None = None
    created_at: datetime
    updated_at: datetime
    usage_count: int = 0
    metadata: dict[str, Any]

    class Config:
        from_attributes = True


class AgentExecuteRequest(BaseModel):
    """Request model for executing an agent."""

    message: str
    conversation_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    stream: bool = False


class AgentExecutionResponse(BaseModel):
    """Response model for agent execution."""

    execution_id: str
    agent_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    tokens_used: int = 0
    execution_time_ms: float = 0.0


class ToolCreate(BaseModel):
    """Request model for adding a custom tool."""

    name: str
    description: str
    schema_definition: dict[str, Any]
    implementation_type: str = "function"  # function, http, mcp
    config: dict[str, Any] = Field(default_factory=dict)


class AgentListResponse(BaseModel):
    """Response model for listing agents."""

    agents: list[AgentResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# ======================
# Endpoints
# ======================

@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new agent."""
    if not settings.AGENTS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agents feature is disabled",
        )

    service = AgentService(db)

    # Validate capabilities
    valid_capabilities = [c.value for c in AgentCapability]
    for cap in request.capabilities:
        if cap not in valid_capabilities:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid capability: {cap}. Valid: {valid_capabilities}",
            )

    # Convert API request to service model
    service_data = ServiceAgentCreate(
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        model_provider=request.model_provider,
        model_name=request.model_name,
        capabilities=[AgentCapability(c) for c in request.capabilities],
        tools_config=request.tools_config,
        mcp_servers=request.mcp_servers,
        is_public=request.is_public,
        tags=request.metadata.get("tags", []),
    )

    agent = await service.create_agent(
        user_id=str(current_user.id),
        data=service_data,
        organization_id=str(current_user.organization_id) if hasattr(current_user, 'organization_id') and current_user.organization_id else None,
    )

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        system_prompt=agent.system_prompt,
        capabilities=agent.capabilities or [],
        tools_config=agent.tools_config or {},
        mcp_servers=agent.mcp_servers or [],
        actions_config=agent.actions_config or [],
        model_provider=agent.model_provider,
        model_name=agent.model_name,
        model_config=agent.model_config or {},
        is_public=agent.is_public,
        status=agent.status,
        creator_id=str(agent.creator_id),
        organization_id=str(agent.organization_id) if agent.organization_id else None,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        usage_count=agent.usage_count,
        metadata=agent.agent_metadata or {},
    )


@router.get("", response_model=AgentListResponse)
async def list_agents(
    page: int = 1,
    page_size: int = 20,
    include_public: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List agents accessible to the current user."""
    service = AgentService(db)

    # Convert page/page_size to offset/limit
    offset = (page - 1) * page_size
    agents = await service.list_agents(
        user_id=str(current_user.id),
        include_public=include_public,
        offset=offset,
        limit=page_size,
    )
    total = len(agents)  # Simple count for now

    return AgentListResponse(
        agents=[
            AgentResponse(
                id=str(a.id),
                name=a.name,
                description=a.description,
                system_prompt=a.system_prompt,
                capabilities=a.capabilities or [],
                tools_config=a.tools_config or {},
                mcp_servers=a.mcp_servers or [],
                actions_config=a.actions_config or [],
                model_provider=a.model_provider,
                model_name=a.model_name,
                temperature=a.temperature,
                max_tokens=a.max_tokens,
                is_public=a.is_public,
                is_active=a.is_active,
                owner_id=str(a.owner_id),
                created_at=a.created_at,
                updated_at=a.updated_at,
                metadata=a.metadata or {},
            )
            for a in agents
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get agent by ID."""
    service = AgentService(db)

    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Check access
    if not agent.is_public and str(agent.owner_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        system_prompt=agent.system_prompt,
        capabilities=agent.capabilities or [],
        tools_config=agent.tools_config or {},
        mcp_servers=agent.mcp_servers or [],
        actions_config=agent.actions_config or [],
        model_provider=agent.model_provider,
        model_name=agent.model_name,
        model_config=agent.model_config or {},
        is_public=agent.is_public,
        status=agent.status,
        creator_id=str(agent.creator_id),
        organization_id=str(agent.organization_id) if agent.organization_id else None,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        usage_count=agent.usage_count,
        metadata=agent.agent_metadata or {},
    )


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    request: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an agent."""
    service = AgentService(db)

    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Check ownership
    if str(agent.owner_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can update this agent",
        )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    agent = await service.update_agent(agent_id, **update_data)

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        system_prompt=agent.system_prompt,
        capabilities=agent.capabilities or [],
        tools_config=agent.tools_config or {},
        mcp_servers=agent.mcp_servers or [],
        actions_config=agent.actions_config or [],
        model_provider=agent.model_provider,
        model_name=agent.model_name,
        model_config=agent.model_config or {},
        is_public=agent.is_public,
        status=agent.status,
        creator_id=str(agent.creator_id),
        organization_id=str(agent.organization_id) if agent.organization_id else None,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        usage_count=agent.usage_count,
        metadata=agent.agent_metadata or {},
    )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an agent."""
    service = AgentService(db)

    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    if str(agent.owner_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can delete this agent",
        )

    await service.delete_agent(agent_id)


@router.post("/{agent_id}/execute", response_model=AgentExecutionResponse)
async def execute_agent(
    agent_id: str,
    request: AgentExecuteRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute an agent with the given message."""
    service = AgentService(db)

    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is not active",
        )

    # Check access
    if not agent.is_public and str(agent.owner_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Execute agent
    start_time = datetime.now(UTC)
    result = await service.execute(
        agent_id=agent_id,
        user_id=str(current_user.id),
        message=request.message,
        conversation_id=request.conversation_id,
        context=request.context,
    )

    execution_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

    return AgentExecutionResponse(
        execution_id=result.get("execution_id", ""),
        agent_id=agent_id,
        status=result.get("status", "completed"),
        started_at=start_time,
        completed_at=datetime.now(UTC),
        result=result,
        steps=result.get("steps", []),
        tokens_used=result.get("tokens_used", 0),
        execution_time_ms=execution_time,
    )


@router.get("/{agent_id}/executions")
async def list_agent_executions(
    agent_id: str,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List execution history for an agent."""
    service = AgentService(db)

    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    if not agent.is_public and str(agent.owner_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    executions = await service.list_executions(
        agent_id=agent_id,
        page=page,
        page_size=page_size,
    )

    return {
        "executions": executions,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{agent_id}/tools")
async def add_agent_tool(
    agent_id: str,
    request: ToolCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a custom tool to an agent."""
    service = AgentService(db)

    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    if str(agent.owner_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can add tools",
        )

    tool = await service.add_tool(
        agent_id=agent_id,
        name=request.name,
        description=request.description,
        schema_definition=request.schema_definition,
        implementation_type=request.implementation_type,
        config=request.config,
    )

    return {
        "id": str(tool.id),
        "name": tool.name,
        "description": tool.description,
        "schema_definition": tool.schema_definition,
    }


@router.get("/capabilities/list")
async def list_capabilities():
    """List all available agent capabilities."""
    return {
        "capabilities": [
            {
                "name": cap.value,
                "description": _get_capability_description(cap),
            }
            for cap in AgentCapability
        ]
    }


def _get_capability_description(cap: AgentCapability) -> str:
    """Get description for a capability."""
    descriptions = {
        AgentCapability.CODE_EXECUTION: "Execute code in a sandboxed environment",
        AgentCapability.FILE_SEARCH: "Search through files and documents",
        AgentCapability.WEB_SEARCH: "Search the web for information",
        AgentCapability.IMAGE_GENERATION: "Generate images using AI models",
        AgentCapability.IMAGE_VISION: "Analyze and understand images",
        AgentCapability.SPEECH_TO_TEXT: "Convert speech to text",
        AgentCapability.TEXT_TO_SPEECH: "Convert text to speech",
        AgentCapability.FUNCTION_CALLING: "Call custom functions and tools",
        AgentCapability.MCP_SERVER: "Connect to MCP protocol servers",
        AgentCapability.RETRIEVAL: "Retrieve information from knowledge bases",
        AgentCapability.ACTIONS: "Execute OpenAPI-defined actions",
    }
    return descriptions.get(cap, cap.value)
