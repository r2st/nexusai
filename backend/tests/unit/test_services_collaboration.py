"""
Unit tests for collaboration services.
"""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# =============================================================================
# Mock Models and Types
# =============================================================================


class PresenceStatus:
    """Presence status types."""
    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"


class SessionType:
    """Session types."""
    CODE_REVIEW = "code_review"
    PAIR_PROGRAMMING = "pair_programming"
    DEBUGGING = "debugging"
    DISCUSSION = "discussion"


class AnnotationType:
    """Annotation types."""
    COMMENT = "comment"
    SUGGESTION = "suggestion"
    QUESTION = "question"
    TODO = "todo"
    BUG = "bug"


class ActivityType:
    """Activity types."""
    SESSION_STARTED = "session_started"
    SESSION_JOINED = "session_joined"
    ANNOTATION_CREATED = "annotation_created"
    ANNOTATION_RESOLVED = "annotation_resolved"
    MENTION = "mention"
    FILE_OPENED = "file_opened"
    COMMIT = "commit"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_presence_service():
    """Create a mock presence service."""
    service = AsyncMock()
    service.update_presence = AsyncMock()
    service.get_presence = AsyncMock()
    service.get_presences = AsyncMock()
    service.set_offline = AsyncMock()
    service.heartbeat = AsyncMock()
    service.get_users_in_file = AsyncMock()
    service.join_room = AsyncMock()
    service.leave_room = AsyncMock()
    service.get_room_members = AsyncMock()
    service.broadcast_to_room = AsyncMock()
    return service


@pytest.fixture
def mock_session_manager():
    """Create a mock session manager."""
    manager = AsyncMock()
    manager.create_session = AsyncMock()
    manager.get_session = AsyncMock()
    manager.list_sessions = AsyncMock()
    manager.join_session = AsyncMock()
    manager.leave_session = AsyncMock()
    manager.end_session = AsyncMock()
    manager.add_message = AsyncMock()
    return manager


@pytest.fixture
def mock_annotation_service():
    """Create a mock annotation service."""
    service = AsyncMock()
    service.create_annotation = AsyncMock()
    service.get_annotation = AsyncMock()
    service.list_annotations = AsyncMock()
    service.resolve_annotation = AsyncMock()
    service.get_user_mentions = AsyncMock()
    service.get_annotation_summary = AsyncMock()
    return service


@pytest.fixture
def mock_activity_feed():
    """Create a mock activity feed."""
    feed = AsyncMock()
    feed.record_event = AsyncMock()
    feed.record_session_started = AsyncMock()
    feed.record_annotation_created = AsyncMock()
    feed.get_organization_feed = AsyncMock()
    feed.get_project_feed = AsyncMock()
    feed.get_user_feed = AsyncMock()
    feed.get_activity_summary = AsyncMock()
    return feed


@pytest.fixture
def sample_user_presence():
    """Create a sample user presence."""
    return MagicMock(
        user_id=str(uuid4()),
        username="testuser",
        status=PresenceStatus.ONLINE,
        status_message="Working on feature",
        current_project_id=str(uuid4()),
        current_file_path="src/main.py",
        current_line=42,
        client_type="web",
        client_version="1.0.0",
        avatar_url="https://example.com/avatar.png",
        last_seen=datetime.now(UTC),
    )


@pytest.fixture
def sample_session():
    """Create a sample shared session."""
    return MagicMock(
        id=str(uuid4()),
        organization_id=str(uuid4()),
        session_type=MagicMock(value="code_review"),
        title="Review PR #123",
        description="Code review for authentication feature",
        host_user_id=str(uuid4()),
        host_username="host_user",
        project_id=str(uuid4()),
        file_path="src/auth.py",
        pr_id="123",
        is_public=False,
        max_participants=10,
        is_active=True,
        participants=[
            MagicMock(user_id=str(uuid4()), username="user1", is_active=True),
            MagicMock(user_id=str(uuid4()), username="user2", is_active=True),
        ],
        created_at=datetime.now(UTC),
        ended_at=None,
    )


@pytest.fixture
def sample_annotation():
    """Create a sample code annotation."""
    return MagicMock(
        id=str(uuid4()),
        organization_id=str(uuid4()),
        project_id=str(uuid4()),
        file_path="src/main.py",
        start_line=10,
        end_line=15,
        annotation_type=MagicMock(value="comment"),
        title="Consider refactoring",
        content="This function could be simplified.",
        author_id=str(uuid4()),
        author_username="reviewer",
        mentions=[],
        commit_sha="abc123",
        branch="main",
        parent_id=None,
        resolved=False,
        resolved_by=None,
        resolved_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_activity_event():
    """Create a sample activity event."""
    return MagicMock(
        id=str(uuid4()),
        organization_id=str(uuid4()),
        project_id=str(uuid4()),
        activity_type=MagicMock(value="session_started"),
        title="Started code review session",
        description="Review PR #123",
        actor_id=str(uuid4()),
        actor_username="reviewer",
        target_type="session",
        target_id=str(uuid4()),
        metadata={},
        is_public=True,
        visible_to_user_ids=None,
        created_at=datetime.now(UTC),
    )


# =============================================================================
# UserPresence Model Tests
# =============================================================================


class TestUserPresenceModel:
    """Tests for UserPresence model."""

    def test_presence_status_values(self):
        """Test presence status enumeration values."""
        assert PresenceStatus.ONLINE == "online"
        assert PresenceStatus.AWAY == "away"
        assert PresenceStatus.BUSY == "busy"
        assert PresenceStatus.OFFLINE == "offline"

    def test_user_presence_creation(self, sample_user_presence):
        """Test creating a user presence object."""
        assert sample_user_presence.user_id is not None
        assert sample_user_presence.username == "testuser"
        assert sample_user_presence.status == PresenceStatus.ONLINE
        assert sample_user_presence.current_file_path == "src/main.py"
        assert sample_user_presence.current_line == 42

    def test_user_presence_with_optional_fields(self):
        """Test user presence with optional fields."""
        presence = MagicMock(
            user_id=str(uuid4()),
            username="user",
            status=PresenceStatus.ONLINE,
            status_message=None,
            current_project_id=None,
            current_file_path=None,
            current_line=None,
        )
        assert presence.status_message is None
        assert presence.current_project_id is None


# =============================================================================
# SharedSession Model Tests
# =============================================================================


class TestSharedSessionModel:
    """Tests for SharedSession model."""

    def test_session_type_values(self):
        """Test session type enumeration values."""
        assert SessionType.CODE_REVIEW == "code_review"
        assert SessionType.PAIR_PROGRAMMING == "pair_programming"
        assert SessionType.DEBUGGING == "debugging"
        assert SessionType.DISCUSSION == "discussion"

    def test_shared_session_creation(self, sample_session):
        """Test creating a shared session."""
        assert sample_session.id is not None
        assert sample_session.title == "Review PR #123"
        assert sample_session.is_active is True
        assert len(sample_session.participants) == 2

    def test_session_participants_count(self, sample_session):
        """Test counting active session participants."""
        active_count = len([p for p in sample_session.participants if p.is_active])
        assert active_count == 2


# =============================================================================
# CodeAnnotation Model Tests
# =============================================================================


class TestCodeAnnotationModel:
    """Tests for CodeAnnotation model."""

    def test_annotation_type_values(self):
        """Test annotation type enumeration values."""
        assert AnnotationType.COMMENT == "comment"
        assert AnnotationType.SUGGESTION == "suggestion"
        assert AnnotationType.QUESTION == "question"
        assert AnnotationType.TODO == "todo"
        assert AnnotationType.BUG == "bug"

    def test_code_annotation_creation(self, sample_annotation):
        """Test creating a code annotation."""
        assert sample_annotation.id is not None
        assert sample_annotation.file_path == "src/main.py"
        assert sample_annotation.start_line == 10
        assert sample_annotation.end_line == 15
        assert sample_annotation.resolved is False

    def test_annotation_line_range(self, sample_annotation):
        """Test annotation spans multiple lines."""
        line_count = sample_annotation.end_line - sample_annotation.start_line + 1
        assert line_count == 6


# =============================================================================
# ActivityEvent Model Tests
# =============================================================================


class TestActivityEventModel:
    """Tests for ActivityEvent model."""

    def test_activity_type_values(self):
        """Test activity type enumeration values."""
        assert ActivityType.SESSION_STARTED == "session_started"
        assert ActivityType.SESSION_JOINED == "session_joined"
        assert ActivityType.ANNOTATION_CREATED == "annotation_created"
        assert ActivityType.ANNOTATION_RESOLVED == "annotation_resolved"
        assert ActivityType.MENTION == "mention"

    def test_activity_event_creation(self, sample_activity_event):
        """Test creating an activity event."""
        assert sample_activity_event.id is not None
        assert sample_activity_event.title == "Started code review session"
        assert sample_activity_event.is_public is True


# =============================================================================
# PresenceService Tests
# =============================================================================


class TestPresenceService:
    """Tests for PresenceService class."""

    @pytest.mark.asyncio
    async def test_update_presence(self, mock_presence_service, sample_user_presence):
        """Test updating user presence."""
        mock_presence_service.update_presence.return_value = sample_user_presence

        result = await mock_presence_service.update_presence(
            user_id=sample_user_presence.user_id,
            username="testuser",
            status=PresenceStatus.ONLINE,
            current_file_path="src/main.py",
        )

        assert result == sample_user_presence
        mock_presence_service.update_presence.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_presence(self, mock_presence_service, sample_user_presence):
        """Test getting user presence."""
        mock_presence_service.get_presence.return_value = sample_user_presence

        result = await mock_presence_service.get_presence(sample_user_presence.user_id)

        assert result == sample_user_presence

    @pytest.mark.asyncio
    async def test_get_presence_not_found(self, mock_presence_service):
        """Test getting presence for non-existent user."""
        mock_presence_service.get_presence.return_value = None

        result = await mock_presence_service.get_presence("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_team_presences(self, mock_presence_service, sample_user_presence):
        """Test getting presence for multiple users."""
        presences = [sample_user_presence]
        mock_presence_service.get_presences.return_value = presences

        result = await mock_presence_service.get_presences(
            user_ids=[sample_user_presence.user_id],
            project_id=sample_user_presence.current_project_id,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_set_user_offline(self, mock_presence_service, sample_user_presence):
        """Test setting user as offline."""
        offline_presence = MagicMock(
            **{**sample_user_presence.__dict__, "status": PresenceStatus.OFFLINE}
        )
        mock_presence_service.set_offline.return_value = offline_presence

        result = await mock_presence_service.set_offline(sample_user_presence.user_id)

        assert result.status == PresenceStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_heartbeat(self, mock_presence_service, sample_user_presence):
        """Test processing heartbeat."""
        mock_presence_service.heartbeat.return_value = sample_user_presence

        result = await mock_presence_service.heartbeat(sample_user_presence.user_id)

        assert result == sample_user_presence

    @pytest.mark.asyncio
    async def test_get_users_in_file(self, mock_presence_service, sample_user_presence):
        """Test getting users viewing a file."""
        mock_presence_service.get_users_in_file.return_value = [sample_user_presence]

        result = await mock_presence_service.get_users_in_file(
            project_id=sample_user_presence.current_project_id,
            file_path="src/main.py",
        )

        assert len(result) == 1
        assert result[0].current_file_path == "src/main.py"


# =============================================================================
# SessionManager Tests
# =============================================================================


class TestSessionManager:
    """Tests for SessionManager class."""

    @pytest.mark.asyncio
    async def test_create_session(self, mock_session_manager, sample_session):
        """Test creating a new session."""
        mock_session_manager.create_session.return_value = sample_session

        result = await mock_session_manager.create_session(
            organization_id=sample_session.organization_id,
            session_type=SessionType.CODE_REVIEW,
            title="Review PR #123",
            host_user_id=sample_session.host_user_id,
            host_username="host_user",
        )

        assert result.title == "Review PR #123"

    @pytest.mark.asyncio
    async def test_get_session(self, mock_session_manager, sample_session):
        """Test getting a session by ID."""
        mock_session_manager.get_session.return_value = sample_session

        result = await mock_session_manager.get_session(sample_session.id)

        assert result == sample_session

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, mock_session_manager):
        """Test getting non-existent session."""
        mock_session_manager.get_session.return_value = None

        result = await mock_session_manager.get_session("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_sessions(self, mock_session_manager, sample_session):
        """Test listing sessions with filters."""
        mock_session_manager.list_sessions.return_value = [sample_session]

        result = await mock_session_manager.list_sessions(
            organization_id=sample_session.organization_id,
            is_active=True,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_sessions_by_type(self, mock_session_manager, sample_session):
        """Test listing sessions filtered by type."""
        mock_session_manager.list_sessions.return_value = [sample_session]

        result = await mock_session_manager.list_sessions(
            session_type=SessionType.CODE_REVIEW,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_join_session(self, mock_session_manager, sample_session):
        """Test joining a session."""
        mock_session_manager.join_session.return_value = sample_session

        result = await mock_session_manager.join_session(
            session_id=sample_session.id,
            user_id=str(uuid4()),
            username="newuser",
            role="participant",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_join_session_full(self, mock_session_manager):
        """Test joining a full session."""
        mock_session_manager.join_session.return_value = None

        result = await mock_session_manager.join_session(
            session_id=str(uuid4()),
            user_id=str(uuid4()),
            username="newuser",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_leave_session(self, mock_session_manager, sample_session):
        """Test leaving a session."""
        mock_session_manager.leave_session.return_value = sample_session

        result = await mock_session_manager.leave_session(
            session_id=sample_session.id,
            user_id=sample_session.participants[0].user_id,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_end_session(self, mock_session_manager, sample_session):
        """Test ending a session."""
        ended_session = MagicMock(**{**sample_session.__dict__})
        ended_session.is_active = False
        ended_session.ended_at = datetime.now(UTC)
        mock_session_manager.end_session.return_value = ended_session

        result = await mock_session_manager.end_session(
            session_id=sample_session.id,
            ended_by=sample_session.host_user_id,
        )

        assert result.is_active is False
        assert result.ended_at is not None

    @pytest.mark.asyncio
    async def test_add_message(self, mock_session_manager, sample_session):
        """Test adding a message to session."""
        message = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "username": "sender",
            "message": "Hello!",
            "message_type": "text",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        mock_session_manager.add_message.return_value = message

        result = await mock_session_manager.add_message(
            session_id=sample_session.id,
            user_id=message["user_id"],
            username="sender",
            message="Hello!",
        )

        assert result["message"] == "Hello!"


# =============================================================================
# AnnotationService Tests
# =============================================================================


class TestAnnotationService:
    """Tests for AnnotationService class."""

    @pytest.mark.asyncio
    async def test_create_annotation(self, mock_annotation_service, sample_annotation):
        """Test creating an annotation."""
        mock_annotation_service.create_annotation.return_value = sample_annotation

        result = await mock_annotation_service.create_annotation(
            organization_id=sample_annotation.organization_id,
            project_id=sample_annotation.project_id,
            file_path="src/main.py",
            start_line=10,
            end_line=15,
            annotation_type=AnnotationType.COMMENT,
            content="This function could be simplified.",
            author_id=sample_annotation.author_id,
            author_username="reviewer",
        )

        assert result.file_path == "src/main.py"
        assert result.start_line == 10

    @pytest.mark.asyncio
    async def test_create_annotation_with_mentions(self, mock_annotation_service, sample_annotation):
        """Test creating an annotation with mentions."""
        mentioned_user_id = str(uuid4())
        annotation_with_mentions = MagicMock(**{**sample_annotation.__dict__})
        annotation_with_mentions.mentions = [mentioned_user_id]
        mock_annotation_service.create_annotation.return_value = annotation_with_mentions

        result = await mock_annotation_service.create_annotation(
            organization_id=sample_annotation.organization_id,
            project_id=sample_annotation.project_id,
            file_path="src/main.py",
            start_line=10,
            end_line=15,
            annotation_type=AnnotationType.COMMENT,
            content="@user please review this",
            author_id=sample_annotation.author_id,
            author_username="reviewer",
            mentions=[mentioned_user_id],
        )

        assert mentioned_user_id in result.mentions

    @pytest.mark.asyncio
    async def test_create_reply_annotation(self, mock_annotation_service, sample_annotation):
        """Test creating a reply to an annotation."""
        parent_id = str(uuid4())
        reply = MagicMock(**{**sample_annotation.__dict__})
        reply.parent_id = parent_id
        mock_annotation_service.create_annotation.return_value = reply

        result = await mock_annotation_service.create_annotation(
            organization_id=sample_annotation.organization_id,
            project_id=sample_annotation.project_id,
            file_path="src/main.py",
            start_line=10,
            end_line=15,
            annotation_type=AnnotationType.COMMENT,
            content="I agree with this.",
            author_id=sample_annotation.author_id,
            author_username="reviewer",
            parent_id=parent_id,
        )

        assert result.parent_id == parent_id

    @pytest.mark.asyncio
    async def test_get_annotation(self, mock_annotation_service, sample_annotation):
        """Test getting an annotation by ID."""
        mock_annotation_service.get_annotation.return_value = sample_annotation

        result = await mock_annotation_service.get_annotation(sample_annotation.id)

        assert result == sample_annotation

    @pytest.mark.asyncio
    async def test_list_annotations(self, mock_annotation_service, sample_annotation):
        """Test listing annotations with filters."""
        mock_annotation_service.list_annotations.return_value = [sample_annotation]

        result = await mock_annotation_service.list_annotations(
            organization_id=sample_annotation.organization_id,
            project_id=sample_annotation.project_id,
            file_path="src/main.py",
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_unresolved_annotations(self, mock_annotation_service, sample_annotation):
        """Test listing unresolved annotations."""
        mock_annotation_service.list_annotations.return_value = [sample_annotation]

        result = await mock_annotation_service.list_annotations(
            organization_id=sample_annotation.organization_id,
            resolved=False,
        )

        assert len(result) == 1
        assert result[0].resolved is False

    @pytest.mark.asyncio
    async def test_resolve_annotation(self, mock_annotation_service, sample_annotation):
        """Test resolving an annotation."""
        resolved_annotation = MagicMock(**{**sample_annotation.__dict__})
        resolved_annotation.resolved = True
        resolved_annotation.resolved_by = str(uuid4())
        resolved_annotation.resolved_at = datetime.now(UTC)
        mock_annotation_service.resolve_annotation.return_value = resolved_annotation

        result = await mock_annotation_service.resolve_annotation(
            annotation_id=sample_annotation.id,
            resolved_by=resolved_annotation.resolved_by,
        )

        assert result.resolved is True
        assert result.resolved_at is not None

    @pytest.mark.asyncio
    async def test_get_user_mentions(self, mock_annotation_service, sample_annotation):
        """Test getting annotations mentioning a user."""
        mock_annotation_service.get_user_mentions.return_value = [sample_annotation]

        result = await mock_annotation_service.get_user_mentions(
            user_id=str(uuid4()),
            unresolved_only=True,
        )

        assert len(result) == 1


# =============================================================================
# ActivityFeed Tests
# =============================================================================


class TestActivityFeed:
    """Tests for ActivityFeed class."""

    @pytest.mark.asyncio
    async def test_record_event(self, mock_activity_feed, sample_activity_event):
        """Test recording an activity event."""
        mock_activity_feed.record_event.return_value = sample_activity_event

        result = await mock_activity_feed.record_event(
            organization_id=sample_activity_event.organization_id,
            project_id=sample_activity_event.project_id,
            activity_type=ActivityType.SESSION_STARTED,
            title="Started code review session",
            actor_id=sample_activity_event.actor_id,
            actor_username="reviewer",
        )

        mock_activity_feed.record_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_session_started(self, mock_activity_feed):
        """Test recording session started activity."""
        await mock_activity_feed.record_session_started(
            organization_id=str(uuid4()),
            project_id=str(uuid4()),
            actor_id=str(uuid4()),
            actor_username="host",
            session_id=str(uuid4()),
            session_type="code_review",
            session_title="Review PR #123",
        )

        mock_activity_feed.record_session_started.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_annotation_created(self, mock_activity_feed):
        """Test recording annotation created activity."""
        await mock_activity_feed.record_annotation_created(
            organization_id=str(uuid4()),
            project_id=str(uuid4()),
            actor_id=str(uuid4()),
            actor_username="reviewer",
            annotation_id=str(uuid4()),
            annotation_type="comment",
            file_path="src/main.py",
            line=10,
            content_preview="This could be improved...",
        )

        mock_activity_feed.record_annotation_created.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_organization_feed(self, mock_activity_feed, sample_activity_event):
        """Test getting organization activity feed."""
        mock_activity_feed.get_organization_feed.return_value = [sample_activity_event]

        result = await mock_activity_feed.get_organization_feed(
            organization_id=sample_activity_event.organization_id,
            limit=50,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_project_feed(self, mock_activity_feed, sample_activity_event):
        """Test getting project activity feed."""
        mock_activity_feed.get_project_feed.return_value = [sample_activity_event]

        result = await mock_activity_feed.get_project_feed(
            project_id=sample_activity_event.project_id,
            limit=50,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_user_feed(self, mock_activity_feed, sample_activity_event):
        """Test getting user activity feed."""
        mock_activity_feed.get_user_feed.return_value = [sample_activity_event]

        result = await mock_activity_feed.get_user_feed(
            user_id=sample_activity_event.actor_id,
            limit=50,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_activity_summary(self, mock_activity_feed):
        """Test getting activity summary."""
        summary = {
            "total_events": 150,
            "events_by_type": {
                "session_started": 20,
                "annotation_created": 80,
                "commit": 50,
            },
            "active_users": 15,
            "period_days": 7,
        }
        mock_activity_feed.get_activity_summary.return_value = summary

        result = await mock_activity_feed.get_activity_summary(
            organization_id=str(uuid4()),
            days=7,
        )

        assert result["total_events"] == 150
        assert result["period_days"] == 7


# =============================================================================
# CollaborationService Integration Tests
# =============================================================================


class TestCollaborationService:
    """Tests for CollaborationService unified class."""

    @pytest.mark.asyncio
    async def test_update_user_presence_integration(
        self, mock_presence_service, sample_user_presence
    ):
        """Test updating user presence through unified service."""
        mock_presence_service.update_presence.return_value = sample_user_presence

        # Simulate unified service call
        result = await mock_presence_service.update_presence(
            user_id=sample_user_presence.user_id,
            username="testuser",
            status=PresenceStatus.ONLINE,
            current_file_path="src/main.py",
        )

        assert result.username == "testuser"

    @pytest.mark.asyncio
    async def test_create_session_with_activity(
        self, mock_session_manager, mock_activity_feed, sample_session
    ):
        """Test creating session records activity."""
        mock_session_manager.create_session.return_value = sample_session

        # Create session
        session = await mock_session_manager.create_session(
            organization_id=sample_session.organization_id,
            session_type=SessionType.CODE_REVIEW,
            title="Review PR #123",
            host_user_id=sample_session.host_user_id,
            host_username="host",
        )

        # Record activity
        await mock_activity_feed.record_session_started(
            organization_id=session.organization_id,
            project_id=session.project_id,
            actor_id=session.host_user_id,
            actor_username="host",
            session_id=session.id,
            session_type="code_review",
            session_title="Review PR #123",
        )

        mock_activity_feed.record_session_started.assert_called_once()

    @pytest.mark.asyncio
    async def test_join_session_with_activity(
        self, mock_session_manager, mock_activity_feed, sample_session
    ):
        """Test joining session records activity."""
        mock_session_manager.join_session.return_value = sample_session
        user_id = str(uuid4())

        session = await mock_session_manager.join_session(
            session_id=sample_session.id,
            user_id=user_id,
            username="joiner",
        )

        if session:
            await mock_activity_feed.record_event(
                organization_id=session.organization_id,
                project_id=session.project_id,
                activity_type=ActivityType.SESSION_JOINED,
                title=f"Joined session: {session.title}",
                actor_id=user_id,
                actor_username="joiner",
                target_type="session",
                target_id=sample_session.id,
            )

        mock_activity_feed.record_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_annotation_with_activity(
        self, mock_annotation_service, mock_activity_feed, sample_annotation
    ):
        """Test creating annotation records activity."""
        mock_annotation_service.create_annotation.return_value = sample_annotation

        annotation = await mock_annotation_service.create_annotation(
            organization_id=sample_annotation.organization_id,
            project_id=sample_annotation.project_id,
            file_path="src/main.py",
            start_line=10,
            end_line=15,
            annotation_type=AnnotationType.COMMENT,
            content="This could be improved.",
            author_id=sample_annotation.author_id,
            author_username="reviewer",
        )

        # Record activity (only for top-level annotations)
        if not annotation.parent_id:
            await mock_activity_feed.record_annotation_created(
                organization_id=annotation.organization_id,
                project_id=annotation.project_id,
                actor_id=annotation.author_id,
                actor_username="reviewer",
                annotation_id=annotation.id,
                annotation_type="comment",
                file_path="src/main.py",
                line=10,
                content_preview="This could be improved.",
            )

        mock_activity_feed.record_annotation_created.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_annotation_with_mentions_activity(
        self, mock_annotation_service, mock_activity_feed, sample_annotation
    ):
        """Test creating annotation with mentions records mention events."""
        mentioned_user_id = str(uuid4())
        annotation_with_mentions = MagicMock(**{**sample_annotation.__dict__})
        annotation_with_mentions.mentions = [mentioned_user_id]
        mock_annotation_service.create_annotation.return_value = annotation_with_mentions

        annotation = await mock_annotation_service.create_annotation(
            organization_id=sample_annotation.organization_id,
            project_id=sample_annotation.project_id,
            file_path="src/main.py",
            start_line=10,
            end_line=15,
            annotation_type=AnnotationType.COMMENT,
            content="@user please review",
            author_id=sample_annotation.author_id,
            author_username="reviewer",
            mentions=[mentioned_user_id],
        )

        # Record mention events
        for mentioned_id in annotation.mentions:
            await mock_activity_feed.record_event(
                organization_id=annotation.organization_id,
                project_id=annotation.project_id,
                activity_type=ActivityType.MENTION,
                title=f"Mentioned by reviewer",
                description="@user please review",
                actor_id=annotation.author_id,
                actor_username="reviewer",
                target_type="annotation",
                target_id=annotation.id,
                is_public=False,
                visible_to_user_ids=[mentioned_id],
            )

        assert mock_activity_feed.record_event.call_count == 1

    @pytest.mark.asyncio
    async def test_resolve_annotation_with_activity(
        self, mock_annotation_service, mock_activity_feed, sample_annotation
    ):
        """Test resolving annotation records activity."""
        resolved_annotation = MagicMock(**{**sample_annotation.__dict__})
        resolved_annotation.resolved = True
        resolved_by = str(uuid4())
        mock_annotation_service.resolve_annotation.return_value = resolved_annotation

        annotation = await mock_annotation_service.resolve_annotation(
            annotation_id=sample_annotation.id,
            resolved_by=resolved_by,
        )

        if annotation:
            await mock_activity_feed.record_event(
                organization_id=annotation.organization_id,
                project_id=annotation.project_id,
                activity_type=ActivityType.ANNOTATION_RESOLVED,
                title=f"Resolved annotation on {annotation.file_path}:{annotation.start_line}",
                actor_id=resolved_by,
                actor_username="resolver",
                target_type="annotation",
                target_id=sample_annotation.id,
            )

        mock_activity_feed.record_event.assert_called_once()


# =============================================================================
# Collaboration Room Tests
# =============================================================================


class TestCollaborationRooms:
    """Tests for collaboration room management."""

    @pytest.mark.asyncio
    async def test_join_room(self, mock_presence_service):
        """Test joining a collaboration room."""
        room = MagicMock(
            room_type="project",
            room_key="project-123",
            members=[str(uuid4())],
        )
        mock_presence_service.join_room.return_value = room

        result = await mock_presence_service.join_room(
            user_id=str(uuid4()),
            room_type="project",
            room_key="project-123",
        )

        assert result.room_type == "project"

    @pytest.mark.asyncio
    async def test_leave_room(self, mock_presence_service):
        """Test leaving a collaboration room."""
        room = MagicMock(
            room_type="file",
            room_key="file-src/main.py",
            members=[],
        )
        mock_presence_service.leave_room.return_value = room

        result = await mock_presence_service.leave_room(
            user_id=str(uuid4()),
            room_type="file",
            room_key="file-src/main.py",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_room_members(self, mock_presence_service, sample_user_presence):
        """Test getting room members."""
        mock_presence_service.get_room_members.return_value = [sample_user_presence]

        result = await mock_presence_service.get_room_members(
            room_type="session",
            room_key="session-abc123",
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_broadcast_to_room(self, mock_presence_service):
        """Test getting broadcast recipients."""
        user_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        mock_presence_service.broadcast_to_room.return_value = user_ids

        result = await mock_presence_service.broadcast_to_room(
            room_type="project",
            room_key="project-123",
            event_type="presence_update",
            data={"user": "test"},
            exclude_user_id=user_ids[0],
        )

        # Returns all users except excluded
        assert len(result) == 3


# =============================================================================
# Collaboration Dashboard Tests
# =============================================================================


class TestCollaborationDashboard:
    """Tests for collaboration dashboard."""

    @pytest.mark.asyncio
    async def test_get_dashboard_data(
        self,
        mock_presence_service,
        mock_session_manager,
        mock_annotation_service,
        mock_activity_feed,
        sample_user_presence,
        sample_session,
    ):
        """Test getting collaboration dashboard data."""
        org_id = str(uuid4())

        # Mock presence data
        online_presences = [sample_user_presence]
        mock_presence_service.get_presences.return_value = online_presences

        # Mock session data
        mock_session_manager.list_sessions.return_value = [sample_session]

        # Mock annotation summary
        annotation_summary = {
            "total": 50,
            "unresolved": 20,
            "by_type": {"comment": 30, "suggestion": 15, "bug": 5},
        }
        mock_annotation_service.get_annotation_summary.return_value = annotation_summary

        # Mock activity summary
        activity_summary = {
            "total_events": 150,
            "active_users": 15,
        }
        mock_activity_feed.get_activity_summary.return_value = activity_summary

        # Fetch dashboard components
        presences = await mock_presence_service.get_presences(project_id=None)
        sessions = await mock_session_manager.list_sessions(
            organization_id=org_id, is_active=True
        )
        annotations = await mock_annotation_service.get_annotation_summary(
            organization_id=org_id
        )
        activity = await mock_activity_feed.get_activity_summary(organization_id=org_id)

        # Build dashboard
        online_users = [p for p in presences if p.status != PresenceStatus.OFFLINE]
        dashboard = {
            "online_users": len(online_users),
            "online_user_list": [
                {
                    "user_id": p.user_id,
                    "username": p.username,
                    "status": p.status,
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
            "annotations": annotations,
            "activity": activity,
        }

        assert dashboard["online_users"] == 1
        assert dashboard["active_sessions"] == 1
        assert dashboard["annotations"]["total"] == 50
        assert dashboard["activity"]["total_events"] == 150

    @pytest.mark.asyncio
    async def test_dashboard_empty_data(
        self,
        mock_presence_service,
        mock_session_manager,
        mock_annotation_service,
        mock_activity_feed,
    ):
        """Test dashboard with no activity."""
        mock_presence_service.get_presences.return_value = []
        mock_session_manager.list_sessions.return_value = []
        mock_annotation_service.get_annotation_summary.return_value = {
            "total": 0,
            "unresolved": 0,
            "by_type": {},
        }
        mock_activity_feed.get_activity_summary.return_value = {
            "total_events": 0,
            "active_users": 0,
        }

        presences = await mock_presence_service.get_presences()
        sessions = await mock_session_manager.list_sessions()

        assert len(presences) == 0
        assert len(sessions) == 0


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestCollaborationEdgeCases:
    """Tests for collaboration edge cases."""

    @pytest.mark.asyncio
    async def test_session_max_participants(self, mock_session_manager):
        """Test session participant limit."""
        mock_session_manager.join_session.return_value = None

        # Session is full
        result = await mock_session_manager.join_session(
            session_id=str(uuid4()),
            user_id=str(uuid4()),
            username="newuser",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_annotation_on_deleted_file(self, mock_annotation_service):
        """Test annotation on deleted file."""
        # Annotation still exists but file may not
        annotation = MagicMock(
            id=str(uuid4()),
            file_path="deleted/file.py",
            resolved=False,
        )
        mock_annotation_service.get_annotation.return_value = annotation

        result = await mock_annotation_service.get_annotation(annotation.id)

        assert result is not None
        assert result.file_path == "deleted/file.py"

    @pytest.mark.asyncio
    async def test_presence_timeout(self, mock_presence_service):
        """Test presence timeout handling."""
        stale_presence = MagicMock(
            user_id=str(uuid4()),
            status=PresenceStatus.ONLINE,
            last_seen=datetime.now(UTC) - timedelta(minutes=10),
        )

        # Should be marked as offline due to timeout
        mock_presence_service.get_presence.return_value = stale_presence

        result = await mock_presence_service.get_presence(stale_presence.user_id)

        # Presence exists but is stale
        assert (datetime.now(UTC) - result.last_seen).total_seconds() > 300

    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self, mock_session_manager, sample_session):
        """Test concurrent session join/leave operations."""
        mock_session_manager.join_session.return_value = sample_session
        mock_session_manager.leave_session.return_value = sample_session

        user_id = str(uuid4())

        # Rapid join/leave
        await mock_session_manager.join_session(
            session_id=sample_session.id,
            user_id=user_id,
            username="user",
        )
        await mock_session_manager.leave_session(
            session_id=sample_session.id,
            user_id=user_id,
        )

        assert mock_session_manager.join_session.call_count == 1
        assert mock_session_manager.leave_session.call_count == 1

    @pytest.mark.asyncio
    async def test_annotation_thread_depth(self, mock_annotation_service):
        """Test deeply nested annotation replies."""
        # Build a chain of replies
        parent_id = str(uuid4())
        for i in range(5):
            reply = MagicMock(
                id=str(uuid4()),
                parent_id=parent_id,
                content=f"Reply {i}",
            )
            mock_annotation_service.create_annotation.return_value = reply
            parent_id = reply.id

        # Final reply
        result = await mock_annotation_service.create_annotation(
            organization_id=str(uuid4()),
            project_id=str(uuid4()),
            file_path="src/main.py",
            start_line=10,
            end_line=10,
            annotation_type=AnnotationType.COMMENT,
            content="Final reply",
            author_id=str(uuid4()),
            author_username="user",
            parent_id=parent_id,
        )

        assert result.parent_id is not None

    def test_activity_type_filtering(self):
        """Test filtering activities by type."""
        activities = [
            MagicMock(activity_type=MagicMock(value="session_started")),
            MagicMock(activity_type=MagicMock(value="annotation_created")),
            MagicMock(activity_type=MagicMock(value="session_started")),
            MagicMock(activity_type=MagicMock(value="mention")),
        ]

        session_activities = [
            a for a in activities if a.activity_type.value == "session_started"
        ]

        assert len(session_activities) == 2
