"""Meilisearch integration for fast full-text search."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()


@dataclass
class SearchHit:
    """A search hit from Meilisearch."""

    id: str
    score: float | None = None
    highlights: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class MeilisearchResponse:
    """Response from Meilisearch query."""

    hits: list[SearchHit]
    query: str
    processing_time_ms: int
    total_hits: int
    page: int = 1
    hits_per_page: int = 20
    facets: dict[str, Any] = field(default_factory=dict)


class MeilisearchService:
    """Service for interacting with Meilisearch."""

    # Index names
    INDEX_CONVERSATIONS = "conversations"
    INDEX_MESSAGES = "messages"
    INDEX_DOCUMENTS = "documents"
    INDEX_AGENTS = "agents"

    def __init__(
        self,
        host: str | None = None,
        api_key: str | None = None,
    ):
        self.host = host or settings.MEILISEARCH_HOST
        self.api_key = api_key or settings.MEILISEARCH_API_KEY
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self._client = httpx.AsyncClient(
                base_url=self.host,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> bool:
        """Check if Meilisearch is healthy."""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.error("Meilisearch health check failed", error=str(e))
            return False

    async def create_index(
        self,
        index_name: str,
        primary_key: str = "id",
    ) -> bool:
        """Create an index."""
        try:
            client = await self._get_client()
            response = await client.post(
                "/indexes",
                json={"uid": index_name, "primaryKey": primary_key},
            )
            return response.status_code in (200, 201, 202)
        except Exception as e:
            logger.error("Failed to create index", index=index_name, error=str(e))
            return False

    async def configure_index(
        self,
        index_name: str,
        searchable_attributes: list[str] | None = None,
        filterable_attributes: list[str] | None = None,
        sortable_attributes: list[str] | None = None,
        ranking_rules: list[str] | None = None,
    ) -> bool:
        """Configure index settings."""
        try:
            client = await self._get_client()

            settings_payload: dict[str, Any] = {}

            if searchable_attributes:
                settings_payload["searchableAttributes"] = searchable_attributes

            if filterable_attributes:
                settings_payload["filterableAttributes"] = filterable_attributes

            if sortable_attributes:
                settings_payload["sortableAttributes"] = sortable_attributes

            if ranking_rules:
                settings_payload["rankingRules"] = ranking_rules

            response = await client.patch(
                f"/indexes/{index_name}/settings",
                json=settings_payload,
            )
            return response.status_code in (200, 202)
        except Exception as e:
            logger.error("Failed to configure index", index=index_name, error=str(e))
            return False

    async def add_documents(
        self,
        index_name: str,
        documents: list[dict[str, Any]],
        primary_key: str | None = None,
    ) -> str | None:
        """Add documents to an index. Returns task UID."""
        try:
            client = await self._get_client()

            url = f"/indexes/{index_name}/documents"
            if primary_key:
                url += f"?primaryKey={primary_key}"

            response = await client.post(url, json=documents)

            if response.status_code in (200, 202):
                return response.json().get("taskUid")

            return None
        except Exception as e:
            logger.error("Failed to add documents", index=index_name, error=str(e))
            return None

    async def update_document(
        self,
        index_name: str,
        document: dict[str, Any],
    ) -> str | None:
        """Update a single document."""
        return await self.add_documents(index_name, [document])

    async def delete_document(
        self,
        index_name: str,
        document_id: str,
    ) -> bool:
        """Delete a document by ID."""
        try:
            client = await self._get_client()
            response = await client.delete(
                f"/indexes/{index_name}/documents/{document_id}"
            )
            return response.status_code in (200, 202)
        except Exception as e:
            logger.error("Failed to delete document", index=index_name, error=str(e))
            return False

    async def delete_documents(
        self,
        index_name: str,
        document_ids: list[str],
    ) -> bool:
        """Delete multiple documents by IDs."""
        try:
            client = await self._get_client()
            response = await client.post(
                f"/indexes/{index_name}/documents/delete-batch",
                json=document_ids,
            )
            return response.status_code in (200, 202)
        except Exception as e:
            logger.error("Failed to delete documents", index=index_name, error=str(e))
            return False

    async def search(
        self,
        index_name: str,
        query: str,
        filter: str | None = None,
        sort: list[str] | None = None,
        page: int = 1,
        hits_per_page: int = 20,
        attributes_to_retrieve: list[str] | None = None,
        attributes_to_highlight: list[str] | None = None,
        facets: list[str] | None = None,
    ) -> MeilisearchResponse:
        """Search an index."""
        try:
            client = await self._get_client()

            payload: dict[str, Any] = {
                "q": query,
                "page": page,
                "hitsPerPage": hits_per_page,
            }

            if filter:
                payload["filter"] = filter

            if sort:
                payload["sort"] = sort

            if attributes_to_retrieve:
                payload["attributesToRetrieve"] = attributes_to_retrieve

            if attributes_to_highlight:
                payload["attributesToHighlight"] = attributes_to_highlight

            if facets:
                payload["facets"] = facets

            response = await client.post(
                f"/indexes/{index_name}/search",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            hits = [
                SearchHit(
                    id=hit.get("id", ""),
                    score=hit.get("_rankingScore"),
                    highlights=hit.get("_formatted", {}),
                    data=hit,
                )
                for hit in data.get("hits", [])
            ]

            return MeilisearchResponse(
                hits=hits,
                query=query,
                processing_time_ms=data.get("processingTimeMs", 0),
                total_hits=data.get("totalHits", len(hits)),
                page=page,
                hits_per_page=hits_per_page,
                facets=data.get("facetDistribution", {}),
            )

        except Exception as e:
            logger.error("Search failed", index=index_name, error=str(e))
            return MeilisearchResponse(
                hits=[],
                query=query,
                processing_time_ms=0,
                total_hits=0,
            )

    async def multi_search(
        self,
        queries: list[dict[str, Any]],
    ) -> list[MeilisearchResponse]:
        """Execute multiple searches in one request."""
        try:
            client = await self._get_client()

            response = await client.post(
                "/multi-search",
                json={"queries": queries},
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for result in data.get("results", []):
                hits = [
                    SearchHit(
                        id=hit.get("id", ""),
                        score=hit.get("_rankingScore"),
                        highlights=hit.get("_formatted", {}),
                        data=hit,
                    )
                    for hit in result.get("hits", [])
                ]

                results.append(MeilisearchResponse(
                    hits=hits,
                    query=result.get("query", ""),
                    processing_time_ms=result.get("processingTimeMs", 0),
                    total_hits=result.get("totalHits", len(hits)),
                ))

            return results

        except Exception as e:
            logger.error("Multi-search failed", error=str(e))
            return []

    async def get_task(self, task_uid: str) -> dict[str, Any] | None:
        """Get task status."""
        try:
            client = await self._get_client()
            response = await client.get(f"/tasks/{task_uid}")

            if response.status_code == 200:
                return response.json()

            return None
        except Exception as e:
            logger.error("Failed to get task", task_uid=task_uid, error=str(e))
            return None

    async def wait_for_task(
        self,
        task_uid: str,
        timeout_seconds: int = 60,
    ) -> bool:
        """Wait for a task to complete."""
        import asyncio

        for _ in range(timeout_seconds):
            task = await self.get_task(task_uid)

            if task:
                status = task.get("status")

                if status == "succeeded":
                    return True
                elif status in ("failed", "canceled"):
                    logger.error("Task failed", task_uid=task_uid, status=status)
                    return False

            await asyncio.sleep(1)

        return False

    # High-level methods for specific indexes

    async def index_conversation(
        self,
        conversation_id: str,
        user_id: str,
        title: str,
        messages_preview: str,
        created_at: datetime,
        updated_at: datetime,
        tags: list[str] | None = None,
    ) -> str | None:
        """Index a conversation for search."""
        document = {
            "id": conversation_id,
            "user_id": user_id,
            "title": title,
            "messages_preview": messages_preview,
            "created_at": created_at.timestamp(),
            "updated_at": updated_at.timestamp(),
            "tags": tags or [],
        }

        return await self.add_documents(self.INDEX_CONVERSATIONS, [document])

    async def index_message(
        self,
        message_id: str,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        created_at: datetime,
    ) -> str | None:
        """Index a message for search."""
        document = {
            "id": message_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "created_at": created_at.timestamp(),
        }

        return await self.add_documents(self.INDEX_MESSAGES, [document])

    async def search_conversations(
        self,
        user_id: str,
        query: str,
        page: int = 1,
        hits_per_page: int = 20,
    ) -> MeilisearchResponse:
        """Search user's conversations."""
        return await self.search(
            index_name=self.INDEX_CONVERSATIONS,
            query=query,
            filter=f"user_id = '{user_id}'",
            sort=["updated_at:desc"],
            page=page,
            hits_per_page=hits_per_page,
            attributes_to_highlight=["title", "messages_preview"],
        )

    async def search_messages(
        self,
        user_id: str,
        query: str,
        conversation_id: str | None = None,
        page: int = 1,
        hits_per_page: int = 20,
    ) -> MeilisearchResponse:
        """Search messages."""
        filter_parts = [f"user_id = '{user_id}'"]

        if conversation_id:
            filter_parts.append(f"conversation_id = '{conversation_id}'")

        return await self.search(
            index_name=self.INDEX_MESSAGES,
            query=query,
            filter=" AND ".join(filter_parts),
            sort=["created_at:desc"],
            page=page,
            hits_per_page=hits_per_page,
            attributes_to_highlight=["content"],
        )

    async def setup_indexes(self) -> bool:
        """Set up all indexes with proper configuration."""
        success = True

        # Conversations index
        if await self.create_index(self.INDEX_CONVERSATIONS):
            await self.configure_index(
                self.INDEX_CONVERSATIONS,
                searchable_attributes=["title", "messages_preview", "tags"],
                filterable_attributes=["user_id", "tags", "created_at", "updated_at"],
                sortable_attributes=["created_at", "updated_at"],
            )
        else:
            success = False

        # Messages index
        if await self.create_index(self.INDEX_MESSAGES):
            await self.configure_index(
                self.INDEX_MESSAGES,
                searchable_attributes=["content"],
                filterable_attributes=["user_id", "conversation_id", "role", "created_at"],
                sortable_attributes=["created_at"],
            )
        else:
            success = False

        # Documents index
        if await self.create_index(self.INDEX_DOCUMENTS):
            await self.configure_index(
                self.INDEX_DOCUMENTS,
                searchable_attributes=["title", "content", "summary", "tags"],
                filterable_attributes=["user_id", "organization_id", "document_type", "created_at"],
                sortable_attributes=["created_at", "updated_at"],
            )
        else:
            success = False

        # Agents index
        if await self.create_index(self.INDEX_AGENTS):
            await self.configure_index(
                self.INDEX_AGENTS,
                searchable_attributes=["name", "description", "tags"],
                filterable_attributes=["creator_id", "is_public", "marketplace_category", "status"],
                sortable_attributes=["usage_count", "rating", "created_at"],
            )
        else:
            success = False

        return success


# Global service instance
meilisearch_service = MeilisearchService()
