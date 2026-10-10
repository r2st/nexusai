"""
Jira Connector

Connector for Atlassian Jira issue tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import hashlib
import hmac
import logging

import httpx

from .base import BaseConnector, ConnectorConfig, ConnectorStatus, DEFAULT_HTTP_TIMEOUT, WebhookEvent

logger = logging.getLogger(__name__)


@dataclass
class JiraConfig(ConnectorConfig):
    """Jira-specific configuration."""
    # Jira instance
    instance_url: str = ""  # e.g., https://company.atlassian.net
    cloud: bool = True  # Jira Cloud vs Server
    
    # Authentication
    email: str = ""
    api_token: str = ""
    
    # OAuth (for Jira Cloud)
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_access_token: str = ""
    oauth_refresh_token: str = ""
    
    # Webhook
    webhook_secret: str = ""
    
    # Sync settings
    projects: List[str] = field(default_factory=list)  # Empty = all projects
    issue_types: List[str] = field(default_factory=list)  # Empty = all types
    sync_comments: bool = True
    sync_attachments: bool = False
    sync_worklogs: bool = False


class JiraConnector(BaseConnector):
    """
    Jira connector for issue tracking integration.
    
    Features:
    - Issue sync (create, update, transitions)
    - Comment sync
    - Sprint/board data
    - Webhook events
    - JQL queries
    """
    
    name = "jira"
    display_name = "Jira"
    
    def __init__(self, config: JiraConfig):
        super().__init__(config)
        self.config: JiraConfig = config
        self._client: Optional[httpx.AsyncClient] = None
    
    async def connect(self) -> bool:
        """Establish connection to Jira."""
        try:
            self._client = httpx.AsyncClient(
                base_url=f"{self.config.instance_url}/rest/api/3",
                auth=(self.config.email, self.config.api_token) if self.config.api_token else None,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=DEFAULT_HTTP_TIMEOUT,
            )
            
            # Test connection
            response = await self._client.get("/myself")
            if response.status_code == 200:
                self.status = ConnectorStatus.CONNECTED
                user = response.json()
                logger.info(f"Connected to Jira as {user.get('displayName', 'unknown')}")
                return True
            else:
                self.status = ConnectorStatus.ERROR
                self.last_error = f"Auth failed: {response.status_code}"
                return False
                
        except Exception as e:
            self.status = ConnectorStatus.ERROR
            self.last_error = str(e)
            logger.error(f"Jira connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self.status = ConnectorStatus.DISCONNECTED
    
    async def health_check(self) -> bool:
        """Check connection health."""
        if not self._client:
            return False
        
        try:
            response = await self._client.get("/serverInfo")
            return response.status_code == 200
        except Exception:
            return False
    
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify Jira webhook signature."""
        if not self.config.webhook_secret:
            return True  # No verification configured
        
        expected = hmac.new(
            self.config.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)
    
    async def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> WebhookEvent:
        """Process Jira webhook event."""
        event = WebhookEvent(
            source=self.name,
            event_type=event_type,
            payload=payload,
            received_at=datetime.utcnow(),
        )
        
        # Extract common fields
        issue = payload.get("issue", {})
        if issue:
            event.resource_id = issue.get("key")
            event.resource_type = "issue"
        
        changelog = payload.get("changelog", {})
        if changelog:
            event.metadata["changes"] = changelog.get("items", [])
        
        user = payload.get("user", {})
        if user:
            event.metadata["actor"] = user.get("displayName")
        
        return event
    
    # Issue Operations
    
    async def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Get issue by key."""
        if not self._client:
            return None
        
        response = await self._client.get(
            f"/issue/{issue_key}",
            params={"expand": "changelog,comments"},
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    
    async def search_issues(
        self,
        jql: str,
        start_at: int = 0,
        max_results: int = 50,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Search issues using JQL."""
        if not self._client:
            return {"issues": [], "total": 0}
        
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
        }
        if fields:
            params["fields"] = ",".join(fields)
        
        response = await self._client.get("/search", params=params)
        
        if response.status_code == 200:
            return response.json()
        return {"issues": [], "total": 0}
    
    async def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str = "Task",
        description: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignee: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new issue."""
        if not self._client:
            return None
        
        fields = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }
        
        if description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            }
        
        if priority:
            fields["priority"] = {"name": priority}
        
        if labels:
            fields["labels"] = labels
        
        if assignee:
            fields["assignee"] = {"accountId": assignee}
        
        if custom_fields:
            fields.update(custom_fields)
        
        response = await self._client.post("/issue", json={"fields": fields})
        
        if response.status_code == 201:
            return response.json()
        
        logger.error(f"Failed to create issue: {response.text}")
        return None
    
    async def update_issue(
        self,
        issue_key: str,
        fields: Dict[str, Any],
    ) -> bool:
        """Update an issue."""
        if not self._client:
            return False
        
        response = await self._client.put(
            f"/issue/{issue_key}",
            json={"fields": fields},
        )
        
        return response.status_code == 204
    
    async def transition_issue(
        self,
        issue_key: str,
        transition_id: str,
        comment: Optional[str] = None,
    ) -> bool:
        """Transition issue to a new status."""
        if not self._client:
            return False
        
        payload: Dict[str, Any] = {
            "transition": {"id": transition_id},
        }
        
        if comment:
            payload["update"] = {
                "comment": [
                    {
                        "add": {
                            "body": {
                                "type": "doc",
                                "version": 1,
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": comment}],
                                    }
                                ],
                            }
                        }
                    }
                ]
            }
        
        response = await self._client.post(
            f"/issue/{issue_key}/transitions",
            json=payload,
        )
        
        return response.status_code == 204
    
    async def add_comment(
        self,
        issue_key: str,
        body: str,
    ) -> Optional[Dict[str, Any]]:
        """Add a comment to an issue."""
        if not self._client:
            return None
        
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": body}],
                    }
                ],
            }
        }
        
        response = await self._client.post(
            f"/issue/{issue_key}/comment",
            json=payload,
        )
        
        if response.status_code == 201:
            return response.json()
        return None
    
    # Project Operations
    
    async def get_projects(self) -> List[Dict[str, Any]]:
        """Get all accessible projects."""
        if not self._client:
            return []
        
        response = await self._client.get("/project")
        
        if response.status_code == 200:
            return response.json()
        return []
    
    async def get_project(self, project_key: str) -> Optional[Dict[str, Any]]:
        """Get project details."""
        if not self._client:
            return None
        
        response = await self._client.get(f"/project/{project_key}")
        
        if response.status_code == 200:
            return response.json()
        return None
    
    # Sprint/Board Operations
    
    async def get_boards(self, project_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get Jira boards."""
        if not self._client:
            return []
        
        # Agile API uses different base URL
        url = f"{self.config.instance_url}/rest/agile/1.0/board"
        
        params = {}
        if project_key:
            params["projectKeyOrId"] = project_key
        
        response = await self._client.get(url, params=params)
        
        if response.status_code == 200:
            return response.json().get("values", [])
        return []
    
    async def get_sprints(
        self,
        board_id: int,
        state: str = "active",
    ) -> List[Dict[str, Any]]:
        """Get sprints for a board."""
        if not self._client:
            return []
        
        url = f"{self.config.instance_url}/rest/agile/1.0/board/{board_id}/sprint"
        
        response = await self._client.get(url, params={"state": state})
        
        if response.status_code == 200:
            return response.json().get("values", [])
        return []
    
    # Sync Operations
    
    async def sync_all(self) -> Dict[str, int]:
        """Sync all issues from configured projects."""
        stats = {"issues": 0, "comments": 0, "errors": 0}
        
        projects = self.config.projects or [p["key"] for p in await self.get_projects()]
        
        for project_key in projects:
            try:
                jql = f"project = {project_key} ORDER BY updated DESC"
                result = await self.search_issues(jql, max_results=100)
                
                for issue in result.get("issues", []):
                    stats["issues"] += 1
                    # Process issue...
                    
            except Exception as e:
                logger.error(f"Error syncing project {project_key}: {e}")
                stats["errors"] += 1
        
        return stats
    
    def normalize_event(self, event: WebhookEvent) -> Dict[str, Any]:
        """Convert Jira event to canonical format."""
        payload = event.payload
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})
        
        return {
            "source": "jira",
            "type": "ticket",
            "external_id": issue.get("key"),
            "title": fields.get("summary"),
            "description": self._extract_text(fields.get("description")),
            "status": fields.get("status", {}).get("name"),
            "priority": fields.get("priority", {}).get("name"),
            "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
            "reporter": fields.get("reporter", {}).get("displayName") if fields.get("reporter") else None,
            "labels": fields.get("labels", []),
            "created_at": fields.get("created"),
            "updated_at": fields.get("updated"),
            "project": fields.get("project", {}).get("key"),
            "issue_type": fields.get("issuetype", {}).get("name"),
            "url": f"{self.config.instance_url}/browse/{issue.get('key')}",
        }
    
    def _extract_text(self, doc: Optional[Dict[str, Any]]) -> str:
        """Extract plain text from Atlassian Document Format."""
        if not doc:
            return ""
        
        if isinstance(doc, str):
            return doc
        
        text_parts = []
        
        def extract(node: Dict[str, Any]) -> None:
            if node.get("type") == "text":
                text_parts.append(node.get("text", ""))
            for child in node.get("content", []):
                extract(child)
        
        extract(doc)
        return " ".join(text_parts)
