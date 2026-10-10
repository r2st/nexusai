"""Real-time Collaboration API endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, WebSocket, WebSocketDisconnect, status
import structlog
from app.api.deps import get_current_user
from app.models.user import User

logger = structlog.get_logger()
from pydantic import BaseModel, Field

from app.services.collaboration import (
    get_collaboration_service,
    get_presence_service,
    get_session_manager,
    get_annotation_service,
    get_activity_feed,
    PresenceStatus,
    SessionType,
    AnnotationType,
    ActivityType,
)

router = APIRouter(prefix="/collaboration", tags=["collaboration"])


# --- Request/Response Models ---

class UpdatePresenceRequest(BaseModel):
    """Request to update user presence."""
    user_id: str
    username: str
    status: PresenceStatus | None = None
    status_message: str | None = None
    current_project_id: str | None = None
    current_file_path: str | None = None
    current_line: int | None = None
    client_type: str = "web"
    client_version: str | None = None
    avatar_url: str | None = None


class HeartbeatRequest(BaseModel):
    """Heartbeat request."""
    user_id: str


class CreateSessionRequest(BaseModel):
    """Request to create a session."""
    organization_id: str = Field(..., min_length=1, max_length=200)
    session_type: SessionType
    title: str = Field(..., min_length=1, max_length=500)
    host_user_id: str = Field(..., min_length=1, max_length=200)
    host_username: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    project_id: str | None = Field(default=None, max_length=200)
    file_path: str | None = Field(default=None, max_length=1024)
    pr_id: str | None = Field(default=None, max_length=200)
    is_public: bool = False
    max_participants: int = Field(default=10, ge=1, le=100)


class JoinSessionRequest(BaseModel):
    """Request to join a session."""
    user_id: str
    username: str
    role: str = "participant"


class SessionMessageRequest(BaseModel):
    """Request to send a session message."""
    user_id: str = Field(..., min_length=1, max_length=200)
    username: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=50000)
    message_type: str = Field(default="text", max_length=50)


class CreateAnnotationRequest(BaseModel):
    """Request to create an annotation."""
    organization_id: str = Field(..., min_length=1, max_length=200)
    project_id: str = Field(..., min_length=1, max_length=200)
    file_path: str = Field(..., min_length=1, max_length=1024)
    start_line: int = Field(..., ge=1, le=1000000)
    end_line: int = Field(..., ge=1, le=1000000)
    annotation_type: AnnotationType
    content: str = Field(..., min_length=1, max_length=50000)
    author_id: str = Field(..., min_length=1, max_length=200)
    author_username: str = Field(..., min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=500)
    start_column: int | None = Field(default=None, ge=0, le=10000)
    end_column: int | None = Field(default=None, ge=0, le=10000)
    code_snippet: str | None = Field(default=None, max_length=50000)
    mentions: list[str] = Field(default_factory=list, max_length=50)
    commit_sha: str | None = Field(default=None, max_length=64)
    branch: str | None = Field(default=None, max_length=200)
    parent_id: str | None = Field(default=None, max_length=200)


class UpdateAnnotationRequest(BaseModel):
    """Request to update an annotation."""
    user_id: str
    content: str | None = None
    title: str | None = None
    annotation_type: AnnotationType | None = None
    mentions: list[str] | None = None


class ResolveAnnotationRequest(BaseModel):
    """Request to resolve an annotation."""
    resolved_by: str
    resolved_by_username: str


class JoinRoomRequest(BaseModel):
    """Request to join a room."""
    user_id: str
    room_type: str
    room_key: str


# --- Presence Endpoints ---

@router.post("/presence")
async def update_presence(request: UpdatePresenceRequest, _current_user: User = Depends(get_current_user)):
    """Update user presence."""
    service = get_collaboration_service()
    presence = await service.update_user_presence(
        user_id=request.user_id,
        username=request.username,
        status=request.status,
        status_message=request.status_message,
        current_project_id=request.current_project_id,
        current_file_path=request.current_file_path,
        current_line=request.current_line,
        client_type=request.client_type,
        client_version=request.client_version,
        avatar_url=request.avatar_url,
    )
    return {"presence": presence.model_dump()}


@router.get("/presence/{user_id}")
async def get_presence(user_id: str, _current_user: User = Depends(get_current_user)):
    """Get user presence."""
    service = get_collaboration_service()
    presence = await service.get_user_presence(user_id)
    if not presence:
        raise HTTPException(status_code=404, detail="User not found")
    return {"presence": presence.model_dump()}


@router.get("/presence")
async def get_team_presence(
    project_id: str | None = None,
    status: PresenceStatus | None = None,
    user_ids: str | None = None,  # Comma-separated
    _current_user: User = Depends(get_current_user),
):
    """Get team presence."""
    service = get_collaboration_service()
    user_id_list = user_ids.split(",") if user_ids else None
    presences = await service.get_team_presence(
        user_ids=user_id_list,
        project_id=project_id,
        status=status,
    )
    return {"presences": [p.model_dump() for p in presences]}


@router.post("/presence/heartbeat")
async def heartbeat(request: HeartbeatRequest, _current_user: User = Depends(get_current_user)):
    """Process heartbeat."""
    service = get_collaboration_service()
    presence = await service.heartbeat(request.user_id)
    if not presence:
        raise HTTPException(status_code=404, detail="User not found")
    return {"presence": presence.model_dump()}


@router.post("/presence/{user_id}/offline")
async def set_offline(user_id: str, _current_user: User = Depends(get_current_user)):
    """Set user offline."""
    service = get_collaboration_service()
    presence = await service.set_user_offline(user_id)
    if not presence:
        raise HTTPException(status_code=404, detail="User not found")
    return {"presence": presence.model_dump()}


@router.get("/presence/file/{project_id}")
async def get_users_in_file(
    project_id: str,
    file_path: str,
    _current_user: User = Depends(get_current_user),
):
    """Get users viewing a specific file."""
    service = get_collaboration_service()
    users = await service.get_users_in_file(project_id, file_path)
    return {"users": [u.model_dump() for u in users]}


# --- Session Endpoints ---

@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(request: CreateSessionRequest, _current_user: User = Depends(get_current_user)):
    """Create a new collaborative session."""
    service = get_collaboration_service()
    session = await service.create_session(
        organization_id=request.organization_id,
        session_type=request.session_type,
        title=request.title,
        host_user_id=request.host_user_id,
        host_username=request.host_username,
        description=request.description,
        project_id=request.project_id,
        file_path=request.file_path,
        pr_id=request.pr_id,
        is_public=request.is_public,
        max_participants=request.max_participants,
    )
    return {"session": session.model_dump()}


@router.get("/sessions")
async def list_sessions(
    organization_id: str | None = None,
    session_type: SessionType | None = None,
    project_id: str | None = None,
    user_id: str | None = None,
    is_active: bool = True,
    _current_user: User = Depends(get_current_user),
):
    """List collaborative sessions."""
    service = get_collaboration_service()
    sessions = await service.list_sessions(
        organization_id=organization_id,
        session_type=session_type,
        project_id=project_id,
        user_id=user_id,
        is_active=is_active,
    )
    return {"sessions": [s.model_dump() for s in sessions]}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, _current_user: User = Depends(get_current_user)):
    """Get a session by ID."""
    service = get_collaboration_service()
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session.model_dump()}


@router.post("/sessions/{session_id}/join")
async def join_session(session_id: str, request: JoinSessionRequest, _current_user: User = Depends(get_current_user)):
    """Join a session."""
    service = get_collaboration_service()
    session = await service.join_session(
        session_id=session_id,
        user_id=request.user_id,
        username=request.username,
        role=request.role,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or full")
    return {"session": session.model_dump()}


@router.post("/sessions/{session_id}/leave")
async def leave_session(session_id: str, user_id: str, _current_user: User = Depends(get_current_user)):
    """Leave a session."""
    service = get_collaboration_service()
    session = await service.leave_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session.model_dump()}


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str, ended_by: str, _current_user: User = Depends(get_current_user)):
    """End a session."""
    service = get_collaboration_service()
    session = await service.end_session(session_id, ended_by)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or not authorized")
    return {"session": session.model_dump()}


@router.post("/sessions/{session_id}/messages")
async def send_session_message(session_id: str, request: SessionMessageRequest, _current_user: User = Depends(get_current_user)):
    """Send a message in a session."""
    service = get_collaboration_service()
    message = await service.send_session_message(
        session_id=session_id,
        user_id=request.user_id,
        username=request.username,
        message=request.message,
        message_type=request.message_type,
    )
    if not message:
        raise HTTPException(status_code=404, detail="Session not found or not active")
    return {"message": message}


# --- Annotation Endpoints ---

@router.post("/annotations", status_code=status.HTTP_201_CREATED)
async def create_annotation(request: CreateAnnotationRequest, _current_user: User = Depends(get_current_user)):
    """Create a new annotation."""
    service = get_collaboration_service()
    annotation = await service.create_annotation(
        organization_id=request.organization_id,
        project_id=request.project_id,
        file_path=request.file_path,
        start_line=request.start_line,
        end_line=request.end_line,
        annotation_type=request.annotation_type,
        content=request.content,
        author_id=request.author_id,
        author_username=request.author_username,
        title=request.title,
        mentions=request.mentions,
        commit_sha=request.commit_sha,
        branch=request.branch,
        parent_id=request.parent_id,
    )
    return {"annotation": annotation.model_dump()}


@router.get("/annotations")
async def list_annotations(
    organization_id: str,
    project_id: str | None = None,
    file_path: str | None = None,
    annotation_type: AnnotationType | None = None,
    resolved: bool | None = None,
    limit: int = Query(default=100, le=500),
    _current_user: User = Depends(get_current_user),
):
    """List annotations."""
    service = get_collaboration_service()
    annotations = await service.list_annotations(
        organization_id=organization_id,
        project_id=project_id,
        file_path=file_path,
        annotation_type=annotation_type,
        resolved=resolved,
        limit=limit,
    )
    return {"annotations": [a.model_dump() for a in annotations]}


@router.get("/annotations/{annotation_id}")
async def get_annotation(annotation_id: str, _current_user: User = Depends(get_current_user)):
    """Get an annotation."""
    service = get_collaboration_service()
    annotation = await service.get_annotation(annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return {"annotation": annotation.model_dump()}


@router.put("/annotations/{annotation_id}")
async def update_annotation(annotation_id: str, request: UpdateAnnotationRequest, _current_user: User = Depends(get_current_user)):
    """Update an annotation."""
    annotations = get_annotation_service()
    annotation = await annotations.update_annotation(
        annotation_id=annotation_id,
        user_id=request.user_id,
        content=request.content,
        title=request.title,
        annotation_type=request.annotation_type,
        mentions=request.mentions,
    )
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found or not authorized")
    return {"annotation": annotation.model_dump()}


@router.delete("/annotations/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_annotation(annotation_id: str, user_id: str, _current_user: User = Depends(get_current_user))-> None:
    """Delete an annotation."""
    annotations = get_annotation_service()
    success = await annotations.delete_annotation(annotation_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Annotation not found or not authorized")


@router.post("/annotations/{annotation_id}/resolve")
async def resolve_annotation(annotation_id: str, request: ResolveAnnotationRequest, _current_user: User = Depends(get_current_user)):
    """Resolve an annotation."""
    service = get_collaboration_service()
    annotation = await service.resolve_annotation(
        annotation_id=annotation_id,
        resolved_by=request.resolved_by,
        resolved_by_username=request.resolved_by_username,
    )
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return {"annotation": annotation.model_dump()}


@router.post("/annotations/{annotation_id}/unresolve")
async def unresolve_annotation(annotation_id: str, _current_user: User = Depends(get_current_user)):
    """Unresolve an annotation."""
    annotations = get_annotation_service()
    annotation = await annotations.unresolve_annotation(annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return {"annotation": annotation.model_dump()}


@router.get("/annotations/{annotation_id}/replies")
async def get_annotation_replies(annotation_id: str, _current_user: User = Depends(get_current_user)):
    """Get replies to an annotation."""
    annotations = get_annotation_service()
    replies = await annotations.get_replies(annotation_id)
    return {"replies": [r.model_dump() for r in replies]}


@router.get("/annotations/mentions/{user_id}")
async def get_user_mentions(user_id: str, unresolved_only: bool = True, _current_user: User = Depends(get_current_user)):
    """Get annotations mentioning a user."""
    service = get_collaboration_service()
    mentions = await service.get_user_mentions(user_id, unresolved_only)
    return {"mentions": [m.model_dump() for m in mentions]}


# --- Activity Feed Endpoints ---

@router.get("/activity/organization/{organization_id}")
async def get_organization_activity(
    organization_id: str,
    viewer_user_id: str | None = None,
    project_id: str | None = None,
    activity_types: str | None = None,  # Comma-separated
    since: datetime | None = None,
    limit: int = Query(default=50, le=200),
    _current_user: User = Depends(get_current_user),
):
    """Get organization activity feed."""
    service = get_collaboration_service()

    type_list = None
    if activity_types:
        type_list = [ActivityType(t.strip()) for t in activity_types.split(",")]

    events = await service.get_organization_activity(
        organization_id=organization_id,
        viewer_user_id=viewer_user_id,
        activity_types=type_list,
        project_id=project_id,
        since=since,
        limit=limit,
    )
    return {"events": [e.model_dump() for e in events]}


@router.get("/activity/project/{project_id}")
async def get_project_activity(
    project_id: str,
    viewer_user_id: str | None = None,
    activity_types: str | None = None,
    since: datetime | None = None,
    limit: int = Query(default=50, le=200),
    _current_user: User = Depends(get_current_user),
):
    """Get project activity feed."""
    service = get_collaboration_service()

    type_list = None
    if activity_types:
        type_list = [ActivityType(t.strip()) for t in activity_types.split(",")]

    events = await service.get_project_activity(
        project_id=project_id,
        viewer_user_id=viewer_user_id,
        activity_types=type_list,
        since=since,
        limit=limit,
    )
    return {"events": [e.model_dump() for e in events]}


@router.get("/activity/user/{user_id}")
async def get_user_activity(
    user_id: str,
    viewer_user_id: str | None = None,
    _current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, le=200),
):
    """Get user activity feed."""
    service = get_collaboration_service()
    events = await service.get_user_activity(
        user_id=user_id,
        viewer_user_id=viewer_user_id,
        limit=limit,
    )
    return {"events": [e.model_dump() for e in events]}


@router.get("/activity/summary/{organization_id}")
async def get_activity_summary(
    organization_id: str,
    project_id: str | None = None,
    _current_user: User = Depends(get_current_user),
    days: int = Query(default=7, le=30),
):
    """Get activity summary."""
    service = get_collaboration_service()
    summary = await service.get_activity_summary(
        organization_id=organization_id,
        project_id=project_id,
        days=days,
    )
    return {"summary": summary}


# --- Room Endpoints ---

@router.post("/rooms/join")
async def join_room(request: JoinRoomRequest, _current_user: User = Depends(get_current_user)):
    """Join a collaboration room."""
    service = get_collaboration_service()
    room = await service.join_room(
        user_id=request.user_id,
        room_type=request.room_type,
        room_key=request.room_key,
    )
    return {"room": room.model_dump()}


@router.post("/rooms/leave")
async def leave_room(request: JoinRoomRequest, _current_user: User = Depends(get_current_user)):
    """Leave a collaboration room."""
    service = get_collaboration_service()
    room = await service.leave_room(
        user_id=request.user_id,
        room_type=request.room_type,
        room_key=request.room_key,
    )
    return {"room": room.model_dump() if room else None}


@router.get("/rooms/{room_type}/{room_key}/members")
async def get_room_members(room_type: str, room_key: str, _current_user: User = Depends(get_current_user)):
    """Get room members."""
    service = get_collaboration_service()
    members = await service.get_room_members(room_type, room_key)
    return {"members": [m.model_dump() for m in members]}


# --- Dashboard Endpoint ---

@router.get("/dashboard/{organization_id}")
async def get_collaboration_dashboard(
    organization_id: str,
    project_id: str | None = None,
    _current_user: User = Depends(get_current_user),
):
    """Get collaboration dashboard data."""
    service = get_collaboration_service()
    dashboard = await service.get_collaboration_dashboard(
        organization_id=organization_id,
        project_id=project_id,
    )
    return {"dashboard": dashboard}


# --- WebSocket Endpoint ---

# Connection manager for WebSocket
class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[str, dict[str, WebSocket]] = {}  # room_id -> {user_id: ws}

    async def connect(
        self,
        websocket: WebSocket,
        room_id: str,
        user_id: str,
    ):
        """Connect to a room."""
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
        self.active_connections[room_id][user_id] = websocket

    def disconnect(self, room_id: str, user_id: str):
        """Disconnect from a room."""
        if room_id in self.active_connections:
            self.active_connections[room_id].pop(user_id, None)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(
        self,
        room_id: str,
        message: dict[str, Any],
        exclude_user_id: str | None = None,
    ):
        """Broadcast message to room."""
        if room_id not in self.active_connections:
            return

        dead_connections = []
        for user_id, websocket in self.active_connections[room_id].items():
            if user_id != exclude_user_id:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.debug("Removing dead websocket connection", room_id=room_id, user_id=user_id)
                    dead_connections.append(user_id)

        for user_id in dead_connections:
            self.active_connections[room_id].pop(user_id, None)
        if room_id in self.active_connections and not self.active_connections[room_id]:
            del self.active_connections[room_id]


manager = ConnectionManager()


@router.websocket("/ws/{room_type}/{room_key}/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_type: str,
    room_key: str,
    user_id: str,
):
    """WebSocket endpoint for real-time collaboration."""
    room_id = f"{room_type}:{room_key}"
    service = get_collaboration_service()

    await manager.connect(websocket, room_id, user_id)

    # Join the room
    await service.join_room(user_id, room_type, room_key)

    try:
        # Broadcast join event
        await manager.broadcast(
            room_id,
            {
                "type": "user_joined",
                "user_id": user_id,
                "room_type": room_type,
                "room_key": room_key,
            },
            exclude_user_id=user_id,
        )

        # Handle messages
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "presence_update":
                # Update presence and broadcast
                await manager.broadcast(
                    room_id,
                    {
                        "type": "presence_update",
                        "user_id": user_id,
                        "data": data.get("data", {}),
                    },
                    exclude_user_id=user_id,
                )

            elif message_type == "cursor_move":
                # Broadcast cursor position
                await manager.broadcast(
                    room_id,
                    {
                        "type": "cursor_move",
                        "user_id": user_id,
                        "line": data.get("line"),
                        "column": data.get("column"),
                        "file_path": data.get("file_path"),
                    },
                    exclude_user_id=user_id,
                )

            elif message_type == "selection_change":
                # Broadcast selection change
                await manager.broadcast(
                    room_id,
                    {
                        "type": "selection_change",
                        "user_id": user_id,
                        "selections": data.get("selections", []),
                    },
                    exclude_user_id=user_id,
                )

            elif message_type == "chat_message":
                # Broadcast chat message
                await manager.broadcast(
                    room_id,
                    {
                        "type": "chat_message",
                        "user_id": user_id,
                        "message": data.get("message"),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

            elif message_type == "heartbeat":
                # Process heartbeat
                await service.heartbeat(user_id)
                await websocket.send_json({"type": "heartbeat_ack"})

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(room_id, user_id)
        await service.leave_room(user_id, room_type, room_key)

        # Broadcast leave event
        await manager.broadcast(
            room_id,
            {
                "type": "user_left",
                "user_id": user_id,
            },
        )
