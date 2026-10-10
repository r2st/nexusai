"""Session Store - Redis-backed session management for scalability."""

import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from app.core.config import settings
from app.services.setup_chatbot.schemas import ChatMessage, SetupSession


class SessionStore(ABC):
    """Abstract session store interface."""

    @abstractmethod
    async def get(self, session_id: str) -> SetupSession | None:
        """Get a session by ID."""
        pass

    @abstractmethod
    async def save(self, session: SetupSession) -> None:
        """Save a session."""
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """Delete a session."""
        pass

    @abstractmethod
    async def list_by_user(
        self, user_id: str, tenant_id: str, limit: int = 10
    ) -> list[SetupSession]:
        """List sessions for a user."""
        pass

    @abstractmethod
    async def cleanup_expired(self, max_age_hours: int = 24) -> int:
        """Clean up expired sessions."""
        pass


class InMemorySessionStore(SessionStore):
    """In-memory session store for development/testing."""

    def __init__(self):
        self._sessions: dict[str, SetupSession] = {}

    async def get(self, session_id: str) -> SetupSession | None:
        return self._sessions.get(session_id)

    async def save(self, session: SetupSession) -> None:
        session.updated_at = datetime.utcnow()
        self._sessions[session.id] = session

    async def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    async def list_by_user(
        self, user_id: str, tenant_id: str, limit: int = 10
    ) -> list[SetupSession]:
        sessions = [
            s for s in self._sessions.values()
            if s.user_id == user_id and s.tenant_id == tenant_id
        ]
        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)[:limit]

    async def cleanup_expired(self, max_age_hours: int = 24) -> int:
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired = [
            sid for sid, session in self._sessions.items()
            if session.updated_at < cutoff
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)


class RedisSessionStore(SessionStore):
    """Redis-backed session store for production scalability."""

    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        self._redis = None
        self._prefix = "setup_session:"
        self._user_index_prefix = "setup_sessions_user:"
        self._ttl = 86400  # 24 hours

    async def _get_redis(self):
        """Get or create Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
            except ImportError:
                raise RuntimeError("redis package required for RedisSessionStore")
        return self._redis

    def _serialize_session(self, session: SetupSession) -> str:
        """Serialize session to JSON."""
        data = session.model_dump()
        # Convert datetime objects to ISO strings
        for key in ['started_at', 'updated_at', 'completed_at']:
            if data.get(key):
                data[key] = data[key].isoformat() if isinstance(data[key], datetime) else data[key]

        # Serialize messages
        for msg in data.get('messages', []):
            if msg.get('timestamp'):
                msg['timestamp'] = msg['timestamp'].isoformat() if isinstance(msg['timestamp'], datetime) else msg['timestamp']

        return json.dumps(data)

    def _deserialize_session(self, data: str) -> SetupSession:
        """Deserialize session from JSON."""
        parsed = json.loads(data)

        # Parse datetime objects
        for key in ['started_at', 'updated_at', 'completed_at']:
            if parsed.get(key):
                parsed[key] = datetime.fromisoformat(parsed[key])

        # Parse message timestamps
        messages = []
        for msg_data in parsed.get('messages', []):
            if msg_data.get('timestamp'):
                msg_data['timestamp'] = datetime.fromisoformat(msg_data['timestamp'])
            messages.append(ChatMessage(**msg_data))
        parsed['messages'] = messages

        return SetupSession(**parsed)

    async def get(self, session_id: str) -> SetupSession | None:
        redis = await self._get_redis()
        data = await redis.get(f"{self._prefix}{session_id}")
        if data:
            return self._deserialize_session(data)
        return None

    async def save(self, session: SetupSession) -> None:
        redis = await self._get_redis()
        session.updated_at = datetime.utcnow()

        # Save session
        key = f"{self._prefix}{session.id}"
        await redis.setex(key, self._ttl, self._serialize_session(session))

        # Update user index
        user_key = f"{self._user_index_prefix}{session.tenant_id}:{session.user_id}"
        await redis.zadd(user_key, {session.id: session.updated_at.timestamp()})
        await redis.expire(user_key, self._ttl)

    async def delete(self, session_id: str) -> bool:
        redis = await self._get_redis()

        # Get session to find user info
        session = await self.get(session_id)
        if session:
            # Remove from user index
            user_key = f"{self._user_index_prefix}{session.tenant_id}:{session.user_id}"
            await redis.zrem(user_key, session_id)

        # Delete session
        result = await redis.delete(f"{self._prefix}{session_id}")
        return result > 0

    async def list_by_user(
        self, user_id: str, tenant_id: str, limit: int = 10
    ) -> list[SetupSession]:
        redis = await self._get_redis()
        user_key = f"{self._user_index_prefix}{tenant_id}:{user_id}"

        # Get session IDs from sorted set (most recent first)
        session_ids = await redis.zrevrange(user_key, 0, limit - 1)

        sessions = []
        for sid in session_ids:
            session = await self.get(sid)
            if session:
                sessions.append(session)

        return sessions

    async def cleanup_expired(self, max_age_hours: int = 24) -> int:
        """Clean up expired sessions (Redis handles TTL automatically)."""
        # Redis handles expiration automatically via TTL
        # This method is here for interface consistency
        return 0

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None


def get_session_store() -> SessionStore:
    """Get the appropriate session store based on configuration."""
    redis_url = getattr(settings, 'REDIS_URL', None)

    if redis_url:
        try:
            return RedisSessionStore(redis_url)
        except Exception:
            # Fall back to in-memory if Redis is not available
            pass

    return InMemorySessionStore()


# Singleton instance
_session_store: SessionStore | None = None


async def get_or_create_session_store() -> SessionStore:
    """Get or create the session store singleton."""
    global _session_store
    if _session_store is None:
        _session_store = get_session_store()
    return _session_store
