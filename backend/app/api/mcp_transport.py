"""MCP HTTP Transport API endpoints.

Exposes the MCP server over HTTP, SSE, and WebSocket transports
for external LLM clients (Claude, Cursor, etc.) to connect.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
import structlog

from app.api.deps import get_current_user

from app.models.user import User
from app.services.mcp import (
    create_nexusai_mcp_server,
    MCPHTTPTransport,
    HTTPTransportConfig,
    create_mcp_http_transport,
    get_mcp_http_transport,
)


logger = structlog.get_logger()

router = APIRouter(tags=["mcp-transport"])

# Initialize HTTP transport lazily
_transport_initialized = False


def get_http_transport() -> MCPHTTPTransport:
    """Get or create the HTTP transport."""
    global _transport_initialized

    transport = get_mcp_http_transport()

    if transport is None:
        # Create transport with server factory
        config = HTTPTransportConfig(
            session_timeout_seconds=3600,
            max_sessions=1000,
            requests_per_minute=120,
            requests_per_second=20,
            require_auth=True,
        )

        transport = create_mcp_http_transport(
            server_factory=create_nexusai_mcp_server,
            config=config,
        )
        _transport_initialized = True

    return transport


# Get the transport router and include it
# The transport creates its own router with all MCP endpoints
def get_mcp_router() -> APIRouter:
    """Get the MCP transport router."""
    transport = get_http_transport()
    return transport.create_router(prefix="")


# Create a main router that includes transport endpoints
mcp_transport_router = APIRouter(prefix="/mcp", tags=["mcp-transport"])


@mcp_transport_router.get("/info", summary="Get MCP server information")
async def get_mcp_info(
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get MCP server information."""
    transport = get_http_transport()

    return {
        "name": "NexusAI MCP Server",
        "version": "1.0.0",
        "transports": ["http", "sse", "websocket"],
        "endpoints": {
            "jsonrpc": "/api/mcp",
            "session": "/api/mcp/session",
            "sse": "/api/mcp/sse/{session_id}",
            "websocket": "/api/mcp/ws/{session_id}",
        },
        "stats": {
            "sessions": transport.session_manager.get_stats(),
        },
    }


@mcp_transport_router.get("/tools", summary="List available MCP tools")
async def list_mcp_tools(
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List available MCP tools."""
    from app.services.mcp import get_all_tools_summary

    return get_all_tools_summary()


@mcp_transport_router.post("/start", summary="Start the MCP HTTP transport")
async def start_transport(
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Start the MCP HTTP transport."""
    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can manage MCP transport",
        )

    transport = get_http_transport()
    await transport.start()

    return {"status": "started"}


@mcp_transport_router.post("/stop", summary="Stop the MCP HTTP transport")
async def stop_transport(
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Stop the MCP HTTP transport."""
    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can manage MCP transport",
        )

    transport = get_http_transport()
    await transport.stop()

    return {"status": "stopped"}


# Include the transport's router for MCP protocol endpoints
# This needs to be done at app startup to include the dynamic router
def include_mcp_transport_routes(parent_router: APIRouter) -> None:
    """Include MCP transport routes in the parent router.

    Call this during app initialization.
    """
    transport = get_http_transport()
    transport_router = transport.create_router(prefix="/mcp")
    parent_router.include_router(transport_router)
    parent_router.include_router(mcp_transport_router)
