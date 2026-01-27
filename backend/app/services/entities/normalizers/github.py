"""GitHub normalizer for transforming GitHub events to canonical entities."""

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


class GitHubNormalizer(BaseNormalizer):
    """Normalizer for GitHub webhook events."""

    @property
    def source(self) -> str:
        return "github"

    def normalize(
        self,
        event_type: str,
        payload: dict[str, Any],
        tenant_id: str,
        connection_id: str | None = None,
    ) -> list[Entity]:
        """Normalize GitHub event payload to entities."""
        entities: list[Entity] = []

        # Extract repository entity from most events
        if "repository" in payload:
            repo = self._normalize_repository(
                payload["repository"], tenant_id, connection_id
            )
            if repo:
                entities.append(repo)

        # Extract sender as developer
        if "sender" in payload:
            dev = self._normalize_developer(
                payload["sender"], tenant_id, connection_id
            )
            if dev:
                entities.append(dev)

        # Event-specific normalization
        if event_type == "push":
            entities.extend(self._normalize_push(payload, tenant_id, connection_id))

        elif event_type == "pull_request":
            entities.extend(self._normalize_pull_request(payload, tenant_id, connection_id))

        elif event_type in ("check_run", "check_suite", "workflow_run"):
            entities.extend(self._normalize_ci(event_type, payload, tenant_id, connection_id))

        elif event_type in ("deployment", "deployment_status"):
            entities.extend(self._normalize_deployment(event_type, payload, tenant_id, connection_id))

        return entities

    def _normalize_repository(
        self,
        data: dict[str, Any],
        tenant_id: str,
        connection_id: str | None,
    ) -> Repository | None:
        """Normalize repository data."""
        if not data:
            return None

        owner = data.get("owner", {})

        return Repository(
            tenant_id=tenant_id,
            source=self.source,
            source_id=str(data.get("id")),
            connection_id=connection_id,
            source_created_at=self.parse_timestamp(data.get("created_at")),
            source_updated_at=self.parse_timestamp(data.get("updated_at")),
            name=data.get("name", ""),
            full_name=data.get("full_name", ""),
            description=data.get("description"),
            url=data.get("html_url"),
            clone_url=data.get("clone_url"),
            default_branch=data.get("default_branch", "main"),
            is_private=data.get("private", False),
            is_archived=data.get("archived", False),
            is_fork=data.get("fork", False),
            star_count=data.get("stargazers_count", 0),
            fork_count=data.get("forks_count", 0),
            open_issues_count=data.get("open_issues_count", 0),
            size_kb=data.get("size", 0),
            primary_language=data.get("language"),
            owner_id=str(owner.get("id")) if owner else None,
            owner_type=owner.get("type", "").lower() if owner else None,
        )

    def _normalize_developer(
        self,
        data: dict[str, Any],
        tenant_id: str,
        connection_id: str | None,
    ) -> Developer | None:
        """Normalize user/developer data."""
        if not data:
            return None

        return Developer(
            tenant_id=tenant_id,
            source=self.source,
            source_id=str(data.get("id")),
            connection_id=connection_id,
            username=data.get("login", ""),
            display_name=data.get("name"),
            email=data.get("email"),
            avatar_url=data.get("avatar_url"),
            is_bot=data.get("type", "").lower() == "bot",
        )

    def _normalize_push(
        self,
        payload: dict[str, Any],
        tenant_id: str,
        connection_id: str | None,
    ) -> list[Entity]:
        """Normalize push event to commit entities."""
        entities: list[Entity] = []
        repo = payload.get("repository", {})
        repo_id = str(repo.get("id")) if repo else None

        # Normalize each commit
        for commit_data in payload.get("commits", []):
            author = commit_data.get("author", {})
            committer = commit_data.get("committer", {})

            commit = Commit(
                tenant_id=tenant_id,
                source=self.source,
                source_id=commit_data.get("id", ""),
                connection_id=connection_id,
                source_created_at=self.parse_timestamp(commit_data.get("timestamp")),
                sha=commit_data.get("id", ""),
                message=commit_data.get("message", ""),
                short_message=commit_data.get("message", "").split("\n")[0][:80],
                author_name=author.get("name"),
                author_email=author.get("email"),
                committer_name=committer.get("name"),
                committer_email=committer.get("email"),
                repository_id=repo_id,
                branch=payload.get("ref", "").replace("refs/heads/", ""),
                additions=commit_data.get("added", 0) if isinstance(commit_data.get("added"), int) else len(commit_data.get("added", [])),
                deletions=commit_data.get("removed", 0) if isinstance(commit_data.get("removed"), int) else len(commit_data.get("removed", [])),
                files_changed=len(commit_data.get("modified", [])) + len(commit_data.get("added", [])) + len(commit_data.get("removed", [])),
                files=commit_data.get("modified", []) + commit_data.get("added", []) + commit_data.get("removed", []),
            )
            entities.append(commit)

        return entities

    def _normalize_pull_request(
        self,
        payload: dict[str, Any],
        tenant_id: str,
        connection_id: str | None,
    ) -> list[Entity]:
        """Normalize pull request event."""
        entities: list[Entity] = []
        pr_data = payload.get("pull_request", {})

        if not pr_data:
            return entities

        repo = payload.get("repository", {})
        repo_id = str(repo.get("id")) if repo else None

        user = pr_data.get("user", {})
        merged_by = pr_data.get("merged_by", {})

        # Map state
        state = pr_data.get("state", "open")
        merged = pr_data.get("merged", False)

        # Extract reviewers
        reviewer_ids = []
        for reviewer in pr_data.get("requested_reviewers", []):
            reviewer_ids.append(str(reviewer.get("id")))
            # Create developer entity for reviewer
            dev = self._normalize_developer(reviewer, tenant_id, connection_id)
            if dev:
                entities.append(dev)

        # Extract assignees
        assignee_ids = []
        for assignee in pr_data.get("assignees", []):
            assignee_ids.append(str(assignee.get("id")))
            dev = self._normalize_developer(assignee, tenant_id, connection_id)
            if dev:
                entities.append(dev)

        # Create PR author developer
        if user:
            dev = self._normalize_developer(user, tenant_id, connection_id)
            if dev:
                entities.append(dev)

        pr = PullRequest(
            tenant_id=tenant_id,
            source=self.source,
            source_id=str(pr_data.get("id")),
            connection_id=connection_id,
            source_created_at=self.parse_timestamp(pr_data.get("created_at")),
            source_updated_at=self.parse_timestamp(pr_data.get("updated_at")),
            number=pr_data.get("number", 0),
            title=pr_data.get("title", ""),
            body=pr_data.get("body"),
            url=pr_data.get("html_url"),
            state=state,
            is_draft=pr_data.get("draft", False),
            merged=merged,
            merged_at=self.parse_timestamp(pr_data.get("merged_at")),
            closed_at=self.parse_timestamp(pr_data.get("closed_at")),
            source_branch=pr_data.get("head", {}).get("ref"),
            target_branch=pr_data.get("base", {}).get("ref"),
            head_sha=pr_data.get("head", {}).get("sha"),
            base_sha=pr_data.get("base", {}).get("sha"),
            repository_id=repo_id,
            author_id=str(user.get("id")) if user else None,
            merged_by_id=str(merged_by.get("id")) if merged_by else None,
            assignee_ids=assignee_ids,
            reviewer_ids=reviewer_ids,
            additions=pr_data.get("additions", 0),
            deletions=pr_data.get("deletions", 0),
            files_changed=pr_data.get("changed_files", 0),
            commits_count=pr_data.get("commits", 0),
            comments_count=pr_data.get("comments", 0),
            review_comments_count=pr_data.get("review_comments", 0),
            labels=[l.get("name", "") for l in pr_data.get("labels", [])],
        )
        entities.append(pr)

        return entities

    def _normalize_ci(
        self,
        event_type: str,
        payload: dict[str, Any],
        tenant_id: str,
        connection_id: str | None,
    ) -> list[Entity]:
        """Normalize CI events (check_run, check_suite, workflow_run)."""
        entities: list[Entity] = []

        if event_type == "workflow_run":
            run = payload.get("workflow_run", {})
            if not run:
                return entities

            repo = payload.get("repository", {})

            # Map status
            status = run.get("status", "pending")
            conclusion = run.get("conclusion")

            build = Build(
                tenant_id=tenant_id,
                source=self.source,
                source_id=str(run.get("id")),
                connection_id=connection_id,
                source_created_at=self.parse_timestamp(run.get("created_at")),
                number=run.get("run_number", 0),
                name=run.get("name"),
                url=run.get("html_url"),
                status=status,
                conclusion=conclusion,
                started_at=self.parse_timestamp(run.get("run_started_at")),
                completed_at=self.parse_timestamp(run.get("updated_at")) if status == "completed" else None,
                trigger=run.get("event"),
                commit_sha=run.get("head_sha"),
                branch=run.get("head_branch"),
                repository_id=str(repo.get("id")) if repo else None,
            )
            entities.append(build)

        return entities

    def _normalize_deployment(
        self,
        event_type: str,
        payload: dict[str, Any],
        tenant_id: str,
        connection_id: str | None,
    ) -> list[Entity]:
        """Normalize deployment events."""
        entities: list[Entity] = []

        deploy_data = payload.get("deployment", {})
        status_data = payload.get("deployment_status", {})
        repo = payload.get("repository", {})

        if not deploy_data:
            return entities

        # Determine status
        if event_type == "deployment_status" and status_data:
            state = status_data.get("state", "pending")
            status_map = {
                "success": "success",
                "failure": "failed",
                "error": "failed",
                "pending": "pending",
                "in_progress": "in_progress",
            }
            status = status_map.get(state, "pending")
        else:
            status = "pending"

        creator = deploy_data.get("creator", {})

        deployment = Deployment(
            tenant_id=tenant_id,
            source=self.source,
            source_id=str(deploy_data.get("id")),
            connection_id=connection_id,
            source_created_at=self.parse_timestamp(deploy_data.get("created_at")),
            source_updated_at=self.parse_timestamp(deploy_data.get("updated_at")),
            url=deploy_data.get("url"),
            status=status,
            commit_sha=deploy_data.get("sha"),
            version=deploy_data.get("ref"),
            environment_name=deploy_data.get("environment"),
            repository_id=str(repo.get("id")) if repo else None,
            deployed_by_id=str(creator.get("id")) if creator else None,
        )
        entities.append(deployment)

        return entities

    def extract_entity_type(self, event_type: str) -> EntityType | None:
        """Map GitHub event type to entity type."""
        mapping = {
            "push": EntityType.COMMIT,
            "pull_request": EntityType.PULL_REQUEST,
            "check_run": EntityType.BUILD,
            "check_suite": EntityType.BUILD,
            "workflow_run": EntityType.BUILD,
            "deployment": EntityType.DEPLOYMENT,
            "deployment_status": EntityType.DEPLOYMENT,
            "issues": EntityType.ISSUE,
            "release": EntityType.RELEASE,
        }
        return mapping.get(event_type)
