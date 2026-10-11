"""OpenFGA integration for fine-grained authorization (ReBAC).

OpenFGA provides Relationship-Based Access Control (ReBAC) enabling:
- Fine-grained permissions at object level
- Relationship-based authorization (like Google Zanzibar)
- Team and organizational hierarchy support
- Dynamic permission evaluation

This integrates with the multi-tenant architecture.
"""

from enum import Enum
from typing import Any

import httpx
import structlog
from pydantic import BaseModel

from app.core.config import settings

logger = structlog.get_logger()


class Relation(str, Enum):
    """Standard relations for authorization."""

    # Organization relations
    ORG_OWNER = "owner"
    ORG_ADMIN = "admin"
    ORG_MEMBER = "member"
    ORG_VIEWER = "viewer"

    # Project relations
    PROJECT_ADMIN = "admin"
    PROJECT_MAINTAINER = "maintainer"
    PROJECT_DEVELOPER = "developer"
    PROJECT_VIEWER = "viewer"

    # Resource relations
    CAN_VIEW = "can_view"
    CAN_EDIT = "can_edit"
    CAN_DELETE = "can_delete"
    CAN_MANAGE = "can_manage"


class AuthorizationTuple(BaseModel):
    """OpenFGA authorization tuple."""

    user: str  # e.g., "user:alice" or "organization:org1#member"
    relation: str  # e.g., "owner", "viewer"
    object: str  # e.g., "project:project1"
    condition: dict[str, Any] | None = None


class OpenFGAClient:
    """Client for OpenFGA authorization service."""

    def __init__(self):
        self.base_url = settings.OPENFGA_URL
        self.store_id = settings.OPENFGA_STORE_ID
        self.model_id = settings.OPENFGA_MODEL_ID
        self.timeout = 10.0
        self._available: bool | None = None

    @property
    def _headers(self) -> dict[str, str]:
        """Get headers for OpenFGA requests."""
        return {"Content-Type": "application/json"}

    async def is_available(self) -> bool:
        """Check if OpenFGA is available."""
        if self._available is not None:
            return self._available

        if not self.base_url or not self.store_id:
            self._available = False
            return False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/stores/{self.store_id}",
                    headers=self._headers,
                )
                self._available = response.status_code == 200
                return self._available
        except Exception as e:
            logger.warning("OpenFGA health check failed", error=str(e))
            self._available = False
            return False

    async def check(
        self,
        user: str,
        relation: str,
        object: str,
        contextual_tuples: list[AuthorizationTuple] | None = None,
    ) -> bool:
        """Check if a user has a relation to an object.

        Args:
            user: The user identifier (e.g., "user:alice")
            relation: The relation to check (e.g., "can_view")
            object: The object identifier (e.g., "project:project1")
            contextual_tuples: Additional tuples for the check

        Returns:
            True if the user has the relation
        """
        if not await self.is_available():
            # Fallback to simple role-based check
            return await self._fallback_check(user, relation, object)

        body: dict[str, Any] = {
            "tuple_key": {
                "user": user,
                "relation": relation,
                "object": object,
            },
        }

        if self.model_id:
            body["authorization_model_id"] = self.model_id

        if contextual_tuples:
            body["contextual_tuples"] = {
                "tuple_keys": [
                    {"user": t.user, "relation": t.relation, "object": t.object}
                    for t in contextual_tuples
                ]
            }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/stores/{self.store_id}/check",
                headers=self._headers,
                json=body,
            )
            response.raise_for_status()
            return response.json().get("allowed", False)

    async def write(
        self,
        writes: list[AuthorizationTuple] | None = None,
        deletes: list[AuthorizationTuple] | None = None,
    ) -> bool:
        """Write or delete authorization tuples.

        Args:
            writes: Tuples to add
            deletes: Tuples to remove

        Returns:
            True if successful
        """
        if not await self.is_available():
            return await self._fallback_write(writes, deletes)

        body: dict[str, Any] = {}

        if self.model_id:
            body["authorization_model_id"] = self.model_id

        if writes:
            body["writes"] = {
                "tuple_keys": [
                    {"user": t.user, "relation": t.relation, "object": t.object}
                    for t in writes
                ]
            }

        if deletes:
            body["deletes"] = {
                "tuple_keys": [
                    {"user": t.user, "relation": t.relation, "object": t.object}
                    for t in deletes
                ]
            }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/stores/{self.store_id}/write",
                headers=self._headers,
                json=body,
            )
            return response.status_code == 200

    async def list_objects(
        self,
        user: str,
        relation: str,
        type: str,
    ) -> list[str]:
        """List all objects of a type that a user has a relation to.

        Args:
            user: The user identifier
            relation: The relation to check
            type: The object type (e.g., "project")

        Returns:
            List of object IDs
        """
        if not await self.is_available():
            return await self._fallback_list_objects(user, relation, type)

        body: dict[str, Any] = {
            "user": user,
            "relation": relation,
            "type": type,
        }

        if self.model_id:
            body["authorization_model_id"] = self.model_id

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/stores/{self.store_id}/list-objects",
                headers=self._headers,
                json=body,
            )
            response.raise_for_status()
            return response.json().get("objects", [])

    async def list_users(
        self,
        relation: str,
        object: str,
        user_type: str = "user",
    ) -> list[str]:
        """List all users that have a relation to an object.

        Args:
            relation: The relation to check
            object: The object identifier
            user_type: The type of users to list

        Returns:
            List of user IDs
        """
        if not await self.is_available():
            return await self._fallback_list_users(relation, object, user_type)

        body: dict[str, Any] = {
            "object": object,
            "relation": relation,
            "user_filters": [{"type": user_type}],
        }

        if self.model_id:
            body["authorization_model_id"] = self.model_id

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/stores/{self.store_id}/list-users",
                headers=self._headers,
                json=body,
            )
            response.raise_for_status()
            users = response.json().get("users", [])
            return [u.get("object", {}).get("id") for u in users if u.get("object")]

    # Fallback implementations for when OpenFGA is not available
    _local_tuples: list[AuthorizationTuple] = []

    async def _fallback_check(self, user: str, relation: str, object: str) -> bool:
        """Simple fallback check using local tuples."""
        for t in self._local_tuples:
            if t.user == user and t.relation == relation and t.object == object:
                return True
        return False

    async def _fallback_write(
        self,
        writes: list[AuthorizationTuple] | None,
        deletes: list[AuthorizationTuple] | None,
    ) -> bool:
        """Fallback write to local tuples."""
        if deletes:
            self._local_tuples = [
                t for t in self._local_tuples
                if not any(
                    t.user == d.user and t.relation == d.relation and t.object == d.object
                    for d in deletes
                )
            ]
        if writes:
            self._local_tuples.extend(writes)
        return True

    async def _fallback_list_objects(
        self,
        user: str,
        relation: str,
        type: str,
    ) -> list[str]:
        """Fallback list objects from local tuples."""
        return [
            t.object for t in self._local_tuples
            if t.user == user and t.relation == relation and t.object.startswith(f"{type}:")
        ]

    async def _fallback_list_users(
        self,
        relation: str,
        object: str,
        user_type: str,
    ) -> list[str]:
        """Fallback list users from local tuples."""
        return [
            t.user.split(":", 1)[1] if ":" in t.user else t.user
            for t in self._local_tuples
            if t.relation == relation and t.object == object and t.user.startswith(f"{user_type}:")
        ]


# Singleton instance
openfga_client = OpenFGAClient()


# Convenience functions for common authorization patterns
async def grant_org_membership(
    user_id: str,
    org_id: str,
    role: str = "member",
) -> bool:
    """Grant organization membership to a user."""
    return await openfga_client.write(
        writes=[
            AuthorizationTuple(
                user=f"user:{user_id}",
                relation=role,
                object=f"organization:{org_id}",
            )
        ]
    )


async def revoke_org_membership(
    user_id: str,
    org_id: str,
    role: str = "member",
) -> bool:
    """Revoke organization membership from a user."""
    return await openfga_client.write(
        deletes=[
            AuthorizationTuple(
                user=f"user:{user_id}",
                relation=role,
                object=f"organization:{org_id}",
            )
        ]
    )


async def grant_project_access(
    user_id: str,
    project_id: str,
    role: str = "developer",
) -> bool:
    """Grant project access to a user."""
    return await openfga_client.write(
        writes=[
            AuthorizationTuple(
                user=f"user:{user_id}",
                relation=role,
                object=f"project:{project_id}",
            )
        ]
    )


async def can_view_project(user_id: str, project_id: str) -> bool:
    """Check if user can view a project."""
    return await openfga_client.check(
        user=f"user:{user_id}",
        relation="can_view",
        object=f"project:{project_id}",
    )


async def can_edit_project(user_id: str, project_id: str) -> bool:
    """Check if user can edit a project."""
    return await openfga_client.check(
        user=f"user:{user_id}",
        relation="can_edit",
        object=f"project:{project_id}",
    )


async def can_manage_connection(user_id: str, connection_id: str) -> bool:
    """Check if user can manage a connection."""
    return await openfga_client.check(
        user=f"user:{user_id}",
        relation="can_manage",
        object=f"connection:{connection_id}",
    )


async def get_user_organizations(user_id: str) -> list[str]:
    """Get all organizations a user is a member of."""
    return await openfga_client.list_objects(
        user=f"user:{user_id}",
        relation="member",
        type="organization",
    )


async def get_user_projects(user_id: str) -> list[str]:
    """Get all projects a user has access to."""
    return await openfga_client.list_objects(
        user=f"user:{user_id}",
        relation="can_view",
        type="project",
    )


# OpenFGA Authorization Model (for reference)
OPENFGA_MODEL = """
model
  schema 1.1

type user

type organization
  relations
    define owner: [user]
    define admin: [user] or owner
    define member: [user] or admin
    define viewer: [user] or member
    define can_manage: admin or owner
    define can_edit: member
    define can_view: viewer

type project
  relations
    define organization: [organization]
    define admin: [user] or admin from organization
    define maintainer: [user] or admin
    define developer: [user] or maintainer
    define viewer: [user] or developer
    define can_manage: admin
    define can_edit: developer
    define can_view: viewer

type connection
  relations
    define project: [project]
    define can_manage: can_manage from project
    define can_view: can_view from project

type document
  relations
    define owner: [user]
    define organization: [organization]
    define can_manage: owner or can_manage from organization
    define can_edit: owner or can_edit from organization
    define can_view: can_edit or can_view from organization
"""
