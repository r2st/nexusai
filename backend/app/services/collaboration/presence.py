"""Presence Service for Real-time Collaboration."""

from datetime import datetime, timedelta
from typing import Any

from app.services.collaboration.models import (
    PresenceStatus,
    UserPresence,
    CollaborationRoom,
)


class PresenceService:
    """Service for managing user presence and online status."""

    def __init__(self):
        # In-memory storage - replace with Redis in production
        self._presences: dict[str, UserPresence] = {}
        self._rooms: dict[str, CollaborationRoom] = {}
        self._user_rooms: dict[str, set[str]] = {}  # user_id -> room_ids

        # Configuration
        self._idle_timeout_minutes = 5
        self._offline_timeout_minutes = 15

    async def update_presence(
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
        """Update user presence information."""
        now = datetime.utcnow()

        if user_id in self._presences:
            presence = self._presences[user_id]
            presence.last_activity = now
            presence.last_seen = now

            if status is not None:
                presence.status = status
            if status_message is not None:
                presence.status_message = status_message
            if current_project_id is not None:
                presence.current_project_id = current_project_id
            if current_file_path is not None:
                presence.current_file_path = current_file_path
            if current_line is not None:
                presence.current_line = current_line
            if avatar_url is not None:
                presence.avatar_url = avatar_url

            presence.client_type = client_type
            if client_version:
                presence.client_version = client_version
        else:
            presence = UserPresence(
                user_id=user_id,
                username=username,
                avatar_url=avatar_url,
                status=status or PresenceStatus.ONLINE,
                status_message=status_message,
                current_project_id=current_project_id,
                current_file_path=current_file_path,
                current_line=current_line,
                last_seen=now,
                last_activity=now,
                session_started=now,
                client_type=client_type,
                client_version=client_version,
            )
            self._presences[user_id] = presence
            self._user_rooms[user_id] = set()

        return presence

    async def get_presence(self, user_id: str) -> UserPresence | None:
        """Get user presence by ID."""
        presence = self._presences.get(user_id)
        if presence:
            # Check if user should be marked as away or offline
            await self._check_presence_timeout(presence)
        return presence

    async def get_presences(
        self,
        user_ids: list[str] | None = None,
        project_id: str | None = None,
        status: PresenceStatus | None = None,
    ) -> list[UserPresence]:
        """Get multiple user presences with optional filters."""
        presences = []

        for user_id, presence in self._presences.items():
            # Filter by user IDs
            if user_ids and user_id not in user_ids:
                continue

            # Filter by project
            if project_id and presence.current_project_id != project_id:
                continue

            # Check timeouts
            await self._check_presence_timeout(presence)

            # Filter by status
            if status and presence.status != status:
                continue

            presences.append(presence)

        return presences

    async def set_offline(self, user_id: str) -> UserPresence | None:
        """Mark a user as offline."""
        presence = self._presences.get(user_id)
        if presence:
            presence.status = PresenceStatus.OFFLINE
            presence.last_seen = datetime.utcnow()

            # Leave all rooms
            await self._leave_all_rooms(user_id)

        return presence

    async def heartbeat(self, user_id: str) -> UserPresence | None:
        """Process a heartbeat to keep presence active."""
        presence = self._presences.get(user_id)
        if presence:
            presence.last_activity = datetime.utcnow()
            presence.last_seen = datetime.utcnow()

            # Restore online status if was away
            if presence.status == PresenceStatus.AWAY:
                presence.status = PresenceStatus.ONLINE

        return presence

    async def _check_presence_timeout(self, presence: UserPresence) -> None:
        """Check and update presence based on activity timeout."""
        now = datetime.utcnow()
        idle_threshold = now - timedelta(minutes=self._idle_timeout_minutes)
        offline_threshold = now - timedelta(minutes=self._offline_timeout_minutes)

        if presence.last_activity < offline_threshold:
            if presence.status != PresenceStatus.OFFLINE:
                presence.status = PresenceStatus.OFFLINE
                await self._leave_all_rooms(presence.user_id)
        elif presence.last_activity < idle_threshold:
            if presence.status == PresenceStatus.ONLINE:
                presence.status = PresenceStatus.AWAY

    # Room Management

    async def join_room(
        self,
        user_id: str,
        room_type: str,
        room_key: str,
    ) -> CollaborationRoom:
        """Join a collaboration room."""
        room_id = f"{room_type}:{room_key}"

        if room_id not in self._rooms:
            self._rooms[room_id] = CollaborationRoom(
                id=room_id,
                room_type=room_type,
                room_key=room_key,
                connected_users=[],
            )

        room = self._rooms[room_id]

        if user_id not in room.connected_users:
            room.connected_users.append(user_id)
            room.last_activity = datetime.utcnow()

        if user_id in self._user_rooms:
            self._user_rooms[user_id].add(room_id)
        else:
            self._user_rooms[user_id] = {room_id}

        return room

    async def leave_room(
        self,
        user_id: str,
        room_type: str,
        room_key: str,
    ) -> CollaborationRoom | None:
        """Leave a collaboration room."""
        room_id = f"{room_type}:{room_key}"

        room = self._rooms.get(room_id)
        if room and user_id in room.connected_users:
            room.connected_users.remove(user_id)
            room.last_activity = datetime.utcnow()

            if user_id in self._user_rooms:
                self._user_rooms[user_id].discard(room_id)

            # Clean up empty rooms
            if not room.connected_users:
                del self._rooms[room_id]
                return None

        return room

    async def _leave_all_rooms(self, user_id: str) -> None:
        """Leave all rooms for a user."""
        if user_id not in self._user_rooms:
            return

        room_ids = list(self._user_rooms[user_id])
        for room_id in room_ids:
            room = self._rooms.get(room_id)
            if room:
                if user_id in room.connected_users:
                    room.connected_users.remove(user_id)
                if not room.connected_users:
                    del self._rooms[room_id]

        self._user_rooms[user_id] = set()

    async def get_room(self, room_type: str, room_key: str) -> CollaborationRoom | None:
        """Get a collaboration room."""
        room_id = f"{room_type}:{room_key}"
        return self._rooms.get(room_id)

    async def get_room_members(
        self,
        room_type: str,
        room_key: str,
    ) -> list[UserPresence]:
        """Get all members in a room with their presence info."""
        room_id = f"{room_type}:{room_key}"
        room = self._rooms.get(room_id)

        if not room:
            return []

        members = []
        for user_id in room.connected_users:
            presence = self._presences.get(user_id)
            if presence:
                members.append(presence)

        return members

    async def get_users_in_file(
        self,
        project_id: str,
        file_path: str,
    ) -> list[UserPresence]:
        """Get all users currently viewing a specific file."""
        users = []
        for presence in self._presences.values():
            if (presence.current_project_id == project_id and
                presence.current_file_path == file_path and
                presence.status != PresenceStatus.OFFLINE):
                users.append(presence)
        return users

    async def get_active_users_count(self, project_id: str | None = None) -> int:
        """Get count of active users, optionally for a specific project."""
        count = 0
        for presence in self._presences.values():
            if presence.status != PresenceStatus.OFFLINE:
                if project_id is None or presence.current_project_id == project_id:
                    count += 1
        return count

    async def broadcast_to_room(
        self,
        room_type: str,
        room_key: str,
        event_type: str,
        data: dict[str, Any],
        exclude_user_id: str | None = None,
    ) -> list[str]:
        """
        Get list of user IDs to broadcast an event to.

        Note: Actual WebSocket broadcasting should be handled by the WebSocket manager.
        This returns the list of recipients.
        """
        room_id = f"{room_type}:{room_key}"
        room = self._rooms.get(room_id)

        if not room:
            return []

        recipients = [
            user_id for user_id in room.connected_users
            if user_id != exclude_user_id
        ]

        return recipients


# Singleton instance
_presence_service: PresenceService | None = None


def get_presence_service() -> PresenceService:
    """Get the presence service singleton."""
    global _presence_service
    if _presence_service is None:
        _presence_service = PresenceService()
    return _presence_service
