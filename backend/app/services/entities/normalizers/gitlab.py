"""GitLab normalizer for transforming GitLab events to canonical entities."""

from datetime import UTC, datetime
from typing import Any

from app.services.entities.models import (
    Commit,
    Developer,
    Entity,
    EntityType,
    PullRequest,
    Repository,
    Build,
    Deployment,
)
from app.services.entities.normalizers.base import BaseNormalizer


class GitLabNormalizer(BaseNormalizer):
    """Normalizer for GitLab webhook events."""

    @property
    def source(self) -> str:
        return "gitlab"

    def normalize(
        self,
        event_type: str,
        payload: dict[str, Any],
        tenant_id: str,
        connection_id: str | None = None,
    ) -> list[Entity]:
        """Normalize GitLab event payload to entities."""
        entities: list[Entity] = []

        # Extract project/repository
        if "project" in payload:
            repo = self._normalize_repository(
                payload["project"], tenant_id, connection_id
            )
            if repo:
                entities.append(repo)

        # Extract user
        if "user" in payload:
            dev = self._normalize_developer(
                payload["user"], tenant_id, connection_id
            )
            if dev:
                entities.append(dev)

        # Event-specific normalization
        if event_type == "Push Hook":
            entities.extend(self._normalize_push(payload, tenant_id, connection_id))

        elif event_type == "Merge Request Hook":
            entities.extend(self._normalize_merge_request(payload, tenant_id, connection_id))

        elif event_type == "Pipeline Hook":
            entities.extend(self._normalize_pipeline(payload, tenant_id, connection_id))

        elif event_type == "Deployment Hook":
            entities.extend(self._normalize_deployment(payload, tenant_id, connection_id))

        return entities

    def _normalize_repository(
        self,
        data: dict[str, Any],
        tenant_id: str,
        connection_id: str | None,
    ) -> Repository | None:
        """Normalize GitLab project data."""
        if not data:
            return None

        return Repository(
            tenant_id=tenant_id,
            source=self.source,
            source_id=str(data.get("id")),
            connection_id=connection_id,
            source_created_at=self.parse_timestamp(data.get("created_at")),
            name=data.get("name", ""),
            full_name=data.get("path_with_namespace", ""),
            description=data.get("description"),
            url=data.get("web_url"),
            clone_url=data.get("git_http_url") or data.get("http_url"),
            default_branch=data.get("default_branch", "main"),
            is_private=data.get("visibility") == "private",
            star_count=data.get("star_count", 0),
            fork_count=data.get("forks_count", 0),
        )

    def _normalize_developer(
        self,
        data: dict[str, Any],
        tenant_id: str,
        connection_id: str | None,
    ) -> Developer | None:
        """Normalize GitLab user data."""
        if not data:
            return None

        return Developer(
            tenant_id=tenant_id,
            source=self.source,
            source_id=str(data.get("id")),
            connection_id=connection_id,
            username=data.get("username", ""),
            display_name=data.get("name"),
            email=data.get("email"),
            avatar_url=data.get("avatar_url"),
        )

    def _normalize_push(
        self,
        payload: dict[str, Any],
        tenant_id: str,
        connection_id: str | None,
    ) -> list[Entity]:
        """Normalize push event to commit entities."""
        entities: list[Entity] = []
        project = payload.get("project", {})
        project_id = str(project.get("id")) if project else None

        for commit_data in payload.get("commits", []):
            author = commit_data.get("author", {})

            commit = Commit(
                tenant_id=tenant_id,
                source=self.source,
                source_id=commit_data.get("id", ""),
                connection_id=connection_id,
                source_created_at=self.parse_timestamp(commit_data.get("timestamp")),
                sha=commit_data.get("id", ""),
                message=commit_data.get("message", ""),
                short_message=commit_data.get("title") or commit_data.get("message", "").split("\n")[0][:80],
                author_name=author.get("name"),
                author_email=author.get("email"),
                repository_id=project_id,
                branch=payload.get("ref", "").replace("refs/heads/", ""),
                additions=len(commit_data.get("added", [])),
                deletions=len(commit_data.get("removed", [])),
                files_changed=len(commit_data.get("modified", [])) + len(commit_data.get("added", [])) + len(commit_data.get("removed", [])),
                files=commit_data.get("modified", []) + commit_data.get("added", []) + commit_data.get("removed", []),
                url=commit_data.get("url"),
            )
            entities.append(commit)

        return entities

    def _normalize_merge_request(
        self,
        payload: dict[str, Any],
        tenant_id: str,
        connection_id: str | None,
    ) -> list[Entity]:
        """Normalize merge request event."""
        entities: list[Entity] = []
        mr_data = payload.get("object_attributes", {})

        if not mr_data:
            return entities

        project = payload.get("project", {})
        project_id = str(project.get("id")) if project else None

        user = payload.get("user", {})

        # Map state
        state = mr_data.get("state", "opened")
        action = mr_data.get("action", "")
        merged = state == "merged" or action == "merge"

        # Extract assignees
        assignee_ids = []
        for assignee in payload.get("assignees", []):
            assignee_ids.append(str(assignee.get("id")))
            dev = self._normalize_developer(assignee, tenant_id, connection_id)
            if dev:
                entities.append(dev)

        # Extract reviewers
        reviewer_ids = []
        for reviewer in payload.get("reviewers", []):
            reviewer_ids.append(str(reviewer.get("id")))
            dev = self._normalize_developer(reviewer, tenant_id, connection_id)
            if dev:
                entities.append(dev)

        mr = PullRequest(
            tenant_id=tenant_id,
            source=self.source,
            source_id=str(mr_data.get("id")),
            connection_id=connection_id,
            source_created_at=self.parse_timestamp(mr_data.get("created_at")),
            source_updated_at=self.parse_timestamp(mr_data.get("updated_at")),
            number=mr_data.get("iid", 0),
            title=mr_data.get("title", ""),
            body=mr_data.get("description"),
            url=mr_data.get("url"),
            state=state,
            is_draft=mr_data.get("work_in_progress", False) or mr_data.get("draft", False),
            merged=merged,
            merged_at=self.parse_timestamp(mr_data.get("merged_at")),
            closed_at=self.parse_timestamp(mr_data.get("closed_at")) if state == "closed" else None,
            source_branch=mr_data.get("source_branch"),
            target_branch=mr_data.get("target_branch"),
            head_sha=mr_data.get("last_commit", {}).get("id"),
            repository_id=project_id,
            author_id=str(mr_data.get("author_id")) if mr_data.get("author_id") else None,
            merged_by_id=str(mr_data.get("merge_user_id")) if mr_data.get("merge_user_id") else None,
            assignee_ids=assignee_ids,
            reviewer_ids=reviewer_ids,
            labels=payload.get("labels", []),
        )
        entities.append(mr)

        return entities

    def _normalize_pipeline(
        self,
        payload: dict[str, Any],
        tenant_id: str,
        connection_id: str | None,
    ) -> list[Entity]:
        """Normalize pipeline event."""
        entities: list[Entity] = []
        pipeline = payload.get("object_attributes", {})

        if not pipeline:
            return entities

        project = payload.get("project", {})

        # Map status
        status = pipeline.get("status", "pending")
        status_map = {
            "success": "success",
            "failed": "failed",
            "canceled": "cancelled",
            "skipped": "skipped",
            "pending": "pending",
            "running": "running",
            "created": "pending",
        }

        build = Build(
            tenant_id=tenant_id,
            source=self.source,
            source_id=str(pipeline.get("id")),
            connection_id=connection_id,
            source_created_at=self.parse_timestamp(pipeline.get("created_at")),
            number=pipeline.get("id", 0),
            url=pipeline.get("url"),
            status=status_map.get(status, "pending"),
            started_at=self.parse_timestamp(pipeline.get("created_at")),
            completed_at=self.parse_timestamp(pipeline.get("finished_at")),
            duration_seconds=pipeline.get("duration"),
            commit_sha=pipeline.get("sha"),
            branch=pipeline.get("ref"),
            repository_id=str(project.get("id")) if project else None,
            trigger=pipeline.get("source"),
        )
        entities.append(build)

        return entities

    def _normalize_deployment(
        self,
        payload: dict[str, Any],
        tenant_id: str,
        connection_id: str | None,
    ) -> list[Entity]:
        """Normalize deployment event."""
        entities: list[Entity] = []

        deploy_data = payload.get("object_attributes", {})
        if not deploy_data:
            # Try alternative structure
            deploy_data = payload

        project = payload.get("project", {})

        # Map status
        status = deploy_data.get("status", "pending")
        status_map = {
            "success": "success",
            "failed": "failed",
            "canceled": "cancelled",
            "running": "in_progress",
            "created": "pending",
        }

        deployment = Deployment(
            tenant_id=tenant_id,
            source=self.source,
            source_id=str(deploy_data.get("deployment_id") or deploy_data.get("id")),
            connection_id=connection_id,
            source_created_at=self.parse_timestamp(deploy_data.get("created_at")),
            status=status_map.get(status, "pending"),
            commit_sha=deploy_data.get("sha") or deploy_data.get("commit_sha"),
            environment_name=deploy_data.get("environment"),
            repository_id=str(project.get("id")) if project else None,
        )
        entities.append(deployment)

        return entities

    def extract_entity_type(self, event_type: str) -> EntityType | None:
        """Map GitLab event type to entity type."""
        mapping = {
            "Push Hook": EntityType.COMMIT,
            "Tag Push Hook": EntityType.RELEASE,
            "Merge Request Hook": EntityType.PULL_REQUEST,
            "Pipeline Hook": EntityType.BUILD,
            "Job Hook": EntityType.BUILD,
            "Deployment Hook": EntityType.DEPLOYMENT,
            "Issue Hook": EntityType.ISSUE,
            "Release Hook": EntityType.RELEASE,
        }
        return mapping.get(event_type)
