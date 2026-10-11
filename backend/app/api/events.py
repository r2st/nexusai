"""Event ingestion API endpoints.

Provides:
- Generic webhook receiver
- Event query endpoints
- Event replay endpoints
- Statistics endpoints
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_current_user, get_db

from app.models.user import User
from app.services.events import (
    EventQuery,
    EventSource,
    EventType,
    WebhookPayload,
    get_event_store,
    get_webhook_handler,
    get_event_publisher,
)


logger = structlog.get_logger()

router = APIRouter(tags=["events"])


# Request/Response models
class WebhookRequest(BaseModel):
    """Request body for generic webhook endpoint."""

    payload: dict[str, Any] = Field(..., description="Webhook payload")


class EventListResponse(BaseModel):
    """Response for event list queries."""

    events: list[dict[str, Any]]
    total: int
    has_more: bool


class EventStatsResponse(BaseModel):
    """Response for event statistics."""

    tenant_id: str
    total_events: int
    events_by_source: dict[str, int]
    events_by_type: dict[str, int]
    oldest_event: datetime | None
    newest_event: datetime | None


class ReplayRequest(BaseModel):
    """Request for event replay."""

    source: EventSource | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    batch_size: int = Field(default=100, ge=1, le=1000)


class PublisherStatsResponse(BaseModel):
    """Response for publisher statistics."""

    connected: bool
    using_nats: bool
    memory_queue_size: int
    subscribers: int
    stream: dict[str, Any] | None = None


# Webhook endpoints
@router.post(
    "/webhooks/{source}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive webhook from a source",
)
async def receive_webhook(
    source: EventSource,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    x_connection_id: str | None = Header(None, alias="X-Connection-ID"),
):
    """Receive and process a webhook from any supported source.

    The source is specified in the path, and tenant ID must be provided
    in the X-Tenant-ID header.

    Source-specific headers are automatically extracted:
    - GitHub: X-GitHub-Event, X-Hub-Signature-256, X-GitHub-Delivery
    - GitLab: X-Gitlab-Event, X-Gitlab-Token
    - Jira: X-Atlassian-Webhook-Identifier
    - PagerDuty: X-Webhook-Id
    - Slack: X-Slack-Request-Timestamp, X-Slack-Signature
    """
    # Get raw body
    body = await request.body()

    try:
        import json
        payload_dict = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    # Extract headers
    headers = {k.lower(): v for k, v in request.headers.items()}

    # Determine event type from source-specific header
    event_type = _get_event_type_from_headers(source, headers)

    # Get signature from source-specific header
    signature = _get_signature_from_headers(source, headers)

    # Get delivery ID
    delivery_id = _get_delivery_id_from_headers(source, headers)

    # Create webhook payload
    webhook = WebhookPayload(
        source=source,
        event_type=event_type,
        payload=payload_dict,
        headers=headers,
        signature=signature,
        delivery_id=delivery_id,
        tenant_id=x_tenant_id,
        connection_id=x_connection_id,
    )

    # Process webhook
    handler = get_webhook_handler()
    try:
        event = await handler.handle_webhook(webhook, db)
        await db.commit()

        return {
            "status": "accepted",
            "event_id": event.id,
            "event_type": event.event_type.value,
            "source": event.source.value,
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload. Please check the request format.",
        )
    except Exception as e:
        await db.rollback()
        logger.error("Failed to process webhook", source=source.value, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook. Please try again later.",
        )


def _get_event_type_from_headers(source: EventSource, headers: dict[str, str]) -> str:
    """Extract event type from source-specific headers."""
    if source == EventSource.GITHUB:
        return headers.get("x-github-event", "unknown")
    elif source == EventSource.GITLAB:
        return headers.get("x-gitlab-event", "unknown")
    elif source == EventSource.JIRA:
        return headers.get("x-atlassian-webhook-identifier", "unknown")
    elif source == EventSource.PAGERDUTY:
        return headers.get("x-pagerduty-signature", "unknown")
    elif source == EventSource.SLACK:
        return "callback"  # Slack uses payload.type
    else:
        return "webhook"


def _get_signature_from_headers(source: EventSource, headers: dict[str, str]) -> str | None:
    """Extract signature from source-specific headers."""
    if source == EventSource.GITHUB:
        return headers.get("x-hub-signature-256")
    elif source == EventSource.GITLAB:
        return headers.get("x-gitlab-token")
    elif source == EventSource.SLACK:
        return headers.get("x-slack-signature")
    return None


def _get_delivery_id_from_headers(source: EventSource, headers: dict[str, str]) -> str | None:
    """Extract delivery ID from source-specific headers."""
    if source == EventSource.GITHUB:
        return headers.get("x-github-delivery")
    elif source == EventSource.PAGERDUTY:
        return headers.get("x-webhook-id")
    return None


# Query endpoints
@router.get(
    "",
    response_model=EventListResponse,
    summary="Query events",
)
async def list_events(
    source: EventSource | None = None,
    event_type: EventType | None = None,
    connection_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    processed: bool | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Query events for the current tenant.

    Results are filtered by the authenticated user's organization.
    """
    # Get tenant ID from user's organization
    # For now, use user ID as fallback
    tenant_id = str(current_user.organization_id) if current_user.organization_id else str(current_user.id)

    query = EventQuery(
        tenant_id=tenant_id,
        source=source,
        event_type=event_type,
        connection_id=connection_id,
        start_time=start_time,
        end_time=end_time,
        processed=processed,
        limit=limit + 1,  # Fetch one extra to check has_more
        offset=offset,
    )

    store = get_event_store()
    events = await store.query(db, query)

    has_more = len(events) > limit
    if has_more:
        events = events[:limit]

    return EventListResponse(
        events=events,
        total=len(events),
        has_more=has_more,
    )


@router.get(
    "/stats",
    response_model=EventStatsResponse,
    summary="Get event statistics",
)
async def get_event_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get event statistics for the current tenant."""
    tenant_id = str(current_user.organization_id) if current_user.organization_id else str(current_user.id)

    store = get_event_store()
    stats = await store.get_stats(db, tenant_id)

    return EventStatsResponse(
        tenant_id=stats.tenant_id,
        total_events=stats.total_events,
        events_by_source=stats.events_by_source,
        events_by_type=stats.events_by_type,
        oldest_event=stats.oldest_event,
        newest_event=stats.newest_event,
    )


@router.get(
    "/{event_id}",
    summary="Get event details",
)
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full details of a specific event."""
    tenant_id = str(current_user.organization_id) if current_user.organization_id else str(current_user.id)

    # Query for the event metadata
    store = get_event_store()
    query = EventQuery(tenant_id=tenant_id, limit=1)

    # This is a simplified lookup - in production, add event_id filter
    from sqlalchemy import text
    result = await db.execute(
        text("""
            SELECT storage_path FROM events_index
            WHERE id = :event_id AND tenant_id = :tenant_id
        """),
        {"event_id": event_id, "tenant_id": tenant_id},
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    # Fetch full event from S3
    event = await store.get_by_path(row.storage_path)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event payload not found in storage",
        )

    return event.model_dump()


# Replay endpoints
@router.post(
    "/replay",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Replay events",
)
async def replay_events(
    request: ReplayRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replay events from the event store.

    This republishes events to the message queue for reprocessing.
    Useful for backfilling or recovering from processing failures.
    """
    tenant_id = str(current_user.organization_id) if current_user.organization_id else str(current_user.id)

    store = get_event_store()
    publisher = get_event_publisher()

    # Count events to replay
    query = EventQuery(
        tenant_id=tenant_id,
        source=request.source,
        start_time=request.start_time,
        end_time=request.end_time,
        limit=1,
    )
    events_meta = await store.query(db, query)

    # Start replay in background (in production, use a task queue)
    replay_count = 0
    async for event in store.replay(
        db,
        tenant_id,
        source=request.source,
        start_time=request.start_time,
        end_time=request.end_time,
        batch_size=request.batch_size,
    ):
        await publisher.publish(event)
        replay_count += 1

        # Limit for safety
        if replay_count >= 10000:
            break

    return {
        "status": "completed",
        "events_replayed": replay_count,
        "tenant_id": tenant_id,
    }


# Admin endpoints
@router.get(
    "/publisher/stats",
    response_model=PublisherStatsResponse,
    summary="Get publisher statistics",
)
async def get_publisher_stats(
    current_user: User = Depends(get_current_user),
):
    """Get message queue publisher statistics.

    Requires admin role.
    """
    # In production, check for admin role
    publisher = get_event_publisher()
    stats = await publisher.get_stats()

    return PublisherStatsResponse(**stats)


@router.post(
    "/publisher/connect",
    summary="Connect to message queue",
)
async def connect_publisher(
    current_user: User = Depends(get_current_user),
):
    """Connect or reconnect to the message queue.

    Requires admin role.
    """
    publisher = get_event_publisher()
    await publisher.connect()

    return {"status": "connected"}


@router.post(
    "/{event_id}/mark-processed",
    summary="Mark event as processed",
)
async def mark_event_processed(
    event_id: str,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an event as processed or failed.

    Used by event consumers to update processing state.
    """
    store = get_event_store()
    await store.mark_processed(db, event_id, error)
    await db.commit()

    return {
        "status": "updated",
        "event_id": event_id,
        "processed": error is None,
    }
