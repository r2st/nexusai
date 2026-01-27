"""Unified Collaboration Service."""

from datetime import datetime
from typing import Any

from app.services.collaboration.models import (
    PresenceStatus,
    UserPresence,
    SessionType,
    SharedSession,
    AnnotationType,
    CodeAnnotation,
    ActivityType,
    ActivityEvent,
    CollaborationRoom,
)
from app.services.collaboration.presence import (
    PresenceService,
    get_presence_service,
)
from app.services.collaboration.sessions import (
    SessionManager,
    get_session_manager,
)
from app.services.collaboration.annotations import (
    AnnotationService,
    get_annotation_service,
)
from app.services.collaboration.activity import (
    ActivityFeed,
    get_activity_feed,
)


class CollaborationService:
    """
    Unified service for Real-time Collaboration.

    Orchestrates presence, sessions, annotations, and activity feeds.
    """

    def __init__(self):
        self._presence = get_presence_service()
        self._sessions = get_session_manager()
        self._annotations = get_annotation_service()
        self._activity = get_activity_feed()

    # Presence Operations

    async def update_user_presence(
        self,
        user_id: str,
        username: str,
        status: PresenceStatus | None = None,
        status_message: str | None = None,
        current_project_id: str | None = None,
        current_file_path: str | None = None,
        current_line: int | None = None,
        client_type: str = "web",
        client_version: str | None = None,
        avatar_url: str | None = None,
    ) -> UserPresence:
        """Update user presence."""
        return await self._presence.update_presence(
            user_id=user_id,
            username=username,
            status=status,
            status_message=status_message,
            current_project_id=current_project_id,
            current_file_path=current_file_path,
            current_line=current_line,
            client_type=client_type,
            client_version=client_version,
            avatar_url=avatar_url,
        )

    async def get_user_presence(self, user_id: str) -> UserPresence | None:
        """Get user presence."""
        return await self._presence.get_presence(user_id)

    async def get_team_presence(
        self,
        user_ids: list[str] | None = None,
        project_id: str | None = None,
        status: PresenceStatus | None = None,
    ) -> list[UserPresence]:
        """Get presence for multiple users."""
        return await self._presence.get_presences(user_ids, project_id, status)

    async def set_user_offline(self, user_id: str) -> UserPresence | None:
        """Set user as offline."""
        return await self._presence.set_offline(user_id)

    async def heartbeat(self, user_id: str) -> UserPresence | None:
        """Process heartbeat."""
        return await self._presence.heartbeat(user_id)

    async def get_users_in_file(
        self,
        project_id: str,
        file_path: str,
    ) -> list[UserPresence]:
        """Get users viewing a file."""
        return await self._presence.get_users_in_file(project_id, file_path)

    # Session Operations

    async def create_session(
        self,
        organization_id: str,
        session_type: SessionType,
        title: str,
        host_user_id: str,
        host_username: str,
        description: str | None = None,
        project_id: str | None = None,
        file_path: str | None = None,
        pr_id: str | None = None,
        is_public: bool = False,
        max_participants: int = 10,
    ) -> SharedSession:
        """Create a new session."""
        session = await self._sessions.create_session(
            organization_id=organization_id,
            session_type=session_type,
            title=title,
            host_user_id=host_user_id,
            host_username=host_username,
            description=description,
            project_id=project_id,
            file_path=file_path,
            pr_id=pr_id,
            is_public=is_public,
            max_participants=max_participants,
        )

        # Record activity
        await self._activity.record_session_started(
            organization_id=organization_id,
            project_id=project_id,
            actor_id=host_user_id,
            actor_username=host_username,
            session_id=session.id,
            session_type=session_type.value,
            session_title=title,
        )

        return session

    async def get_session(self, session_id: str) -> SharedSession | None:
        """Get a session."""
        return await self._sessions.get_session(session_id)

    async def list_sessions(
        self,
        organization_id: str | None = None,
        session_type: SessionType | None = None,
        project_id: str | None = None,
        user_id: str | None = None,
        is_active: bool | None = True,
    ) -> list[SharedSession]:
        """List sessions."""
        return await self._sessions.list_sessions(
            organization_id=organization_id,
            session_type=session_type,
            project_id=project_id,
            user_id=user_id,
            is_active=is_active,
        )

    async def join_session(
        self,
        session_id: str,
        user_id: str,
        username: str,
        role: str = "participant",
    ) -> SharedSession | None:
        """Join a session."""
        session = await self._sessions.join_session(
            session_id=session_id,
            user_id=user_id,
            username=username,
            role=role,
        )

        if session:
            # Record activity
            await self._activity.record_event(
                organization_id=session.organization_id,
                project_id=session.project_id,
                activity_type=ActivityType.SESSION_JOINED,
                title=f"Joined session: {session.title}",
                actor_id=user_id,
                actor_username=username,
                target_type="session",
                target_id=session_id,
            )

        return session

    async def leave_session(
        self,
        session_id: str,
        user_id: str,
    ) -> SharedSession | None:
        """Leave a session."""
        return await self._sessions.leave_session(session_id, user_id)

    async def end_session(
        self,
        session_id: str,
        ended_by: str,
    ) -> SharedSession | None:
        """End a session."""
        return await self._sessions.end_session(session_id, ended_by)

    async def send_session_message(
        self,
        session_id: str,
        user_id: str,
        username: str,
        message: str,
        message_type: str = "text",
    ) -> dict[str, Any] | None:
        """Send a message in a session."""
        return await self._sessions.add_message(
            session_id=session_id,
            user_id=user_id,
            username=username,
            message=message,
            message_type=message_type,
        )

    # Annotation Operations

    async def create_annotation(
        self,
        organization_id: str,
        project_id: str,
        file_path: str,
        start_line: int,
        end_line: int,
        annotation_type: AnnotationType,
        content: str,
        author_id: str,
        author_username: str,
        title: str | None = None,
        mentions: list[str] | None = None,
        commit_sha: str | None = None,
        branch: str | None = None,
        parent_id: str | None = None,
    ) -> CodeAnnotation:
        """Create an annotation."""
        annotation = await self._annotations.create_annotation(
            organization_id=organization_id,
            project_id=project_id,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            annotation_type=annotation_type,
            content=content,
            author_id=author_id,
            author_username=author_username,
            title=title,
            mentions=mentions,
            commit_sha=commit_sha,
            branch=branch,
            parent_id=parent_id,
        )

        # Record activity (only for top-level annotations)
        if not parent_id:
            await self._activity.record_annotation_created(
                organization_id=organization_id,
                project_id=project_id,
                actor_id=author_id,
                actor_username=author_username,
                annotation_id=annotation.id,
                annotation_type=annotation_type.value,
                file_path=file_path,
                line=start_line,
                content_preview=content[:100],
            )

        # Record mention events
        if mentions:
            for mentioned_user_id in mentions:
                await self._activity.record_event(
                    organization_id=organization_id,
                    project_id=project_id,
                    activity_type=ActivityType.MENTION,
                    title=f"Mentioned by {author_username}",
                    description=content[:100],
                    actor_id=author_id,
                    actor_username=author_username,
                    target_type="annotation",
                    target_id=annotation.id,
                    is_public=False,
                    visible_to_user_ids=[mentioned_user_id],
                )

        return annotation

    async def get_annotation(self, annotation_id: str) -> CodeAnnotation | None:
        """Get an annotation."""
        return await self._annotations.get_annotation(annotation_id)

    async def list_annotations(
        self,
        organization_id: str,
        project_id: str | None = None,
        file_path: str | None = None,
        annotation_type: AnnotationType | None = None,
        resolved: bool | None = None,
        limit: int = 100,
    ) -> list[CodeAnnotation]:
        """List annotations."""
        return await self._annotations.list_annotations(
            organization_id=organization_id,
            project_id=project_id,
            file_path=file_path,
            annotation_type=annotation_type,
            resolved=resolved,
            limit=limit,
        )

    async def resolve_annotation(
        self,
        annotation_id: str,
        resolved_by: str,
        resolved_by_username: str,
    ) -> CodeAnnotation | None:
        """Resolve an annotation."""
        annotation = await self._annotations.resolve_annotation(
            annotation_id=annotation_id,
            resolved_by=resolved_by,
        )

        if annotation:
            # Record activity
            await self._activity.record_event(
                organization_id=annotation.organization_id,
                project_id=annotation.project_id,
                activity_type=ActivityType.ANNOTATION_RESOLVED,
                title=f"Resolved annotation on {annotation.file_path}:{annotation.start_line}",
                actor_id=resolved_by,
                actor_username=resolved_by_username,
                target_type="annotation",
                target_id=annotation_id,
            )

        return annotation

    async def get_file_annotations(
        self,
        organization_id: str,
        project_id: str,
        file_path: str,
        resolved: bool | None = None,
    ) -> list[CodeAnnotation]:
        """Get annotations for a file."""
        return await self._annotations.list_annotations(
            organization_id=organization_id,
            project_id=project_id,
            file_path=file_path,
            resolved=resolved,
        )

    async def get_user_mentions(
        self,
        user_id: str,
        unresolved_only: bool = True,
    ) -> list[CodeAnnotation]:
        """Get annotations mentioning a user."""
        return await self._annotations.get_user_mentions(user_id, unresolved_only)

    # Activity Feed Operations

    async def get_organization_activity(
        self,
        organization_id: str,
        viewer_user_id: str | None = None,
        activity_types: list[ActivityType] | None = None,
        project_id: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[ActivityEvent]:
        """Get organization activity feed."""
        return await self._activity.get_organization_feed(
            organization_id=organization_id,
            viewer_user_id=viewer_user_id,
            activity_types=activity_types,
            project_id=project_id,
            since=since,
            limit=limit,
        )

    async def get_project_activity(
        self,
        project_id: str,
        viewer_user_id: str | None = None,
        activity_types: list[ActivityType] | None = None,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[ActivityEvent]:
        """Get project activity feed."""
        return await self._activity.get_project_feed(
            project_id=project_id,
            viewer_user_id=viewer_user_id,
            activity_types=activity_types,
            since=since,
            limit=limit,
        )

    async def get_user_activity(
        self,
        user_id: str,
        viewer_user_id: str | None = None,
        limit: int = 50,
    ) -> list[ActivityEvent]:
        """Get user activity feed."""
        return await self._activity.get_user_feed(
            user_id=user_id,
            viewer_user_id=viewer_user_id,
            limit=limit,
        )

    async def get_activity_summary(
        self,
        organization_id: str,
        project_id: str | None = None,
        days: int = 7,
    ) -> dict[str, Any]:
        """Get activity summary."""
        return await self._activity.get_activity_summary(
            organization_id=organization_id,
            project_id=project_id,
            days=days,
        )

    # Room Operations (for WebSocket management)

    async def join_room(
        self,
        user_id: str,
        room_type: str,
        room_key: str,
    ) -> CollaborationRoom:
        """Join a collaboration room."""
        return await self._presence.join_room(user_id, room_type, room_key)

    async def leave_room(
        self,
        user_id: str,
        room_type: str,
        room_key: str,
    ) -> CollaborationRoom | None:
        """Leave a collaboration room."""
        return await self._presence.leave_room(user_id, room_type, room_key)

    async def get_room_members(
        self,
        room_type: str,
        room_key: str,
    ) -> list[UserPresence]:
        """Get room members."""
        return await self._presence.get_room_members(room_type, room_key)

    async def broadcast_recipients(
        self,
        room_type: str,
        room_key: str,
        exclude_user_id: str | None = None,
    ) -> list[str]:
        """Get list of users to broadcast to in a room."""
        return await self._presence.broadcast_to_room(
            room_type=room_type,
            room_key=room_key,
            event_type="",  # Not used for recipient list
            data={},
            exclude_user_id=exclude_user_id,
        )

    # Dashboard / Summary

    async def get_collaboration_dashboard(
        self,
        organization_id: str,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Get collaboration dashboard data."""
        # Get active users
        presences = await self._presence.get_presences(project_id=project_id)
        online_users = [p for p in presences if p.status != PresenceStatus.OFFLINE]

        # Get active sessions
        sessions = await self._sessions.list_sessions(
            organization_id=organization_id,
            project_id=project_id,
            is_active=True,
        )

        # Get annotation summary
        annotation_summary = await self._annotations.get_annotation_summary(
            organization_id=organization_id,
            project_id=project_id,
        )

        # Get activity summary
        activity_summary = await self._activity.get_activity_summary(
            organization_id=organization_id,
            project_id=project_id,
        )

        return {
            "online_users": len(online_users),
            "online_user_list": [
                {
                    "user_id": p.user_id,
                    "username": p.username,
                    "status": p.status.value,
                    "current_file": p.current_file_path,
                }
                for p in online_users[:20]
            ],
            "active_sessions": len(sessions),
            "sessions": [
                {
                    "id": s.id,
                    "type": s.session_type.value,
                    "title": s.title,
                    "participants": len([p for p in s.participants if p.is_active]),
                }
                for s in sessions[:10]
            ],
            "annotations": annotation_summary,
            "activity": activity_summary,
        }


# Singleton instance
_collaboration_service: CollaborationService | None = None


def get_collaboration_service() -> CollaborationService:
    """Get the collaboration service singleton."""
    global _collaboration_service
    if _collaboration_service is None:
        _collaboration_service = CollaborationService()
    return _collaboration_service
