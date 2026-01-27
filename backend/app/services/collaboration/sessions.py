"""Session Manager for Real-time Collaboration."""

import uuid
from datetime import datetime
from typing import Any

from app.services.collaboration.models import (
    SessionType,
    SessionParticipant,
    SharedSession,
)


class SessionManager:
    """Service for managing collaborative sessions."""

    def __init__(self):
        # In-memory storage - replace with database in production
        self._sessions: dict[str, SharedSession] = {}
        self._user_sessions: dict[str, set[str]] = {}  # user_id -> session_ids

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
        """Create a new collaborative session."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Create host participant
        host_participant = SessionParticipant(
            user_id=host_user_id,
            username=host_username,
            role="host",
            joined_at=now,
            is_active=True,
            can_edit=True,
            can_invite=True,
            can_moderate=True,
        )

        session = SharedSession(
            id=session_id,
            organization_id=organization_id,
            session_type=session_type,
            title=title,
            description=description,
            project_id=project_id,
            file_path=file_path,
            pr_id=pr_id,
            host_user_id=host_user_id,
            participants=[host_participant],
            max_participants=max_participants,
            is_active=True,
            is_public=is_public,
            created_at=now,
            started_at=now,
        )

        self._sessions[session_id] = session

        # Track user's sessions
        if host_user_id not in self._user_sessions:
            self._user_sessions[host_user_id] = set()
        self._user_sessions[host_user_id].add(session_id)

        return session

    async def get_session(self, session_id: str) -> SharedSession | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    async def list_sessions(
        self,
        organization_id: str | None = None,
        session_type: SessionType | None = None,
        project_id: str | None = None,
        user_id: str | None = None,
        is_active: bool | None = True,
        is_public: bool | None = None,
    ) -> list[SharedSession]:
        """List sessions with optional filters."""
        sessions = []

        for session in self._sessions.values():
            # Filter by organization
            if organization_id and session.organization_id != organization_id:
                continue

            # Filter by type
            if session_type and session.session_type != session_type:
                continue

            # Filter by project
            if project_id and session.project_id != project_id:
                continue

            # Filter by active status
            if is_active is not None and session.is_active != is_active:
                continue

            # Filter by public status
            if is_public is not None and session.is_public != is_public:
                continue

            # Filter by user participation
            if user_id:
                participant_ids = [p.user_id for p in session.participants]
                if user_id not in participant_ids:
                    continue

            sessions.append(session)

        # Sort by created_at descending
        sessions.sort(key=lambda s: s.created_at, reverse=True)

        return sessions

    async def join_session(
        self,
        session_id: str,
        user_id: str,
        username: str,
        role: str = "participant",
        can_edit: bool = True,
    ) -> SharedSession | None:
        """Join an existing session."""
        session = self._sessions.get(session_id)
        if not session or not session.is_active:
            return None

        # Check if already a participant
        for participant in session.participants:
            if participant.user_id == user_id:
                # Rejoin - mark as active
                participant.is_active = True
                participant.left_at = None
                return session

        # Check max participants
        active_count = sum(1 for p in session.participants if p.is_active)
        if active_count >= session.max_participants:
            return None

        # Add new participant
        participant = SessionParticipant(
            user_id=user_id,
            username=username,
            role=role,
            joined_at=datetime.utcnow(),
            is_active=True,
            can_edit=can_edit,
            can_invite=role in ["host", "moderator"],
            can_moderate=role in ["host", "moderator"],
        )
        session.participants.append(participant)

        # Track user's sessions
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = set()
        self._user_sessions[user_id].add(session_id)

        return session

    async def leave_session(
        self,
        session_id: str,
        user_id: str,
    ) -> SharedSession | None:
        """Leave a session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        for participant in session.participants:
            if participant.user_id == user_id:
                participant.is_active = False
                participant.left_at = datetime.utcnow()
                break

        # Remove from user's sessions
        if user_id in self._user_sessions:
            self._user_sessions[user_id].discard(session_id)

        # Check if session should be ended (no active participants)
        active_count = sum(1 for p in session.participants if p.is_active)
        if active_count == 0:
            session.is_active = False
            session.ended_at = datetime.utcnow()

        return session

    async def end_session(
        self,
        session_id: str,
        ended_by: str,
    ) -> SharedSession | None:
        """End a session (host only)."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Verify host
        if session.host_user_id != ended_by:
            # Check if user is moderator
            is_moderator = False
            for p in session.participants:
                if p.user_id == ended_by and p.can_moderate:
                    is_moderator = True
                    break
            if not is_moderator:
                return None

        session.is_active = False
        session.ended_at = datetime.utcnow()

        # Mark all participants as left
        for participant in session.participants:
            if participant.is_active:
                participant.is_active = False
                participant.left_at = session.ended_at

        # Clean up user session tracking
        for participant in session.participants:
            if participant.user_id in self._user_sessions:
                self._user_sessions[participant.user_id].discard(session_id)

        return session

    async def update_participant_permissions(
        self,
        session_id: str,
        user_id: str,
        can_edit: bool | None = None,
        can_invite: bool | None = None,
        can_moderate: bool | None = None,
        role: str | None = None,
    ) -> SharedSession | None:
        """Update participant permissions."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        for participant in session.participants:
            if participant.user_id == user_id:
                if can_edit is not None:
                    participant.can_edit = can_edit
                if can_invite is not None:
                    participant.can_invite = can_invite
                if can_moderate is not None:
                    participant.can_moderate = can_moderate
                if role is not None:
                    participant.role = role
                break

        return session

    async def add_message(
        self,
        session_id: str,
        user_id: str,
        username: str,
        message: str,
        message_type: str = "text",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Add a message to the session."""
        session = self._sessions.get(session_id)
        if not session or not session.is_active:
            return None

        # Verify user is participant
        is_participant = any(
            p.user_id == user_id and p.is_active
            for p in session.participants
        )
        if not is_participant:
            return None

        message_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "username": username,
            "message": message,
            "type": message_type,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        session.messages.append(message_data)

        return message_data

    async def update_shared_state(
        self,
        session_id: str,
        user_id: str,
        key: str,
        value: Any,
    ) -> SharedSession | None:
        """Update shared state in a session."""
        session = self._sessions.get(session_id)
        if not session or not session.is_active:
            return None

        # Verify user can edit
        can_edit = any(
            p.user_id == user_id and p.is_active and p.can_edit
            for p in session.participants
        )
        if not can_edit:
            return None

        session.shared_state[key] = {
            "value": value,
            "updated_by": user_id,
            "updated_at": datetime.utcnow().isoformat(),
        }

        return session

    async def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = True,
    ) -> list[SharedSession]:
        """Get all sessions for a user."""
        session_ids = self._user_sessions.get(user_id, set())
        sessions = []

        for session_id in session_ids:
            session = self._sessions.get(session_id)
            if session:
                if active_only and not session.is_active:
                    continue
                sessions.append(session)

        return sessions

    async def get_active_participants(
        self,
        session_id: str,
    ) -> list[SessionParticipant]:
        """Get active participants in a session."""
        session = self._sessions.get(session_id)
        if not session:
            return []

        return [p for p in session.participants if p.is_active]

    async def transfer_host(
        self,
        session_id: str,
        current_host_id: str,
        new_host_id: str,
    ) -> SharedSession | None:
        """Transfer session host to another participant."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Verify current host
        if session.host_user_id != current_host_id:
            return None

        # Verify new host is active participant
        new_host_participant = None
        for p in session.participants:
            if p.user_id == new_host_id and p.is_active:
                new_host_participant = p
                break

        if not new_host_participant:
            return None

        # Update roles
        session.host_user_id = new_host_id
        new_host_participant.role = "host"
        new_host_participant.can_edit = True
        new_host_participant.can_invite = True
        new_host_participant.can_moderate = True

        # Demote old host to participant
        for p in session.participants:
            if p.user_id == current_host_id:
                p.role = "participant"
                break

        return session


# Singleton instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get the session manager singleton."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
