"""Annotation Service for Real-time Collaboration."""

import uuid
from datetime import datetime
from typing import Any

from app.services.collaboration.models import (
    AnnotationType,
    CodeAnnotation,
)


class AnnotationService:
    """Service for managing code annotations."""

    def __init__(self):
        # In-memory storage - replace with database in production
        self._annotations: dict[str, CodeAnnotation] = {}
        self._file_annotations: dict[str, set[str]] = {}  # file_key -> annotation_ids
        self._user_annotations: dict[str, set[str]] = {}  # user_id -> annotation_ids

    def _get_file_key(self, organization_id: str, project_id: str, file_path: str) -> str:
        """Generate a unique key for a file."""
        return f"{organization_id}:{project_id}:{file_path}"

    async def create_annotation(
        self,
        organization_id: str,
        project_id: str,
        file_path: str,
        start_line: int,
        end_line: int,
        annotation_type: AnnotationType,
        content: str,
        author_id: str,
        author_username: str,
        title: str | None = None,
        start_column: int | None = None,
        end_column: int | None = None,
        code_snippet: str | None = None,
        mentions: list[str] | None = None,
        commit_sha: str | None = None,
        branch: str | None = None,
        parent_id: str | None = None,
    ) -> CodeAnnotation:
        """Create a new code annotation."""
        annotation_id = str(uuid.uuid4())
        now = datetime.utcnow()

        annotation = CodeAnnotation(
            id=annotation_id,
            organization_id=organization_id,
            project_id=project_id,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            start_column=start_column,
            end_column=end_column,
            annotation_type=annotation_type,
            title=title,
            content=content,
            code_snippet=code_snippet,
            author_id=author_id,
            author_username=author_username,
            mentions=mentions or [],
            resolved=False,
            parent_id=parent_id,
            reply_count=0,
            created_at=now,
            updated_at=now,
            commit_sha=commit_sha,
            branch=branch,
        )

        self._annotations[annotation_id] = annotation

        # Index by file
        file_key = self._get_file_key(organization_id, project_id, file_path)
        if file_key not in self._file_annotations:
            self._file_annotations[file_key] = set()
        self._file_annotations[file_key].add(annotation_id)

        # Index by user
        if author_id not in self._user_annotations:
            self._user_annotations[author_id] = set()
        self._user_annotations[author_id].add(annotation_id)

        # Update parent reply count if this is a reply
        if parent_id and parent_id in self._annotations:
            self._annotations[parent_id].reply_count += 1

        return annotation

    async def get_annotation(self, annotation_id: str) -> CodeAnnotation | None:
        """Get an annotation by ID."""
        return self._annotations.get(annotation_id)

    async def update_annotation(
        self,
        annotation_id: str,
        user_id: str,
        content: str | None = None,
        title: str | None = None,
        annotation_type: AnnotationType | None = None,
        mentions: list[str] | None = None,
    ) -> CodeAnnotation | None:
        """Update an annotation (author only)."""
        annotation = self._annotations.get(annotation_id)
        if not annotation:
            return None

        # Only author can update
        if annotation.author_id != user_id:
            return None

        if content is not None:
            annotation.content = content
        if title is not None:
            annotation.title = title
        if annotation_type is not None:
            annotation.annotation_type = annotation_type
        if mentions is not None:
            annotation.mentions = mentions

        annotation.updated_at = datetime.utcnow()

        return annotation

    async def delete_annotation(
        self,
        annotation_id: str,
        user_id: str,
    ) -> bool:
        """Delete an annotation (author only)."""
        annotation = self._annotations.get(annotation_id)
        if not annotation:
            return False

        # Only author can delete
        if annotation.author_id != user_id:
            return False

        # Remove from indices
        file_key = self._get_file_key(
            annotation.organization_id,
            annotation.project_id,
            annotation.file_path,
        )
        if file_key in self._file_annotations:
            self._file_annotations[file_key].discard(annotation_id)

        if annotation.author_id in self._user_annotations:
            self._user_annotations[annotation.author_id].discard(annotation_id)

        # Update parent reply count if this is a reply
        if annotation.parent_id and annotation.parent_id in self._annotations:
            self._annotations[annotation.parent_id].reply_count -= 1

        # Delete annotation
        del self._annotations[annotation_id]

        return True

    async def resolve_annotation(
        self,
        annotation_id: str,
        resolved_by: str,
    ) -> CodeAnnotation | None:
        """Mark an annotation as resolved."""
        annotation = self._annotations.get(annotation_id)
        if not annotation:
            return None

        annotation.resolved = True
        annotation.resolved_by = resolved_by
        annotation.resolved_at = datetime.utcnow()
        annotation.updated_at = datetime.utcnow()

        return annotation

    async def unresolve_annotation(
        self,
        annotation_id: str,
    ) -> CodeAnnotation | None:
        """Mark an annotation as unresolved."""
        annotation = self._annotations.get(annotation_id)
        if not annotation:
            return None

        annotation.resolved = False
        annotation.resolved_by = None
        annotation.resolved_at = None
        annotation.updated_at = datetime.utcnow()

        return annotation

    async def list_annotations(
        self,
        organization_id: str | None = None,
        project_id: str | None = None,
        file_path: str | None = None,
        annotation_type: AnnotationType | None = None,
        author_id: str | None = None,
        resolved: bool | None = None,
        branch: str | None = None,
        parent_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CodeAnnotation]:
        """List annotations with optional filters."""
        annotations = []

        # If file is specified, use file index
        if organization_id and project_id and file_path:
            file_key = self._get_file_key(organization_id, project_id, file_path)
            annotation_ids = self._file_annotations.get(file_key, set())
            for aid in annotation_ids:
                annotation = self._annotations.get(aid)
                if annotation:
                    annotations.append(annotation)
        # If author is specified, use user index
        elif author_id:
            annotation_ids = self._user_annotations.get(author_id, set())
            for aid in annotation_ids:
                annotation = self._annotations.get(aid)
                if annotation:
                    annotations.append(annotation)
        else:
            annotations = list(self._annotations.values())

        # Apply filters
        filtered = []
        for annotation in annotations:
            if organization_id and annotation.organization_id != organization_id:
                continue
            if project_id and annotation.project_id != project_id:
                continue
            if annotation_type and annotation.annotation_type != annotation_type:
                continue
            if author_id and annotation.author_id != author_id:
                continue
            if resolved is not None and annotation.resolved != resolved:
                continue
            if branch and annotation.branch != branch:
                continue
            if parent_id is not None:
                if parent_id == "" and annotation.parent_id is not None:
                    continue  # Only top-level
                elif parent_id and annotation.parent_id != parent_id:
                    continue  # Only replies to specific annotation
            filtered.append(annotation)

        # Sort by line number, then by created_at
        filtered.sort(key=lambda a: (a.start_line, a.created_at))

        # Apply pagination
        return filtered[offset:offset + limit]

    async def get_replies(
        self,
        annotation_id: str,
    ) -> list[CodeAnnotation]:
        """Get all replies to an annotation."""
        replies = [
            a for a in self._annotations.values()
            if a.parent_id == annotation_id
        ]
        replies.sort(key=lambda a: a.created_at)
        return replies

    async def get_file_annotation_count(
        self,
        organization_id: str,
        project_id: str,
        file_path: str,
        resolved: bool | None = None,
    ) -> int:
        """Get count of annotations for a file."""
        file_key = self._get_file_key(organization_id, project_id, file_path)
        annotation_ids = self._file_annotations.get(file_key, set())

        if resolved is None:
            return len(annotation_ids)

        count = 0
        for aid in annotation_ids:
            annotation = self._annotations.get(aid)
            if annotation and annotation.resolved == resolved:
                count += 1
        return count

    async def get_annotations_in_range(
        self,
        organization_id: str,
        project_id: str,
        file_path: str,
        start_line: int,
        end_line: int,
    ) -> list[CodeAnnotation]:
        """Get annotations that overlap with a line range."""
        file_key = self._get_file_key(organization_id, project_id, file_path)
        annotation_ids = self._file_annotations.get(file_key, set())

        annotations = []
        for aid in annotation_ids:
            annotation = self._annotations.get(aid)
            if not annotation:
                continue

            # Check if annotation overlaps with the range
            if annotation.end_line >= start_line and annotation.start_line <= end_line:
                annotations.append(annotation)

        annotations.sort(key=lambda a: a.start_line)
        return annotations

    async def get_user_mentions(
        self,
        user_id: str,
        unresolved_only: bool = True,
    ) -> list[CodeAnnotation]:
        """Get all annotations where the user is mentioned."""
        mentions = []
        for annotation in self._annotations.values():
            if user_id in annotation.mentions:
                if unresolved_only and annotation.resolved:
                    continue
                mentions.append(annotation)

        mentions.sort(key=lambda a: a.created_at, reverse=True)
        return mentions

    async def bulk_update_file_path(
        self,
        organization_id: str,
        project_id: str,
        old_path: str,
        new_path: str,
    ) -> int:
        """Update file path for all annotations (for file renames)."""
        old_key = self._get_file_key(organization_id, project_id, old_path)
        new_key = self._get_file_key(organization_id, project_id, new_path)

        annotation_ids = self._file_annotations.get(old_key, set()).copy()
        updated_count = 0

        for aid in annotation_ids:
            annotation = self._annotations.get(aid)
            if annotation:
                annotation.file_path = new_path
                annotation.updated_at = datetime.utcnow()
                updated_count += 1

        # Update index
        if old_key in self._file_annotations:
            self._file_annotations[new_key] = self._file_annotations.pop(old_key)

        return updated_count

    async def get_annotation_summary(
        self,
        organization_id: str,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Get annotation statistics."""
        total = 0
        by_type: dict[str, int] = {}
        by_status = {"resolved": 0, "unresolved": 0}
        by_file: dict[str, int] = {}

        for annotation in self._annotations.values():
            if annotation.organization_id != organization_id:
                continue
            if project_id and annotation.project_id != project_id:
                continue
            if annotation.parent_id:  # Skip replies in counts
                continue

            total += 1

            type_key = annotation.annotation_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

            if annotation.resolved:
                by_status["resolved"] += 1
            else:
                by_status["unresolved"] += 1

            by_file[annotation.file_path] = by_file.get(annotation.file_path, 0) + 1

        return {
            "total": total,
            "by_type": by_type,
            "by_status": by_status,
            "files_with_annotations": len(by_file),
            "top_files": sorted(
                by_file.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10],
        }


# Singleton instance
_annotation_service: AnnotationService | None = None


def get_annotation_service() -> AnnotationService:
    """Get the annotation service singleton."""
    global _annotation_service
    if _annotation_service is None:
        _annotation_service = AnnotationService()
    return _annotation_service
