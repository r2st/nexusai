"""Activity Feed Service for Real-time Collaboration."""

import uuid
from datetime import datetime, timedelta
from typing import Any

from app.services.collaboration.models import (
    ActivityType,
    ActivityEvent,
)


class ActivityFeed:
    """Service for managing team activity feeds."""

    def __init__(self):
        # In-memory storage - replace with database in production
        self._events: dict[str, ActivityEvent] = {}
        self._org_events: dict[str, list[str]] = {}  # org_id -> event_ids (ordered)
        self._project_events: dict[str, list[str]] = {}  # project_id -> event_ids
        self._user_events: dict[str, list[str]] = {}  # user_id -> event_ids

        # Configuration
        self._max_events_per_feed = 1000
        self._event_retention_days = 30

    async def record_event(
        self,
        organization_id: str,
        activity_type: ActivityType,
        title: str,
        actor_id: str,
        actor_username: str,
        project_id: str | None = None,
        description: str | None = None,
        actor_avatar_url: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        target_url: str | None = None,
        metadata: dict[str, Any] | None = None,
        is_public: bool = True,
        visible_to_user_ids: list[str] | None = None,
    ) -> ActivityEvent:
        """Record a new activity event."""
        event_id = str(uuid.uuid4())
        now = datetime.utcnow()

        event = ActivityEvent(
            id=event_id,
            organization_id=organization_id,
            project_id=project_id,
            activity_type=activity_type,
            title=title,
            description=description,
            actor_id=actor_id,
            actor_username=actor_username,
            actor_avatar_url=actor_avatar_url,
            target_type=target_type,
            target_id=target_id,
            target_url=target_url,
            metadata=metadata or {},
            is_public=is_public,
            visible_to_user_ids=visible_to_user_ids,
            created_at=now,
        )

        self._events[event_id] = event

        # Index by organization
        if organization_id not in self._org_events:
            self._org_events[organization_id] = []
        self._org_events[organization_id].insert(0, event_id)
        self._trim_feed(self._org_events[organization_id])

        # Index by project
        if project_id:
            if project_id not in self._project_events:
                self._project_events[project_id] = []
            self._project_events[project_id].insert(0, event_id)
            self._trim_feed(self._project_events[project_id])

        # Index by user
        if actor_id not in self._user_events:
            self._user_events[actor_id] = []
        self._user_events[actor_id].insert(0, event_id)
        self._trim_feed(self._user_events[actor_id])

        return event

    def _trim_feed(self, feed: list[str]) -> None:
        """Trim feed to max size."""
        while len(feed) > self._max_events_per_feed:
            old_event_id = feed.pop()
            # Don't delete the event itself as it might be in other feeds

    async def get_event(self, event_id: str) -> ActivityEvent | None:
        """Get an event by ID."""
        return self._events.get(event_id)

    async def get_organization_feed(
        self,
        organization_id: str,
        viewer_user_id: str | None = None,
        activity_types: list[ActivityType] | None = None,
        project_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ActivityEvent]:
        """Get activity feed for an organization."""
        event_ids = self._org_events.get(organization_id, [])
        return await self._filter_events(
            event_ids=event_ids,
            viewer_user_id=viewer_user_id,
            activity_types=activity_types,
            project_id=project_id,
            since=since,
            until=until,
            limit=limit,
            offset=offset,
        )

    async def get_project_feed(
        self,
        project_id: str,
        viewer_user_id: str | None = None,
        activity_types: list[ActivityType] | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ActivityEvent]:
        """Get activity feed for a project."""
        event_ids = self._project_events.get(project_id, [])
        return await self._filter_events(
            event_ids=event_ids,
            viewer_user_id=viewer_user_id,
            activity_types=activity_types,
            project_id=None,  # Already filtered by project
            since=since,
            until=until,
            limit=limit,
            offset=offset,
        )

    async def get_user_feed(
        self,
        user_id: str,
        viewer_user_id: str | None = None,
        activity_types: list[ActivityType] | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ActivityEvent]:
        """Get activity feed for a user (events they created)."""
        event_ids = self._user_events.get(user_id, [])
        return await self._filter_events(
            event_ids=event_ids,
            viewer_user_id=viewer_user_id,
            activity_types=activity_types,
            project_id=None,
            since=since,
            until=until,
            limit=limit,
            offset=offset,
        )

    async def _filter_events(
        self,
        event_ids: list[str],
        viewer_user_id: str | None = None,
        activity_types: list[ActivityType] | None = None,
        project_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ActivityEvent]:
        """Filter and paginate events."""
        filtered = []
        skipped = 0

        for event_id in event_ids:
            event = self._events.get(event_id)
            if not event:
                continue

            # Visibility check
            if not event.is_public and viewer_user_id:
                if event.visible_to_user_ids and viewer_user_id not in event.visible_to_user_ids:
                    continue

            # Type filter
            if activity_types and event.activity_type not in activity_types:
                continue

            # Project filter
            if project_id and event.project_id != project_id:
                continue

            # Time filters
            if since and event.created_at < since:
                continue
            if until and event.created_at > until:
                continue

            # Pagination
            if skipped < offset:
                skipped += 1
                continue

            filtered.append(event)

            if len(filtered) >= limit:
                break

        return filtered

    async def get_activity_summary(
        self,
        organization_id: str,
        project_id: str | None = None,
        days: int = 7,
    ) -> dict[str, Any]:
        """Get activity summary for a period."""
        since = datetime.utcnow() - timedelta(days=days)

        if project_id:
            event_ids = self._project_events.get(project_id, [])
        else:
            event_ids = self._org_events.get(organization_id, [])

        by_type: dict[str, int] = {}
        by_user: dict[str, int] = {}
        by_day: dict[str, int] = {}
        total = 0

        for event_id in event_ids:
            event = self._events.get(event_id)
            if not event or event.created_at < since:
                continue

            total += 1

            # Count by type
            type_key = event.activity_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

            # Count by user
            by_user[event.actor_username] = by_user.get(event.actor_username, 0) + 1

            # Count by day
            day_key = event.created_at.strftime("%Y-%m-%d")
            by_day[day_key] = by_day.get(day_key, 0) + 1

        return {
            "period_days": days,
            "total_events": total,
            "by_type": by_type,
            "by_user": dict(sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:10]),
            "by_day": by_day,
            "most_active_day": max(by_day.items(), key=lambda x: x[1])[0] if by_day else None,
        }

    # Convenience methods for recording specific event types

    async def record_commit(
        self,
        organization_id: str,
        project_id: str,
        actor_id: str,
        actor_username: str,
        commit_sha: str,
        commit_message: str,
        branch: str,
        files_changed: int = 0,
    ) -> ActivityEvent:
        """Record a commit event."""
        return await self.record_event(
            organization_id=organization_id,
            project_id=project_id,
            activity_type=ActivityType.COMMIT,
            title=f"Committed to {branch}",
            description=commit_message[:200],
            actor_id=actor_id,
            actor_username=actor_username,
            target_type="commit",
            target_id=commit_sha,
            metadata={
                "commit_sha": commit_sha,
                "branch": branch,
                "files_changed": files_changed,
            },
        )

    async def record_pr_opened(
        self,
        organization_id: str,
        project_id: str,
        actor_id: str,
        actor_username: str,
        pr_id: str,
        pr_title: str,
        pr_url: str | None = None,
    ) -> ActivityEvent:
        """Record a PR opened event."""
        return await self.record_event(
            organization_id=organization_id,
            project_id=project_id,
            activity_type=ActivityType.PR_OPENED,
            title=f"Opened PR: {pr_title}",
            actor_id=actor_id,
            actor_username=actor_username,
            target_type="pr",
            target_id=pr_id,
            target_url=pr_url,
            metadata={"pr_title": pr_title},
        )

    async def record_pr_merged(
        self,
        organization_id: str,
        project_id: str,
        actor_id: str,
        actor_username: str,
        pr_id: str,
        pr_title: str,
        pr_url: str | None = None,
    ) -> ActivityEvent:
        """Record a PR merged event."""
        return await self.record_event(
            organization_id=organization_id,
            project_id=project_id,
            activity_type=ActivityType.PR_MERGED,
            title=f"Merged PR: {pr_title}",
            actor_id=actor_id,
            actor_username=actor_username,
            target_type="pr",
            target_id=pr_id,
            target_url=pr_url,
            metadata={"pr_title": pr_title},
        )

    async def record_session_started(
        self,
        organization_id: str,
        project_id: str | None,
        actor_id: str,
        actor_username: str,
        session_id: str,
        session_type: str,
        session_title: str,
    ) -> ActivityEvent:
        """Record a collaboration session started event."""
        return await self.record_event(
            organization_id=organization_id,
            project_id=project_id,
            activity_type=ActivityType.SESSION_STARTED,
            title=f"Started {session_type} session: {session_title}",
            actor_id=actor_id,
            actor_username=actor_username,
            target_type="session",
            target_id=session_id,
            metadata={
                "session_type": session_type,
                "session_title": session_title,
            },
        )

    async def record_annotation_created(
        self,
        organization_id: str,
        project_id: str,
        actor_id: str,
        actor_username: str,
        annotation_id: str,
        annotation_type: str,
        file_path: str,
        line: int,
        content_preview: str,
    ) -> ActivityEvent:
        """Record an annotation created event."""
        return await self.record_event(
            organization_id=organization_id,
            project_id=project_id,
            activity_type=ActivityType.ANNOTATION_CREATED,
            title=f"Added {annotation_type} on {file_path}:{line}",
            description=content_preview[:100],
            actor_id=actor_id,
            actor_username=actor_username,
            target_type="annotation",
            target_id=annotation_id,
            metadata={
                "annotation_type": annotation_type,
                "file_path": file_path,
                "line": line,
            },
        )

    async def record_analysis_completed(
        self,
        organization_id: str,
        project_id: str,
        actor_id: str,
        actor_username: str,
        analysis_type: str,
        issues_found: int = 0,
    ) -> ActivityEvent:
        """Record an analysis completed event."""
        return await self.record_event(
            organization_id=organization_id,
            project_id=project_id,
            activity_type=ActivityType.ANALYSIS_COMPLETED,
            title=f"{analysis_type} analysis completed",
            description=f"Found {issues_found} issues" if issues_found > 0 else "No issues found",
            actor_id=actor_id,
            actor_username=actor_username,
            target_type="analysis",
            metadata={
                "analysis_type": analysis_type,
                "issues_found": issues_found,
            },
        )

    async def record_deployment(
        self,
        organization_id: str,
        project_id: str,
        actor_id: str,
        actor_username: str,
        environment: str,
        version: str,
        status: str = "success",
    ) -> ActivityEvent:
        """Record a deployment event."""
        return await self.record_event(
            organization_id=organization_id,
            project_id=project_id,
            activity_type=ActivityType.DEPLOYMENT,
            title=f"Deployed {version} to {environment}",
            actor_id=actor_id,
            actor_username=actor_username,
            target_type="deployment",
            metadata={
                "environment": environment,
                "version": version,
                "status": status,
            },
        )

    async def cleanup_old_events(self, days: int | None = None) -> int:
        """Remove events older than retention period."""
        retention_days = days or self._event_retention_days
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        removed = 0

        events_to_remove = [
            event_id for event_id, event in self._events.items()
            if event.created_at < cutoff
        ]

        for event_id in events_to_remove:
            event = self._events.pop(event_id, None)
            if event:
                removed += 1

                # Clean up indices
                if event.organization_id in self._org_events:
                    try:
                        self._org_events[event.organization_id].remove(event_id)
                    except ValueError:
                        pass

                if event.project_id and event.project_id in self._project_events:
                    try:
                        self._project_events[event.project_id].remove(event_id)
                    except ValueError:
                        pass

                if event.actor_id in self._user_events:
                    try:
                        self._user_events[event.actor_id].remove(event_id)
                    except ValueError:
                        pass

        return removed


# Singleton instance
_activity_feed: ActivityFeed | None = None


def get_activity_feed() -> ActivityFeed:
    """Get the activity feed singleton."""
    global _activity_feed
    if _activity_feed is None:
        _activity_feed = ActivityFeed()
    return _activity_feed
