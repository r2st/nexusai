"""Real-time Collaboration Services."""

from app.services.collaboration.models import (
    UserPresence,
    PresenceStatus,
    SharedSession,
    SessionType,
    SessionParticipant,
    CodeAnnotation,
    AnnotationType,
    ActivityEvent,
    ActivityType,
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
from app.services.collaboration.service import (
    CollaborationService,
    get_collaboration_service,
)

__all__ = [
    # Models
    "UserPresence",
    "PresenceStatus",
    "SharedSession",
    "SessionType",
    "SessionParticipant",
    "CodeAnnotation",
    "AnnotationType",
    "ActivityEvent",
    "ActivityType",
    "CollaborationRoom",
    # Services
    "PresenceService",
    "get_presence_service",
    "SessionManager",
    "get_session_manager",
    "AnnotationService",
    "get_annotation_service",
    "ActivityFeed",
    "get_activity_feed",
    "CollaborationService",
    "get_collaboration_service",
]
