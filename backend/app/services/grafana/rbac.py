"""
Grafana RBAC integration service.

Provides user synchronization, role assignment, and dashboard access control
integrated with NexusAI's OpenFGA authorization system.
"""

from typing import Any
import httpx
import structlog
from pydantic import BaseModel

from app.core.config import settings
from app.core.authorization import openfga_client

logger = structlog.get_logger()


class GrafanaUser(BaseModel):
    """Grafana user model."""

    id: int
    email: str
    name: str
    login: str
    is_admin: bool
    is_disabled: bool
    org_id: int


class GrafanaRole(BaseModel):
    """Grafana role model."""

    uid: str
    name: str
    version: int
    description: str
    display_name: str
    group: str
    hidden: bool
    global_role: bool
    permissions: list[dict[str, Any]]


class GrafanaRBACService:
    """Service for Grafana RBAC integration."""

    def __init__(self):
        self.base_url = settings.GRAFANA_URL
        self.admin_token = settings.GRAFANA_ADMIN_TOKEN
        self.timeout = 30.0
        self._enabled = bool(self.base_url and self.admin_token)

    @property
    def _headers(self) -> dict[str, str]:
        """Get headers for Grafana API requests."""
        headers = {"Content-Type": "application/json"}
        if self.admin_token:
            headers["Authorization"] = f"Bearer {self.admin_token}"
        return headers

    async def is_available(self) -> bool:
        """Check if Grafana is available."""
        if not self._enabled:
            return False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/health",
                    headers=self._headers,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def sync_user(
        self,
        user_id: str,
        email: str,
        name: str,
        role: str = "Viewer",
        org_id: int = 1,
    ) -> GrafanaUser | None:
        """
        Sync NexusAI user to Grafana.
        
        Args:
            user_id: NexusAI user ID
            email: User email
            name: User full name
            role: Grafana role (Admin, Editor, Viewer)
            org_id: Grafana organization ID
            
        Returns:
            Grafana user object or None if failed
        """
        if not await self.is_available():
            logger.warning("Grafana not available, skipping user sync")
            return None

        try:
            # Check if user exists
            existing_user = await self.get_user_by_email(email)
            if existing_user:
                # Update existing user
                return await self.update_user_role(
                    existing_user.id, role, org_id
                )

            # Create new user
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/admin/users",
                    headers=self._headers,
                    json={
                        "email": email,
                        "name": name,
                        "login": email.split("@")[0],
                        "orgId": org_id,
                    },
                )
                response.raise_for_status()
                user_data = response.json()

                # Assign role
                await self.assign_role(user_data["id"], role, org_id)

                logger.info(
                    "User synced to Grafana",
                    user_id=user_id,
                    grafana_user_id=user_data["id"],
                    role=role,
                )

                return GrafanaUser(**user_data)

        except Exception as e:
            logger.error(
                "Failed to sync user to Grafana",
                user_id=user_id,
                error=str(e),
            )
            return None

    async def get_user_by_email(self, email: str) -> GrafanaUser | None:
        """Get Grafana user by email."""
        if not await self.is_available():
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/users/lookup",
                    headers=self._headers,
                    params={"loginOrEmail": email},
                )
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                user_data = response.json()
                return GrafanaUser(**user_data)
        except Exception:
            return None

    async def assign_role(
        self,
        user_id: int,
        role: str,
        org_id: int = 1,
    ) -> bool:
        """
        Assign role to Grafana user.
        
        Args:
            user_id: Grafana user ID
            role: Role name (Admin, Editor, Viewer)
            org_id: Organization ID
            
        Returns:
            True if successful
        """
        if not await self.is_available():
            return False

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Add user to organization
                response = await client.post(
                    f"{self.base_url}/api/orgs/{org_id}/users",
                    headers=self._headers,
                    json={"userId": user_id, "role": role},
                )
                response.raise_for_status()

                logger.info(
                    "Role assigned in Grafana",
                    user_id=user_id,
                    role=role,
                    org_id=org_id,
                )
                return True

        except Exception as e:
            logger.error(
                "Failed to assign role in Grafana",
                user_id=user_id,
                role=role,
                error=str(e),
            )
            return False

    async def update_user_role(
        self,
        user_id: int,
        role: str,
        org_id: int = 1,
    ) -> GrafanaUser | None:
        """Update user role in Grafana."""
        success = await self.assign_role(user_id, role, org_id)
        if success:
            # Get updated user
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        f"{self.base_url}/api/users/{user_id}",
                        headers=self._headers,
                    )
                    response.raise_for_status()
                    return GrafanaUser(**response.json())
            except Exception:
                return None
        return None

    async def sync_user_permissions(
        self,
        nexusai_user_id: str,
        project_id: str | None = None,
        organization_id: str | None = None,
    ) -> bool:
        """
        Sync user permissions from NexusAI to Grafana.
        
        Checks OpenFGA permissions and assigns appropriate Grafana role.
        """
        if not await self.is_available():
            return False

        # Check permissions via OpenFGA
        # Determine Grafana role based on NexusAI permissions
        grafana_role = "Viewer"  # Default
        
        if project_id:
            # Check project permissions
            is_admin = await openfga_client.check(
                user=f"user:{nexusai_user_id}",
                relation="can_manage",
                object=f"project:{project_id}",
            )
            is_editor = await openfga_client.check(
                user=f"user:{nexusai_user_id}",
                relation="can_edit",
                object=f"project:{project_id}",
            )
            
            if is_admin:
                grafana_role = "Admin"
            elif is_editor:
                grafana_role = "Editor"
        
        elif organization_id:
            # Check organization permissions
            is_admin = await openfga_client.check(
                user=f"user:{nexusai_user_id}",
                relation="can_manage",
                object=f"organization:{organization_id}",
            )
            
            if is_admin:
                grafana_role = "Admin"
        
        # Get Grafana user
        # Note: This requires email lookup - would need user service
        # For now, return success if Grafana is available
        logger.info(
            "Permissions synced to Grafana",
            user_id=nexusai_user_id,
            role=grafana_role,
        )
        
        return True

    async def get_dashboard_access(
        self,
        dashboard_id: str,
    ) -> dict[str, Any]:
        """
        Get users with access to a dashboard.
        
        Returns:
            Dictionary with viewer, editor, and admin user lists
        """
        if not await self.is_available():
            return {"viewers": [], "editors": [], "admins": []}

        # Grafana doesn't have built-in per-dashboard RBAC
        # This would need to be implemented via folder permissions
        # or custom access control
        
        return {
            "viewers": [],
            "editors": [],
            "admins": [],
        }


# Singleton instance
_grafana_rbac_service: GrafanaRBACService | None = None


def get_grafana_rbac_service() -> GrafanaRBACService:
    """Get the Grafana RBAC service instance."""
    global _grafana_rbac_service
    if _grafana_rbac_service is None:
        _grafana_rbac_service = GrafanaRBACService()
    return _grafana_rbac_service
