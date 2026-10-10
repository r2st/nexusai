"""Extension API endpoints for IDE integrations."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
import structlog

from app.api.deps import get_current_user
from app.models.user import User
from app.services.extensions import (
    ExtensionService,
    get_extension_service,
    AnalysisRequest,
    DiagnosticRequest,
    DiagnosticResult,
    CompletionRequest,
    CompletionItem,
    ChatRequest,
    ChatResponse,
    ExtensionConfig,
    ExtensionCapabilities,
    Position,
    AnalysisIssue,
    QuickFix,
    HoverInfo,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/extensions", tags=["extensions"])


# Request/Response Models
class HoverRequest(BaseModel):
    """Request for hover information."""

    file_uri: str
    content: str
    position: Position
    language_id: str


class QuickFixRequest(BaseModel):
    """Request for quick fixes."""

    issue: AnalysisIssue
    file_uri: str
    content: str
    language_id: str


class ConfigUpdateRequest(BaseModel):
    """Request to update extension config."""

    config: ExtensionConfig


class AnalyzeResponse(BaseModel):
    """Response for analysis endpoint."""

    file_uri: str
    version: int
    issue_count: int
    error_count: int
    warning_count: int
    security_issue_count: int
    analysis_time_ms: float
    issues: list[AnalysisIssue]
    metrics: dict[str, Any]


# Dependencies
async def get_ext_service() -> ExtensionService:
    """Get extension service instance."""
    return get_extension_service()


# Endpoints
@router.get("/capabilities", response_model=ExtensionCapabilities)
async def get_capabilities(
    service: Annotated[ExtensionService, Depends(get_ext_service)],
) -> ExtensionCapabilities:
    """Get extension API capabilities.

    Returns the features supported by the extension API,
    allowing clients to adapt their behavior accordingly.
    """
    return service.get_capabilities()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_file(
    request: AnalysisRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExtensionService, Depends(get_ext_service)],
) -> AnalyzeResponse:
    """Analyze a file for issues and suggestions.

    Performs comprehensive code analysis including:
    - Code smell detection
    - Security vulnerability scanning
    - Best practice violations
    - Complexity metrics

    Returns issues with severity, category, and quick fix suggestions.
    """
    try:
        result = await service.analyze(request)

        return AnalyzeResponse(
            file_uri=result.file_uri,
            version=result.version,
            issue_count=len(result.issues),
            error_count=result.error_count,
            warning_count=result.warning_count,
            security_issue_count=len(result.security_issues),
            analysis_time_ms=result.analysis_time_ms,
            issues=result.issues,
            metrics=result.metrics,
        )

    except Exception as e:
        logger.error("Code analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Code analysis failed. Please try again later.",
        )


@router.post("/diagnostics", response_model=DiagnosticResult)
async def get_diagnostics(
    request: DiagnosticRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExtensionService, Depends(get_ext_service)],
) -> DiagnosticResult:
    """Get quick diagnostics for a file.

    Lightweight analysis that returns only errors and warnings,
    suitable for real-time feedback while typing.
    """
    try:
        return await service.get_diagnostics(request)
    except Exception as e:
        logger.error("Diagnostics failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Diagnostics failed. Please try again later.",
        )


@router.post("/completions", response_model=list[CompletionItem])
async def get_completions(
    request: CompletionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExtensionService, Depends(get_ext_service)],
) -> list[CompletionItem]:
    """Get AI-powered code completions.

    Returns intelligent code suggestions based on context,
    using the configured LLM model.
    """
    try:
        return await service.get_completions(request)
    except Exception as e:
        logger.error("Completions failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate completions. Please try again later.",
        )


@router.post("/hover", response_model=HoverInfo | None)
async def get_hover(
    request: HoverRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExtensionService, Depends(get_ext_service)],
) -> HoverInfo | None:
    """Get hover information at a position.

    Returns documentation and type information for the
    symbol at the specified position.
    """
    try:
        return await service.get_hover_info(
            content=request.content,
            position=request.position,
            language_id=request.language_id,
        )
    except Exception as e:
        logger.error("Hover info failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve hover information. Please try again later.",
        )


@router.post("/quick-fixes", response_model=list[QuickFix])
async def get_quick_fixes(
    request: QuickFixRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExtensionService, Depends(get_ext_service)],
) -> list[QuickFix]:
    """Get quick fix actions for an issue.

    Returns available fix actions including AI-generated
    code fixes when available.
    """
    try:
        return await service.get_quick_fixes(
            issue=request.issue,
            content=request.content,
            language_id=request.language_id,
        )
    except Exception as e:
        logger.error("Quick fixes failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate quick fixes. Please try again later.",
        )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExtensionService, Depends(get_ext_service)],
) -> ChatResponse:
    """Chat with the AI assistant.

    Supports context-aware conversations with code selection,
    explicit commands (explain, fix, refactor, etc.), and
    follow-up questions.
    """
    try:
        return await service.chat(request, user_id=str(current_user.id))
    except Exception as e:
        logger.error("Extension chat failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat request failed. Please try again later.",
        )


@router.get("/config", response_model=ExtensionConfig)
async def get_config(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExtensionService, Depends(get_ext_service)],
) -> ExtensionConfig:
    """Get current extension configuration."""
    return service.config


@router.put("/config", response_model=ExtensionConfig)
async def update_config(
    request: ConfigUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExtensionService, Depends(get_ext_service)],
) -> ExtensionConfig:
    """Update extension configuration."""
    service.config = request.config
    return service.config


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Check extension service health."""
    return {"status": "healthy", "service": "extensions"}


# WebSocket for real-time sync
class ConnectionManager:
    """Manages WebSocket connections for real-time sync."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: str, message: dict[str, Any]):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

    async def broadcast(self, message: dict[str, Any]):
        for connections in self.active_connections.values():
            for connection in connections:
                await connection.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/{token}")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    service: Annotated[ExtensionService, Depends(get_ext_service)],
):
    """WebSocket endpoint for real-time sync.

    Provides real-time updates for:
    - Analysis results
    - Diagnostic updates
    - Configuration changes
    """
    # Validate token and get user
    # For now, use token as user_id (should validate JWT in production)
    user_id = token

    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")

            if event_type == "analyze":
                # Trigger analysis and send result
                request = AnalysisRequest(**data.get("payload", {}))
                result = await service.analyze(request)
                await websocket.send_json({
                    "type": "analysis_complete",
                    "payload": result.model_dump(),
                })

            elif event_type == "diagnostics":
                # Trigger diagnostics and send result
                request = DiagnosticRequest(**data.get("payload", {}))
                result = await service.get_diagnostics(request)
                await websocket.send_json({
                    "type": "diagnostics_updated",
                    "payload": result.model_dump(),
                })

            elif event_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
