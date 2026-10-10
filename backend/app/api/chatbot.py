"""Chatbot Integration API endpoints."""

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Header, Response, status
from pydantic import BaseModel, Field
import structlog

from app.services.chatbot import (
    get_chatbot_service,
    ChatPlatform,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


# --- Request/Response Models ---

class ConfigureSlackRequest(BaseModel):
    """Request to configure Slack bot."""
    bot_token: str
    signing_secret: str
    app_id: str | None = None


class ConfigureTeamsRequest(BaseModel):
    """Request to configure Teams bot."""
    app_id: str
    app_password: str
    tenant_id: str | None = None


class LinkUserRequest(BaseModel):
    """Request to link a platform user."""
    platform: ChatPlatform
    platform_user_id: str
    nexus_user_id: str
    organization_id: str


class UnlinkUserRequest(BaseModel):
    """Request to unlink a platform user."""
    platform: ChatPlatform
    platform_user_id: str


class SendNotificationRequest(BaseModel):
    """Request to send a notification."""
    platform: ChatPlatform
    channel_ids: list[str]
    event_type: str
    title: str
    message: str
    metadata: dict[str, Any] | None = None


class BroadcastNotificationRequest(BaseModel):
    """Request to broadcast a notification."""
    event_type: str
    title: str
    message: str
    metadata: dict[str, Any] | None = None


class SubscribeRequest(BaseModel):
    """Request to subscribe a channel."""
    platform: ChatPlatform
    channel_id: str
    event_types: list[str]


class UnsubscribeRequest(BaseModel):
    """Request to unsubscribe a channel."""
    platform: ChatPlatform
    channel_id: str
    event_types: list[str] | None = None


class SendSlackMessageRequest(BaseModel):
    """Request to send a Slack message."""
    channel_id: str
    text: str
    blocks: list[dict[str, Any]] | None = None
    thread_ts: str | None = None


class SendTeamsMessageRequest(BaseModel):
    """Request to send a Teams message."""
    conversation_id: str
    text: str | None = None
    card: dict[str, Any] | None = None


# --- Configuration Endpoints ---

@router.post("/configure/slack")
async def configure_slack(request: ConfigureSlackRequest):
    """Configure Slack bot."""
    service = get_chatbot_service()
    service.configure_slack(
        bot_token=request.bot_token,
        signing_secret=request.signing_secret,
        app_id=request.app_id,
    )
    return {"configured": True, "platform": "slack"}


@router.post("/configure/teams")
async def configure_teams(request: ConfigureTeamsRequest):
    """Configure Teams bot."""
    service = get_chatbot_service()
    service.configure_teams(
        app_id=request.app_id,
        app_password=request.app_password,
        tenant_id=request.tenant_id,
    )
    return {"configured": True, "platform": "teams"}


# --- Slack Webhook Endpoints ---

@router.post("/slack/events")
async def slack_events(
    request: Request,
    x_slack_signature: str = Header(None, alias="X-Slack-Signature"),
    x_slack_request_timestamp: str = Header(None, alias="X-Slack-Request-Timestamp"),
):
    """Handle Slack event webhook."""
    service = get_chatbot_service()

    body = await request.body()

    if not x_slack_signature or not x_slack_request_timestamp:
        raise HTTPException(status_code=401, detail="Missing signature headers")
    if not service.verify_slack_signature(
        timestamp=x_slack_request_timestamp,
        signature=x_slack_signature,
        body=body,
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse JSON
    try:
        event_data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Handle event
    result = await service.handle_slack_event(event_data)

    if result:
        return result

    return {"ok": True}


@router.post("/slack/commands")
async def slack_commands(
    request: Request,
    x_slack_signature: str = Header(None, alias="X-Slack-Signature"),
    x_slack_request_timestamp: str = Header(None, alias="X-Slack-Request-Timestamp"),
):
    """Handle Slack slash command."""
    service = get_chatbot_service()

    body = await request.body()

    if not x_slack_signature or not x_slack_request_timestamp:
        raise HTTPException(status_code=401, detail="Missing signature headers")
    if not service.verify_slack_signature(
        timestamp=x_slack_request_timestamp,
        signature=x_slack_signature,
        body=body,
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse form data
    form_data = await request.form()
    command_data = dict(form_data)

    # Handle command
    result = await service.handle_slack_command(command_data)

    return result


@router.post("/slack/interactions")
async def slack_interactions(
    request: Request,
    x_slack_signature: str = Header(None, alias="X-Slack-Signature"),
    x_slack_request_timestamp: str = Header(None, alias="X-Slack-Request-Timestamp"),
):
    """Handle Slack interactive component."""
    service = get_chatbot_service()

    body = await request.body()

    if not x_slack_signature or not x_slack_request_timestamp:
        raise HTTPException(status_code=401, detail="Missing signature headers")
    if not service.verify_slack_signature(
        timestamp=x_slack_request_timestamp,
        signature=x_slack_signature,
        body=body,
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse form data
    form_data = await request.form()
    payload_str = form_data.get("payload", "{}")

    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Handle interaction
    result = await service.handle_slack_interaction(payload)

    if result:
        return result

    return Response(status_code=200)


# --- Teams Webhook Endpoints ---

@router.post("/teams/messages")
async def teams_messages(request: Request):
    """Handle Teams bot messages."""
    service = get_chatbot_service()

    try:
        activity = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Handle activity
    result = await service.handle_teams_activity(activity)

    if result:
        return result

    return {"status": "ok"}


# --- User Linking Endpoints ---

@router.post("/users/link")
async def link_user(request: LinkUserRequest):
    """Link a platform user to NexusAI."""
    service = get_chatbot_service()
    success = await service.link_user(
        platform=request.platform,
        platform_user_id=request.platform_user_id,
        nexus_user_id=request.nexus_user_id,
        organization_id=request.organization_id,
    )

    if not success:
        raise HTTPException(status_code=404, detail="User not found on platform")

    return {"linked": True}


@router.post("/users/unlink")
async def unlink_user(request: UnlinkUserRequest):
    """Unlink a platform user from NexusAI."""
    service = get_chatbot_service()
    success = await service.unlink_user(
        platform=request.platform,
        platform_user_id=request.platform_user_id,
    )

    return {"unlinked": success}


@router.get("/users/{platform}/{platform_user_id}")
async def get_linked_user(platform: ChatPlatform, platform_user_id: str):
    """Get linked user info."""
    service = get_chatbot_service()
    user = await service.get_linked_user(platform, platform_user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"user": user.model_dump()}


# --- Notification Endpoints ---

@router.post("/notifications/send")
async def send_notification(request: SendNotificationRequest):
    """Send notification to subscribed channels."""
    service = get_chatbot_service()
    sent_to = await service.send_notification(
        platform=request.platform,
        channel_ids=request.channel_ids,
        event_type=request.event_type,
        title=request.title,
        message=request.message,
        metadata=request.metadata,
    )
    return {"sent_to": sent_to}


@router.post("/notifications/broadcast")
async def broadcast_notification(request: BroadcastNotificationRequest):
    """Broadcast notification to all platforms."""
    service = get_chatbot_service()
    results = await service.broadcast_notification(
        event_type=request.event_type,
        title=request.title,
        message=request.message,
        metadata=request.metadata,
    )
    return {"results": results}


# --- Subscription Endpoints ---

@router.post("/subscriptions", status_code=status.HTTP_201_CREATED)
async def subscribe_channel(request: SubscribeRequest):
    """Subscribe a channel to event types."""
    service = get_chatbot_service()
    success = await service.subscribe_channel(
        platform=request.platform,
        channel_id=request.channel_id,
        event_types=request.event_types,
    )
    return {"subscribed": success}


@router.delete("/subscriptions", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_channel(request: UnsubscribeRequest) -> None:
    """Unsubscribe a channel from event types."""
    service = get_chatbot_service()
    await service.unsubscribe_channel(
        platform=request.platform,
        channel_id=request.channel_id,
        event_types=request.event_types,
    )


@router.get("/subscriptions/{platform}/{channel_id}")
async def get_subscriptions(platform: ChatPlatform, channel_id: str):
    """Get subscriptions for a channel."""
    service = get_chatbot_service()
    subscriptions = await service.get_subscriptions(platform, channel_id)
    return {"subscriptions": subscriptions}


# --- Message Endpoints ---

@router.post("/messages/slack")
async def send_slack_message(request: SendSlackMessageRequest):
    """Send a message to Slack."""
    service = get_chatbot_service()
    result = await service.send_slack_message(
        channel_id=request.channel_id,
        text=request.text,
        blocks=request.blocks,
        thread_ts=request.thread_ts,
    )
    return {"result": result}


@router.post("/messages/teams")
async def send_teams_message(request: SendTeamsMessageRequest):
    """Send a message to Teams."""
    service = get_chatbot_service()
    result = await service.send_teams_message(
        conversation_id=request.conversation_id,
        text=request.text,
        card=request.card,
    )
    return {"result": result}


# --- Info Endpoints ---

@router.get("/commands")
async def get_commands(platform: ChatPlatform | None = None):
    """Get available bot commands."""
    service = get_chatbot_service()

    if platform:
        commands = service.get_platform_commands(platform)
    else:
        commands = service.get_commands()

    return {"commands": [c.model_dump() for c in commands]}


@router.get("/dashboard")
async def get_chatbot_dashboard():
    """Get chatbot dashboard data."""
    service = get_chatbot_service()
    dashboard = await service.get_chatbot_dashboard()
    return {"dashboard": dashboard}
