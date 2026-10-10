"""API endpoints for Setup Chatbot."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import structlog

from app.api.deps import get_current_user, get_current_tenant

logger = structlog.get_logger()
from app.models.user import User
from app.services.setup_chatbot import (
    setup_chatbot_service,
    ChatMessage,
    ChatResponse,
    SetupSession,
    PLUGIN_CONFIGS,
)


router = APIRouter(prefix="/setup-assistant", tags=["Setup Assistant"])


# ===================
# Request/Response Schemas
# ===================


class StartSessionRequest(BaseModel):
    """Request to start a new session."""

    flow_type: str | None = Field(
        None,
        description="Type of flow to start: connection, project, pipeline, onboarding",
    )
    plugin: str | None = Field(
        None,
        description="Plugin type for connection flow",
    )


class StartSessionResponse(BaseModel):
    """Response for starting a session."""

    session_id: str
    message: ChatMessage
    flow_type: str | None = None
    current_step: str | None = None


class SendMessageRequest(BaseModel):
    """Request to send a message."""

    message: str = Field(..., min_length=1, max_length=4000)
    quick_reply: bool = Field(
        False, description="Whether this is a quick reply value"
    )


class PluginInfo(BaseModel):
    """Information about a plugin."""

    plugin_type: str
    display_name: str
    description: str
    icon: str
    required_fields: list[str]
    optional_fields: list[str]
    auth_type: str
    endpoint_required: bool
    scopes_supported: list[str]


class PluginListResponse(BaseModel):
    """Response for plugin list."""

    plugins: list[PluginInfo]


class SessionInfoResponse(BaseModel):
    """Response for session info."""

    session_id: str
    flow_type: str | None
    current_step: str | None
    is_active: bool
    message_count: int
    collected_data: dict[str, Any]


# ===================
# Endpoints
# ===================


@router.post("/sessions", response_model=StartSessionResponse)
async def start_session(
    request: StartSessionRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Start a new setup assistant session.

    This creates a new conversational session for guiding users through:
    - Setting up data source connections
    - Creating projects
    - Configuring pipelines
    - Initial onboarding
    """
    context = {}
    if request.plugin:
        if request.plugin not in PLUGIN_CONFIGS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown plugin: {request.plugin}. Available: {list(PLUGIN_CONFIGS.keys())}",
            )
        context["plugin"] = request.plugin

    # Create session
    session = setup_chatbot_service.create_session(
        tenant_id=tenant_id,
        user_id=str(current_user.id),
        flow_type=request.flow_type,
        context=context,
    )

    # Start the flow or get welcome message
    if request.flow_type == "onboarding":
        response = await setup_chatbot_service.start_onboarding(
            tenant_id=tenant_id,
            user_id=str(current_user.id),
        )
        return StartSessionResponse(
            session_id=response.session_id,
            message=response.message,
            flow_type="onboarding",
            current_step=response.current_step,
        )

    if request.flow_type:
        # Start the specific flow
        response = await setup_chatbot_service._start_flow(
            session, request.flow_type, context
        )
    else:
        # Send welcome message
        welcome = ChatMessage(
            role="assistant",
            content="👋 Hi! I'm your setup assistant. I can help you connect data sources, create projects, and configure your analytics. What would you like to do?",
            quick_replies=[
                {"label": "Connect a data source", "value": "connect", "icon": "🔗"},
                {"label": "Create a project", "value": "create project", "icon": "📦"},
                {"label": "Start onboarding", "value": "__start_onboarding__", "icon": "🚀"},
                {"label": "What can you do?", "value": "__capabilities__", "icon": "❓"},
            ],
        )
        session.messages.append(welcome)
        setup_chatbot_service.save_session(session)

        return StartSessionResponse(
            session_id=session.id,
            message=welcome,
            flow_type=None,
            current_step=None,
        )

    return StartSessionResponse(
        session_id=session.id,
        message=response.message,
        flow_type=request.flow_type,
        current_step=response.current_step,
    )


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Send a message to the setup assistant.

    The assistant will process your message and respond with:
    - Guidance for the current step
    - Quick reply options
    - Validation errors if input is invalid
    - Confirmation of completed actions
    """
    session = setup_chatbot_service.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Verify ownership
    if session.user_id != str(current_user.id) or session.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    if not session.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is no longer active",
        )

    # Process the message
    response = await setup_chatbot_service.process_message(
        session=session,
        user_message=request.message,
    )

    return response


@router.get("/sessions/{session_id}", response_model=SessionInfoResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get information about a session."""
    session = setup_chatbot_service.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.user_id != str(current_user.id) or session.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    return SessionInfoResponse(
        session_id=session.id,
        flow_type=session.flow_type,
        current_step=session.current_step,
        is_active=session.is_active,
        message_count=len(session.messages),
        collected_data=session.data,
    )


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessage])
async def get_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get all messages in a session."""
    session = setup_chatbot_service.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.user_id != str(current_user.id) or session.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    return session.messages


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Delete a session."""
    session = setup_chatbot_service.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.user_id != str(current_user.id) or session.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    setup_chatbot_service.delete_session(session_id)

    return {"status": "deleted", "session_id": session_id}


@router.post("/sessions/{session_id}/cancel")
async def cancel_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Cancel the current flow in a session."""
    session = setup_chatbot_service.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.user_id != str(current_user.id) or session.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    response = await setup_chatbot_service._cancel_flow(session)

    return response


@router.get("/plugins", response_model=PluginListResponse)
async def list_plugins(
    current_user: User = Depends(get_current_user),
):
    """List all available plugins for data source connections.

    Returns information about each plugin including:
    - Required and optional configuration fields
    - Authentication type
    - Supported scopes (repos, projects, boards, etc.)
    """
    plugins = [
        PluginInfo(
            plugin_type=key,
            display_name=config.display_name,
            description=config.description,
            icon=config.icon,
            required_fields=config.required_fields,
            optional_fields=config.optional_fields,
            auth_type=config.auth_type,
            endpoint_required=config.endpoint_required,
            scopes_supported=config.scopes_supported,
        )
        for key, config in PLUGIN_CONFIGS.items()
    ]

    return PluginListResponse(plugins=plugins)


@router.post("/quick-setup/{plugin}")
async def quick_setup_connection(
    plugin: str,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Quick start a connection setup for a specific plugin.

    This is a shortcut that creates a session and starts the connection
    flow for the specified plugin.
    """
    if plugin not in PLUGIN_CONFIGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown plugin: {plugin}",
        )

    # Create session with plugin context
    session = setup_chatbot_service.create_session(
        tenant_id=tenant_id,
        user_id=str(current_user.id),
        flow_type="connection",
        context={"plugin": plugin},
    )

    # Start the connection flow
    response = await setup_chatbot_service._start_connection_flow(
        session, plugin
    )

    return {
        "session_id": session.id,
        "message": response.message,
        "current_step": response.current_step,
        "plugin": plugin,
        "plugin_info": PLUGIN_CONFIGS[plugin],
    }


@router.post("/onboarding")
async def start_onboarding(
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Start the onboarding flow for new users.

    This comprehensive flow guides users through:
    1. Creating their first project
    2. Connecting their primary data source
    3. Understanding DORA metrics
    4. Setting up initial dashboards
    """
    response = await setup_chatbot_service.start_onboarding(
        tenant_id=tenant_id,
        user_id=str(current_user.id),
    )

    return {
        "session_id": response.session_id,
        "message": response.message,
        "current_step": response.current_step,
        "flow_type": "onboarding",
    }
