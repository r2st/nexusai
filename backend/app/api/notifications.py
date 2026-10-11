"""Notification API endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import structlog

from app.api.deps import get_current_user
from app.models.user import User
from app.services.notifications import (
    NotificationService,
    get_notification_service,
    NotificationMessage,
    NotificationChannel,
    NotificationType,
    NotificationPriority,
    NotificationPreferences,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/notifications", tags=["notifications"])


# Request/Response Models
class SendNotificationRequest(BaseModel):
    """Request to send a notification."""

    type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    title: str
    body: str
    data: dict[str, Any] = Field(default_factory=dict)
    channels: list[NotificationChannel] | None = None
    user_ids: list[str] | None = None


class TestNotificationRequest(BaseModel):
    """Request to send a test notification."""

    channel: NotificationChannel
    webhook_url: str | None = None  # For testing specific webhook


class NotificationResultResponse(BaseModel):
    """Response for notification send."""

    total_channels: int
    successful: int
    failed: int
    details: list[dict[str, Any]]


class PreferencesRequest(BaseModel):
    """Request to update notification preferences."""

    enabled: bool = True
    channels: dict[NotificationChannel, bool] = Field(default_factory=dict)
    types: dict[NotificationType, bool] = Field(default_factory=dict)
    min_priority: NotificationPriority = NotificationPriority.MEDIUM
    email: str | None = None


# Dependencies
async def get_notif_service() -> NotificationService:
    """Get notification service instance."""
    return get_notification_service()


# Endpoints
@router.post("/send", response_model=NotificationResultResponse)
async def send_notification(
    request: SendNotificationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notif_service)],
) -> NotificationResultResponse:
    """Send a notification to configured channels.

    The notification will be sent to all specified channels,
    or default channels for the notification type if not specified.
    """
    try:
        message = NotificationMessage(
            type=request.type,
            priority=request.priority,
            title=request.title,
            body=request.body,
            data=request.data,
            channels=request.channels,
            user_ids=request.user_ids,
        )

        result = await service.send(message)

        return NotificationResultResponse(
            total_channels=result.total_channels,
            successful=result.successful,
            failed=result.failed,
            details=[
                {
                    "channel": r.channel.value,
                    "success": r.success,
                    "error": r.error,
                }
                for r in result.results
            ],
        )

    except Exception as e:
        logger.error("Failed to send notification", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send notification. Please try again later.",
        )


@router.post("/test")
async def test_notification(
    request: TestNotificationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notif_service)],
) -> dict[str, Any]:
    """Send a test notification to verify configuration.

    Useful for testing webhook URLs and channel configurations.
    """
    message = NotificationMessage(
        type=NotificationType.SYSTEM_ALERT,
        priority=NotificationPriority.LOW,
        title="NexusAI Test Notification",
        body="This is a test notification from NexusAI. If you see this, your notification channel is configured correctly!",
        data={
            "test": True,
            "user": current_user.email if hasattr(current_user, 'email') else str(current_user.id),
        },
    )

    result = await service.send_to_channel(request.channel, message)

    return {
        "channel": result.channel.value,
        "success": result.success,
        "error": result.error,
    }


@router.get("/channels")
async def get_available_channels(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notif_service)],
) -> dict[str, Any]:
    """Get list of available notification channels."""
    channels = service.get_available_channels()

    return {
        "channels": [ch.value for ch in channels],
        "count": len(channels),
    }


@router.get("/preferences")
async def get_preferences(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notif_service)],
) -> NotificationPreferences:
    """Get notification preferences for the current user."""
    prefs = service.get_user_preferences(str(current_user.id))

    if not prefs:
        # Return default preferences
        return NotificationPreferences(user_id=str(current_user.id))

    return prefs


@router.put("/preferences")
async def update_preferences(
    request: PreferencesRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notif_service)],
) -> NotificationPreferences:
    """Update notification preferences for the current user."""
    prefs = NotificationPreferences(
        user_id=str(current_user.id),
        enabled=request.enabled,
        channels=request.channels,
        types=request.types,
        min_priority=request.min_priority,
        email=request.email,
    )

    service.set_user_preferences(prefs)

    return prefs


@router.get("/types", summary="Get all available notification types")
async def get_notification_types() -> dict[str, Any]:
    """Get all available notification types."""
    return {
        "types": [
            {
                "value": t.value,
                "name": t.name,
            }
            for t in NotificationType
        ]
    }


@router.get("/priorities", summary="Get all notification priorities")
async def get_priorities() -> dict[str, Any]:
    """Get all notification priorities."""
    return {
        "priorities": [
            {
                "value": p.value,
                "name": p.name,
            }
            for p in NotificationPriority
        ]
    }


@router.get("/health")
async def health_check(
    service: Annotated[NotificationService, Depends(get_notif_service)],
) -> dict[str, Any]:
    """Check notification service health and configured channels."""
    channels = service.get_available_channels()

    return {
        "status": "healthy",
        "service": "notifications",
        "configured_channels": [ch.value for ch in channels],
        "enabled": service.config.enabled,
    }
