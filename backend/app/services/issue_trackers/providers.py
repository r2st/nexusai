"""
Issue Tracker Providers

Provider implementations for different issue tracking systems.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Any
from datetime import datetime

import httpx

from .models import (
    IssueTrackerType,
    Issue,
    IssueCreate,
    IssueUpdate,
    IssueStatus,
    IssuePriority,
    IssueType,
    IssueComment,
    Sprint,
    Board,
    IssueTrackerConfig,
    IssueSearchQuery,
    IssueSearchResult,
)

logger = logging.getLogger(__name__)


class BaseIssueTracker(ABC):
    """Base class for issue tracker providers."""
    
    tracker_type: IssueTrackerType
    
    def __init__(self, config: IssueTrackerConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=30.0,
        )
    
    @abstractmethod
    async def get_issue(self, issue_key: str) -> Issue:
        """Get an issue by key."""
        pass
    
    @abstractmethod
    async def create_issue(self, data: IssueCreate) -> Issue:
        """Create a new issue."""
        pass
    
    @abstractmethod
    async def update_issue(self, issue_key: str, data: IssueUpdate) -> Issue:
        """Update an existing issue."""
        pass
    
    @abstractmethod
    async def search_issues(self, query: IssueSearchQuery) -> IssueSearchResult:
        """Search for issues."""
        pass
    
    @abstractmethod
    async def add_comment(self, issue_key: str, body: str) -> IssueComment:
        """Add a comment to an issue."""
        pass
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def _map_status_to_tracker(self, status: IssueStatus) -> str:
        """Map internal status to tracker-specific status."""
        return self.config.status_mappings.get(status.value, status.value)
    
    def _map_status_from_tracker(self, status: str) -> IssueStatus:
        """Map tracker-specific status to internal status."""
        reverse_map = {v: k for k, v in self.config.status_mappings.items()}
        status_str = reverse_map.get(status, status).lower()
        try:
            return IssueStatus(status_str)
        except ValueError:
            return IssueStatus.OPEN


class JiraProvider(BaseIssueTracker):
    """Jira issue tracker provider."""
    
    tracker_type = IssueTrackerType.JIRA
    
    def __init__(self, config: IssueTrackerConfig):
        super().__init__(config)
        
        # Set up authentication
        if config.api_token and config.username:
            import base64
            credentials = base64.b64encode(
                f"{config.username}:{config.api_token}".encode()
            ).decode()
            self.client.headers["Authorization"] = f"Basic {credentials}"
        elif config.oauth_token:
            self.client.headers["Authorization"] = f"Bearer {config.oauth_token}"
    
    async def get_issue(self, issue_key: str) -> Issue:
        """Get a Jira issue by key."""
        response = await self.client.get(
            f"/rest/api/3/issue/{issue_key}",
            params={"expand": "changelog,comments"}
        )
        response.raise_for_status()
        data = response.json()
        return self._parse_issue(data)
    
    async def create_issue(self, data: IssueCreate) -> Issue:
        """Create a Jira issue."""
        fields = {
            "project": {"key": data.project_key},
            "summary": data.title,
            "issuetype": {"name": self._map_issue_type(data.issue_type)},
        }
        
        if data.description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": data.description}]}]
            }
        
        if data.priority:
            fields["priority"] = {"name": self._map_priority(data.priority)}
        
        if data.assignee:
            fields["assignee"] = {"accountId": data.assignee}
        
        if data.labels:
            fields["labels"] = data.labels
        
        if data.components:
            fields["components"] = [{"name": c} for c in data.components]
        
        if data.epic_key:
            fields["parent"] = {"key": data.epic_key}
        
        if data.story_points:
            fields["customfield_10016"] = data.story_points  # Common field ID
        
        if data.due_date:
            fields["duedate"] = data.due_date.strftime("%Y-%m-%d")
        
        response = await self.client.post(
            "/rest/api/3/issue",
            json={"fields": fields}
        )
        response.raise_for_status()
        
        created_key = response.json()["key"]
        return await self.get_issue(created_key)
    
    async def update_issue(self, issue_key: str, data: IssueUpdate) -> Issue:
        """Update a Jira issue."""
        fields = {}
        
        if data.title:
            fields["summary"] = data.title
        
        if data.description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": data.description}]}]
            }
        
        if data.priority:
            fields["priority"] = {"name": self._map_priority(data.priority)}
        
        if data.assignee is not None:
            fields["assignee"] = {"accountId": data.assignee} if data.assignee else None
        
        if data.labels is not None:
            fields["labels"] = data.labels
        
        if fields:
            response = await self.client.put(
                f"/rest/api/3/issue/{issue_key}",
                json={"fields": fields}
            )
            response.raise_for_status()
        
        # Handle status transition separately
        if data.status:
            await self._transition_issue(issue_key, data.status)
        
        return await self.get_issue(issue_key)
    
    async def _transition_issue(self, issue_key: str, status: IssueStatus):
        """Transition issue to a new status."""
        # Get available transitions
        response = await self.client.get(
            f"/rest/api/3/issue/{issue_key}/transitions"
        )
        response.raise_for_status()
        transitions = response.json()["transitions"]
        
        # Find matching transition
        target_status = self._map_status_to_tracker(status)
        for transition in transitions:
            if transition["to"]["name"].lower() == target_status.lower():
                await self.client.post(
                    f"/rest/api/3/issue/{issue_key}/transitions",
                    json={"transition": {"id": transition["id"]}}
                )
                return
        
        logger.warning(f"No transition found for status {target_status}")
    
    async def search_issues(self, query: IssueSearchQuery) -> IssueSearchResult:
        """Search Jira issues using JQL."""
        jql_parts = []
        
        if query.jql:
            jql_parts.append(query.jql)
        else:
            if query.project_key:
                jql_parts.append(f"project = {query.project_key}")
            
            if query.status:
                statuses = ", ".join(f'"{self._map_status_to_tracker(s)}"' for s in query.status)
                jql_parts.append(f"status IN ({statuses})")
            
            if query.assignee:
                jql_parts.append(f"assignee = {query.assignee}")
            
            if query.text_query:
                jql_parts.append(f'text ~ "{query.text_query}"')
            
            if query.created_after:
                jql_parts.append(f"created >= '{query.created_after.strftime('%Y-%m-%d')}'")
            
            if query.sprint_id:
                jql_parts.append(f"sprint = {query.sprint_id}")
        
        jql = " AND ".join(jql_parts) if jql_parts else "ORDER BY created DESC"
        
        response = await self.client.get(
            "/rest/api/3/search",
            params={
                "jql": jql,
                "maxResults": query.max_results,
                "startAt": query.offset,
            }
        )
        response.raise_for_status()
        data = response.json()
        
        issues = [self._parse_issue(issue) for issue in data["issues"]]
        
        return IssueSearchResult(
            issues=issues,
            total=data["total"],
            offset=query.offset,
            max_results=query.max_results,
            has_more=query.offset + len(issues) < data["total"],
        )
    
    async def add_comment(self, issue_key: str, body: str) -> IssueComment:
        """Add a comment to a Jira issue."""
        response = await self.client.post(
            f"/rest/api/3/issue/{issue_key}/comment",
            json={
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": body}]}]
                }
            }
        )
        response.raise_for_status()
        data = response.json()
        
        return IssueComment(
            id=data["id"],
            author=data["author"]["displayName"],
            body=body,
            created_at=datetime.fromisoformat(data["created"].replace("Z", "+00:00")),
        )
    
    async def get_sprints(self, board_id: str) -> list[Sprint]:
        """Get sprints for a board."""
        response = await self.client.get(
            f"/rest/agile/1.0/board/{board_id}/sprint"
        )
        response.raise_for_status()
        
        sprints = []
        for s in response.json().get("values", []):
            sprints.append(Sprint(
                id=str(s["id"]),
                name=s["name"],
                state=s["state"],
                start_date=datetime.fromisoformat(s["startDate"].replace("Z", "+00:00")) if s.get("startDate") else None,
                end_date=datetime.fromisoformat(s["endDate"].replace("Z", "+00:00")) if s.get("endDate") else None,
                goal=s.get("goal"),
                board_id=board_id,
            ))
        
        return sprints
    
    def _parse_issue(self, data: dict) -> Issue:
        """Parse Jira API response to Issue model."""
        fields = data["fields"]
        
        return Issue(
            id=data["id"],
            key=data["key"],
            url=f"{self.config.base_url}/browse/{data['key']}",
            title=fields["summary"],
            description=self._extract_description(fields.get("description")),
            issue_type=self._parse_issue_type(fields.get("issuetype", {}).get("name", "")),
            status=self._map_status_from_tracker(fields.get("status", {}).get("name", "Open")),
            priority=self._parse_priority(fields.get("priority", {}).get("name", "")),
            assignee=fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
            reporter=fields.get("reporter", {}).get("displayName", ""),
            project_id=fields.get("project", {}).get("id", ""),
            project_key=fields.get("project", {}).get("key", ""),
            created_at=datetime.fromisoformat(fields["created"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(fields["updated"].replace("Z", "+00:00")) if fields.get("updated") else None,
            due_date=datetime.fromisoformat(fields["duedate"]) if fields.get("duedate") else None,
            story_points=fields.get("customfield_10016"),
            labels=fields.get("labels", []),
            components=[c["name"] for c in fields.get("components", [])],
            source_tracker=IssueTrackerType.JIRA,
            raw_data=data,
        )
    
    def _extract_description(self, desc: Any) -> Optional[str]:
        """Extract plain text from Jira document format."""
        if not desc:
            return None
        if isinstance(desc, str):
            return desc
        
        # Parse Atlassian Document Format
        texts = []
        def extract_text(node):
            if isinstance(node, dict):
                if node.get("type") == "text":
                    texts.append(node.get("text", ""))
                for child in node.get("content", []):
                    extract_text(child)
            elif isinstance(node, list):
                for item in node:
                    extract_text(item)
        
        extract_text(desc)
        return "\n".join(texts) if texts else None
    
    def _map_issue_type(self, issue_type: IssueType) -> str:
        """Map internal issue type to Jira type."""
        mapping = {
            IssueType.BUG: "Bug",
            IssueType.FEATURE: "Story",
            IssueType.TASK: "Task",
            IssueType.STORY: "Story",
            IssueType.EPIC: "Epic",
            IssueType.TECH_DEBT: "Task",
            IssueType.SECURITY: "Bug",
            IssueType.IMPROVEMENT: "Improvement",
        }
        return self.config.type_mappings.get(issue_type.value) or mapping.get(issue_type, "Task")
    
    def _parse_issue_type(self, type_name: str) -> IssueType:
        """Parse Jira type to internal type."""
        reverse_map = {v: k for k, v in self.config.type_mappings.items()}
        mapping = {
            "bug": IssueType.BUG,
            "story": IssueType.STORY,
            "task": IssueType.TASK,
            "epic": IssueType.EPIC,
            "sub-task": IssueType.TASK,
            "improvement": IssueType.IMPROVEMENT,
        }
        type_lower = type_name.lower()
        if type_lower in reverse_map:
            return IssueType(reverse_map[type_lower])
        return mapping.get(type_lower, IssueType.TASK)
    
    def _map_priority(self, priority: IssuePriority) -> str:
        """Map internal priority to Jira priority."""
        mapping = {
            IssuePriority.CRITICAL: "Highest",
            IssuePriority.HIGH: "High",
            IssuePriority.MEDIUM: "Medium",
            IssuePriority.LOW: "Low",
            IssuePriority.TRIVIAL: "Lowest",
        }
        return self.config.priority_mappings.get(priority.value) or mapping.get(priority, "Medium")
    
    def _parse_priority(self, priority_name: str) -> IssuePriority:
        """Parse Jira priority to internal priority."""
        mapping = {
            "highest": IssuePriority.CRITICAL,
            "high": IssuePriority.HIGH,
            "medium": IssuePriority.MEDIUM,
            "low": IssuePriority.LOW,
            "lowest": IssuePriority.TRIVIAL,
        }
        return mapping.get(priority_name.lower(), IssuePriority.MEDIUM)


class AzureBoardsProvider(BaseIssueTracker):
    """Azure DevOps Boards provider."""
    
    tracker_type = IssueTrackerType.AZURE_BOARDS
    
    def __init__(self, config: IssueTrackerConfig):
        super().__init__(config)
        
        # Azure DevOps uses PAT as Basic auth
        if config.api_token:
            import base64
            credentials = base64.b64encode(f":{config.api_token}".encode()).decode()
            self.client.headers["Authorization"] = f"Basic {credentials}"
        
        self.organization = config.base_url.split("/")[-1] if "/" in config.base_url else config.base_url
    
    async def get_issue(self, issue_key: str) -> Issue:
        """Get an Azure Boards work item."""
        # issue_key is the work item ID
        response = await self.client.get(
            f"/_apis/wit/workitems/{issue_key}",
            params={"api-version": "7.0", "$expand": "all"}
        )
        response.raise_for_status()
        return self._parse_work_item(response.json())
    
    async def create_issue(self, data: IssueCreate) -> Issue:
        """Create an Azure Boards work item."""
        operations = [
            {"op": "add", "path": "/fields/System.Title", "value": data.title},
            {"op": "add", "path": "/fields/System.WorkItemType", "value": self._map_issue_type(data.issue_type)},
        ]
        
        if data.description:
            operations.append({"op": "add", "path": "/fields/System.Description", "value": data.description})
        
        if data.assignee:
            operations.append({"op": "add", "path": "/fields/System.AssignedTo", "value": data.assignee})
        
        if data.priority:
            operations.append({"op": "add", "path": "/fields/Microsoft.VSTS.Common.Priority", "value": self._map_priority(data.priority)})
        
        if data.labels:
            operations.append({"op": "add", "path": "/fields/System.Tags", "value": "; ".join(data.labels)})
        
        if data.story_points:
            operations.append({"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.StoryPoints", "value": data.story_points})
        
        response = await self.client.post(
            f"/{data.project_key}/_apis/wit/workitems/${self._map_issue_type(data.issue_type)}",
            params={"api-version": "7.0"},
            json=operations,
            headers={"Content-Type": "application/json-patch+json"}
        )
        response.raise_for_status()
        return self._parse_work_item(response.json())
    
    async def update_issue(self, issue_key: str, data: IssueUpdate) -> Issue:
        """Update an Azure Boards work item."""
        operations = []
        
        if data.title:
            operations.append({"op": "add", "path": "/fields/System.Title", "value": data.title})
        
        if data.description:
            operations.append({"op": "add", "path": "/fields/System.Description", "value": data.description})
        
        if data.status:
            operations.append({"op": "add", "path": "/fields/System.State", "value": self._map_status_to_tracker(data.status)})
        
        if data.assignee is not None:
            operations.append({"op": "add", "path": "/fields/System.AssignedTo", "value": data.assignee})
        
        if data.priority:
            operations.append({"op": "add", "path": "/fields/Microsoft.VSTS.Common.Priority", "value": self._map_priority(data.priority)})
        
        if operations:
            response = await self.client.patch(
                f"/_apis/wit/workitems/{issue_key}",
                params={"api-version": "7.0"},
                json=operations,
                headers={"Content-Type": "application/json-patch+json"}
            )
            response.raise_for_status()
        
        return await self.get_issue(issue_key)
    
    async def search_issues(self, query: IssueSearchQuery) -> IssueSearchResult:
        """Search Azure Boards work items using WIQL."""
        if query.wiql:
            wiql = query.wiql
        else:
            conditions = ["[System.TeamProject] = @project"]
            
            if query.status:
                states = ", ".join(f"'{self._map_status_to_tracker(s)}'" for s in query.status)
                conditions.append(f"[System.State] IN ({states})")
            
            if query.assignee:
                conditions.append(f"[System.AssignedTo] = '{query.assignee}'")
            
            if query.text_query:
                conditions.append(f"[System.Title] CONTAINS '{query.text_query}'")
            
            wiql = f"SELECT [System.Id] FROM WorkItems WHERE {' AND '.join(conditions)} ORDER BY [System.CreatedDate] DESC"
        
        response = await self.client.post(
            f"/{query.project_key or self.config.default_project_key}/_apis/wit/wiql",
            params={"api-version": "7.0", "$top": query.max_results, "$skip": query.offset},
            json={"query": wiql}
        )
        response.raise_for_status()
        data = response.json()
        
        # Fetch full work items
        work_items = data.get("workItems", [])
        if work_items:
            ids = ",".join(str(wi["id"]) for wi in work_items[:query.max_results])
            detail_response = await self.client.get(
                f"/_apis/wit/workitems",
                params={"ids": ids, "api-version": "7.0", "$expand": "all"}
            )
            detail_response.raise_for_status()
            issues = [self._parse_work_item(wi) for wi in detail_response.json().get("value", [])]
        else:
            issues = []
        
        return IssueSearchResult(
            issues=issues,
            total=len(work_items),
            offset=query.offset,
            max_results=query.max_results,
            has_more=len(work_items) > query.max_results,
        )
    
    async def add_comment(self, issue_key: str, body: str) -> IssueComment:
        """Add a comment to an Azure Boards work item."""
        response = await self.client.post(
            f"/_apis/wit/workitems/{issue_key}/comments",
            params={"api-version": "7.0-preview.3"},
            json={"text": body}
        )
        response.raise_for_status()
        data = response.json()
        
        return IssueComment(
            id=str(data["id"]),
            author=data["createdBy"]["displayName"],
            body=body,
            created_at=datetime.fromisoformat(data["createdDate"].replace("Z", "+00:00")),
        )
    
    def _parse_work_item(self, data: dict) -> Issue:
        """Parse Azure DevOps work item to Issue model."""
        fields = data.get("fields", {})
        
        return Issue(
            id=str(data["id"]),
            key=str(data["id"]),
            url=data.get("_links", {}).get("html", {}).get("href", ""),
            title=fields.get("System.Title", ""),
            description=fields.get("System.Description"),
            issue_type=self._parse_issue_type(fields.get("System.WorkItemType", "Task")),
            status=self._map_status_from_tracker(fields.get("System.State", "New")),
            priority=self._parse_priority(fields.get("Microsoft.VSTS.Common.Priority", 2)),
            assignee=fields.get("System.AssignedTo", {}).get("displayName") if fields.get("System.AssignedTo") else None,
            reporter=fields.get("System.CreatedBy", {}).get("displayName", ""),
            project_id=fields.get("System.TeamProject", ""),
            project_key=fields.get("System.TeamProject", ""),
            created_at=datetime.fromisoformat(fields["System.CreatedDate"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(fields["System.ChangedDate"].replace("Z", "+00:00")) if fields.get("System.ChangedDate") else None,
            story_points=fields.get("Microsoft.VSTS.Scheduling.StoryPoints"),
            labels=fields.get("System.Tags", "").split("; ") if fields.get("System.Tags") else [],
            source_tracker=IssueTrackerType.AZURE_BOARDS,
            raw_data=data,
        )
    
    def _map_issue_type(self, issue_type: IssueType) -> str:
        """Map to Azure DevOps work item type."""
        mapping = {
            IssueType.BUG: "Bug",
            IssueType.FEATURE: "Feature",
            IssueType.TASK: "Task",
            IssueType.STORY: "User Story",
            IssueType.EPIC: "Epic",
            IssueType.TECH_DEBT: "Task",
        }
        return mapping.get(issue_type, "Task")
    
    def _parse_issue_type(self, type_name: str) -> IssueType:
        """Parse Azure DevOps type."""
        mapping = {
            "bug": IssueType.BUG,
            "feature": IssueType.FEATURE,
            "task": IssueType.TASK,
            "user story": IssueType.STORY,
            "epic": IssueType.EPIC,
        }
        return mapping.get(type_name.lower(), IssueType.TASK)
    
    def _map_priority(self, priority: IssuePriority) -> int:
        """Map to Azure DevOps priority (1-4)."""
        mapping = {
            IssuePriority.CRITICAL: 1,
            IssuePriority.HIGH: 1,
            IssuePriority.MEDIUM: 2,
            IssuePriority.LOW: 3,
            IssuePriority.TRIVIAL: 4,
        }
        return mapping.get(priority, 2)
    
    def _parse_priority(self, priority: int) -> IssuePriority:
        """Parse Azure DevOps priority."""
        mapping = {
            1: IssuePriority.HIGH,
            2: IssuePriority.MEDIUM,
            3: IssuePriority.LOW,
            4: IssuePriority.TRIVIAL,
        }
        return mapping.get(priority, IssuePriority.MEDIUM)


class LinearProvider(BaseIssueTracker):
    """Linear issue tracker provider."""
    
    tracker_type = IssueTrackerType.LINEAR
    
    def __init__(self, config: IssueTrackerConfig):
        # Linear uses GraphQL API
        super().__init__(config)
        self.client = httpx.AsyncClient(
            base_url="https://api.linear.app",
            timeout=30.0,
            headers={
                "Authorization": config.api_token or "",
                "Content-Type": "application/json",
            }
        )
    
    async def get_issue(self, issue_key: str) -> Issue:
        """Get a Linear issue."""
        query = """
        query($id: String!) {
            issue(id: $id) {
                id identifier title description state { name } priority
                assignee { name } creator { name }
                createdAt updatedAt dueDate
                labels { nodes { name } }
                team { key }
            }
        }
        """
        response = await self.client.post(
            "/graphql",
            json={"query": query, "variables": {"id": issue_key}}
        )
        response.raise_for_status()
        data = response.json()["data"]["issue"]
        return self._parse_linear_issue(data)
    
    async def create_issue(self, data: IssueCreate) -> Issue:
        """Create a Linear issue."""
        mutation = """
        mutation($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                issue { id identifier title }
            }
        }
        """
        input_data = {
            "teamId": data.project_key,
            "title": data.title,
            "description": data.description,
            "priority": self._map_priority(data.priority),
        }
        
        if data.assignee:
            input_data["assigneeId"] = data.assignee
        
        response = await self.client.post(
            "/graphql",
            json={"query": mutation, "variables": {"input": input_data}}
        )
        response.raise_for_status()
        issue_id = response.json()["data"]["issueCreate"]["issue"]["id"]
        return await self.get_issue(issue_id)
    
    async def update_issue(self, issue_key: str, data: IssueUpdate) -> Issue:
        """Update a Linear issue."""
        mutation = """
        mutation($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                issue { id }
            }
        }
        """
        input_data = {}
        
        if data.title:
            input_data["title"] = data.title
        if data.description:
            input_data["description"] = data.description
        if data.priority:
            input_data["priority"] = self._map_priority(data.priority)
        if data.assignee:
            input_data["assigneeId"] = data.assignee
        
        if input_data:
            await self.client.post(
                "/graphql",
                json={"query": mutation, "variables": {"id": issue_key, "input": input_data}}
            )
        
        return await self.get_issue(issue_key)
    
    async def search_issues(self, query: IssueSearchQuery) -> IssueSearchResult:
        """Search Linear issues."""
        gql_query = """
        query($filter: IssueFilter, $first: Int, $after: String) {
            issues(filter: $filter, first: $first, after: $after) {
                nodes {
                    id identifier title description state { name } priority
                    assignee { name } creator { name }
                    createdAt updatedAt dueDate
                    labels { nodes { name } }
                    team { key }
                }
                pageInfo { hasNextPage endCursor }
            }
        }
        """
        
        filters = {}
        if query.project_key:
            filters["team"] = {"key": {"eq": query.project_key}}
        if query.text_query:
            filters["title"] = {"contains": query.text_query}
        
        response = await self.client.post(
            "/graphql",
            json={
                "query": gql_query,
                "variables": {
                    "filter": filters if filters else None,
                    "first": query.max_results,
                }
            }
        )
        response.raise_for_status()
        data = response.json()["data"]["issues"]
        
        issues = [self._parse_linear_issue(node) for node in data["nodes"]]
        
        return IssueSearchResult(
            issues=issues,
            total=len(issues),
            offset=query.offset,
            max_results=query.max_results,
            has_more=data["pageInfo"]["hasNextPage"],
        )
    
    async def add_comment(self, issue_key: str, body: str) -> IssueComment:
        """Add a comment to a Linear issue."""
        mutation = """
        mutation($input: CommentCreateInput!) {
            commentCreate(input: $input) {
                comment { id body createdAt user { name } }
            }
        }
        """
        response = await self.client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {"input": {"issueId": issue_key, "body": body}}
            }
        )
        response.raise_for_status()
        data = response.json()["data"]["commentCreate"]["comment"]
        
        return IssueComment(
            id=data["id"],
            author=data["user"]["name"],
            body=data["body"],
            created_at=datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00")),
        )
    
    def _parse_linear_issue(self, data: dict) -> Issue:
        """Parse Linear issue to Issue model."""
        return Issue(
            id=data["id"],
            key=data["identifier"],
            url=f"https://linear.app/issue/{data['identifier']}",
            title=data["title"],
            description=data.get("description"),
            status=self._map_status_from_tracker(data.get("state", {}).get("name", "Backlog")),
            priority=self._parse_priority(data.get("priority", 0)),
            assignee=data.get("assignee", {}).get("name") if data.get("assignee") else None,
            reporter=data.get("creator", {}).get("name", ""),
            project_key=data.get("team", {}).get("key", ""),
            created_at=datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updatedAt"].replace("Z", "+00:00")) if data.get("updatedAt") else None,
            due_date=datetime.fromisoformat(data["dueDate"]) if data.get("dueDate") else None,
            labels=[label["name"] for label in data.get("labels", {}).get("nodes", [])],
            source_tracker=IssueTrackerType.LINEAR,
            raw_data=data,
        )
    
    def _map_priority(self, priority: IssuePriority) -> int:
        """Map to Linear priority (0-4)."""
        mapping = {
            IssuePriority.CRITICAL: 1,
            IssuePriority.HIGH: 2,
            IssuePriority.MEDIUM: 3,
            IssuePriority.LOW: 4,
            IssuePriority.TRIVIAL: 0,
        }
        return mapping.get(priority, 3)
    
    def _parse_priority(self, priority: int) -> IssuePriority:
        """Parse Linear priority."""
        mapping = {
            0: IssuePriority.TRIVIAL,
            1: IssuePriority.CRITICAL,
            2: IssuePriority.HIGH,
            3: IssuePriority.MEDIUM,
            4: IssuePriority.LOW,
        }
        return mapping.get(priority, IssuePriority.MEDIUM)


class GitHubIssuesProvider(BaseIssueTracker):
    """GitHub Issues provider."""
    
    tracker_type = IssueTrackerType.GITHUB
    
    def __init__(self, config: IssueTrackerConfig):
        super().__init__(config)
        self.client = httpx.AsyncClient(
            base_url="https://api.github.com",
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {config.api_token}",
                "Accept": "application/vnd.github+json",
            }
        )
    
    async def get_issue(self, issue_key: str) -> Issue:
        """Get a GitHub issue."""
        # issue_key format: owner/repo#number
        parts = issue_key.replace("#", "/").split("/")
        owner, repo, number = parts[0], parts[1], parts[2]
        
        response = await self.client.get(f"/repos/{owner}/{repo}/issues/{number}")
        response.raise_for_status()
        return self._parse_github_issue(response.json(), f"{owner}/{repo}")
    
    async def create_issue(self, data: IssueCreate) -> Issue:
        """Create a GitHub issue."""
        # project_key format: owner/repo
        response = await self.client.post(
            f"/repos/{data.project_key}/issues",
            json={
                "title": data.title,
                "body": data.description,
                "labels": data.labels,
                "assignees": [data.assignee] if data.assignee else [],
            }
        )
        response.raise_for_status()
        return self._parse_github_issue(response.json(), data.project_key)
    
    async def update_issue(self, issue_key: str, data: IssueUpdate) -> Issue:
        """Update a GitHub issue."""
        parts = issue_key.replace("#", "/").split("/")
        owner, repo, number = parts[0], parts[1], parts[2]
        
        update_data = {}
        if data.title:
            update_data["title"] = data.title
        if data.description:
            update_data["body"] = data.description
        if data.status:
            update_data["state"] = "closed" if data.status in [IssueStatus.DONE, IssueStatus.CLOSED] else "open"
        if data.labels is not None:
            update_data["labels"] = data.labels
        
        if update_data:
            response = await self.client.patch(
                f"/repos/{owner}/{repo}/issues/{number}",
                json=update_data
            )
            response.raise_for_status()
        
        return await self.get_issue(issue_key)
    
    async def search_issues(self, query: IssueSearchQuery) -> IssueSearchResult:
        """Search GitHub issues."""
        q_parts = []
        
        if query.project_key:
            q_parts.append(f"repo:{query.project_key}")
        
        q_parts.append("is:issue")
        
        if query.status:
            if IssueStatus.CLOSED in query.status or IssueStatus.DONE in query.status:
                q_parts.append("is:closed")
            else:
                q_parts.append("is:open")
        
        if query.text_query:
            q_parts.append(query.text_query)
        
        if query.labels:
            for label in query.labels:
                q_parts.append(f"label:{label}")
        
        response = await self.client.get(
            "/search/issues",
            params={
                "q": " ".join(q_parts),
                "per_page": query.max_results,
                "page": query.offset // query.max_results + 1,
            }
        )
        response.raise_for_status()
        data = response.json()
        
        issues = [self._parse_github_issue(item, query.project_key or "") for item in data["items"]]
        
        return IssueSearchResult(
            issues=issues,
            total=data["total_count"],
            offset=query.offset,
            max_results=query.max_results,
            has_more=data["total_count"] > query.offset + len(issues),
        )
    
    async def add_comment(self, issue_key: str, body: str) -> IssueComment:
        """Add a comment to a GitHub issue."""
        parts = issue_key.replace("#", "/").split("/")
        owner, repo, number = parts[0], parts[1], parts[2]
        
        response = await self.client.post(
            f"/repos/{owner}/{repo}/issues/{number}/comments",
            json={"body": body}
        )
        response.raise_for_status()
        data = response.json()
        
        return IssueComment(
            id=str(data["id"]),
            author=data["user"]["login"],
            body=data["body"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
        )
    
    def _parse_github_issue(self, data: dict, repo: str) -> Issue:
        """Parse GitHub issue to Issue model."""
        return Issue(
            id=str(data["id"]),
            key=f"{repo}#{data['number']}",
            url=data["html_url"],
            title=data["title"],
            description=data.get("body"),
            issue_type=IssueType.BUG if "bug" in [l["name"].lower() for l in data.get("labels", [])] else IssueType.TASK,
            status=IssueStatus.CLOSED if data["state"] == "closed" else IssueStatus.OPEN,
            assignee=data["assignee"]["login"] if data.get("assignee") else None,
            reporter=data["user"]["login"],
            project_key=repo,
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")) if data.get("updated_at") else None,
            labels=[label["name"] for label in data.get("labels", [])],
            source_tracker=IssueTrackerType.GITHUB,
            raw_data=data,
        )
