"""
PagerDuty Connector

Connector for PagerDuty incident management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import asyncio
import hashlib
import hmac
import logging

import httpx

from .base import BaseConnector, ConnectorConfig, ConnectorStatus, WebhookEvent

logger = logging.getLogger(__name__)


@dataclass
class PagerDutyConfig(ConnectorConfig):
    """PagerDuty-specific configuration."""
    # Authentication
    api_token: str = ""  # REST API token
    integration_key: str = ""  # Events API integration key
    
    # Webhook
    webhook_secret: str = ""
    
    # Services to monitor
    service_ids: List[str] = field(default_factory=list)
    
    # Sync settings
    sync_incidents: bool = True
    sync_services: bool = True
    sync_oncalls: bool = True


class PagerDutyConnector(BaseConnector):
    """
    PagerDuty connector for incident management.
    
    Features:
    - Incident creation/management
    - On-call schedules
    - Service monitoring
    - Webhook events
    """
    
    name = "pagerduty"
    display_name = "PagerDuty"
    
    def __init__(self, config: PagerDutyConfig):
        super().__init__(config)
        self.config: PagerDutyConfig = config
        self._client: Optional[httpx.AsyncClient] = None
        self._events_client: Optional[httpx.AsyncClient] = None
    
    async def connect(self) -> bool:
        """Establish connection to PagerDuty."""
        try:
            self._client = httpx.AsyncClient(
                base_url="https://api.pagerduty.com",
                headers={
                    "Authorization": f"Token token={self.config.api_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/vnd.pagerduty+json;version=2",
                },
                timeout=30.0,
            )
            
            self._events_client = httpx.AsyncClient(
                base_url="https://events.pagerduty.com/v2",
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
            
            # Test connection
            response = await self._client.get("/abilities")
            
            if response.status_code == 200:
                self.status = ConnectorStatus.CONNECTED
                logger.info("Connected to PagerDuty")
                return True
            else:
                self.status = ConnectorStatus.ERROR
                self.last_error = f"Auth failed: {response.status_code}"
                return False
                
        except Exception as e:
            self.status = ConnectorStatus.ERROR
            self.last_error = str(e)
            logger.error(f"PagerDuty connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._events_client:
            await self._events_client.aclose()
            self._events_client = None
        self.status = ConnectorStatus.DISCONNECTED
    
    async def health_check(self) -> bool:
        """Check connection health."""
        if not self._client:
            return False
        
        try:
            response = await self._client.get("/abilities")
            return response.status_code == 200
        except Exception:
            return False
    
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify PagerDuty webhook signature."""
        if not self.config.webhook_secret:
            return True
        
        # PagerDuty v3 webhooks use HMAC-SHA256
        expected = hmac.new(
            self.config.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)
    
    async def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> WebhookEvent:
        """Process PagerDuty webhook event."""
        event = WebhookEvent(
            source=self.name,
            event_type=event_type,
            payload=payload,
            received_at=datetime.utcnow(),
        )
        
        # Handle incident events
        incident = payload.get("incident", {})
        if incident:
            event.resource_id = incident.get("id")
            event.resource_type = "incident"
            event.metadata["status"] = incident.get("status")
            event.metadata["urgency"] = incident.get("urgency")
            event.metadata["service"] = incident.get("service", {}).get("summary")
        
        return event
    
    # Incident Operations
    
    async def get_incidents(
        self,
        statuses: Optional[List[str]] = None,
        service_ids: Optional[List[str]] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        """Get incidents."""
        if not self._client:
            return []
        
        params: Dict[str, Any] = {"limit": limit}
        
        if statuses:
            params["statuses[]"] = statuses
        if service_ids:
            params["service_ids[]"] = service_ids
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        
        response = await self._client.get("/incidents", params=params)
        
        if response.status_code == 200:
            return response.json().get("incidents", [])
        return []
    
    async def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get incident by ID."""
        if not self._client:
            return None
        
        response = await self._client.get(f"/incidents/{incident_id}")
        
        if response.status_code == 200:
            return response.json().get("incident")
        return None
    
    async def create_incident(
        self,
        service_id: str,
        title: str,
        urgency: str = "high",
        body: Optional[str] = None,
        escalation_policy_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create an incident."""
        if not self._client:
            return None
        
        incident = {
            "type": "incident",
            "title": title,
            "urgency": urgency,
            "service": {
                "id": service_id,
                "type": "service_reference",
            },
        }
        
        if body:
            incident["body"] = {"type": "incident_body", "details": body}
        
        if escalation_policy_id:
            incident["escalation_policy"] = {
                "id": escalation_policy_id,
                "type": "escalation_policy_reference",
            }
        
        response = await self._client.post(
            "/incidents",
            json={"incident": incident},
        )
        
        if response.status_code == 201:
            return response.json().get("incident")
        
        logger.error(f"Failed to create incident: {response.text}")
        return None
    
    async def update_incident(
        self,
        incident_id: str,
        status: Optional[str] = None,
        resolution: Optional[str] = None,
        escalation_level: Optional[int] = None,
    ) -> bool:
        """Update an incident."""
        if not self._client:
            return False
        
        incident: Dict[str, Any] = {"type": "incident"}
        
        if status:
            incident["status"] = status
        if resolution:
            incident["resolution"] = resolution
        if escalation_level is not None:
            incident["escalation_level"] = escalation_level
        
        response = await self._client.put(
            f"/incidents/{incident_id}",
            json={"incident": incident},
        )
        
        return response.status_code == 200
    
    async def acknowledge_incident(self, incident_id: str) -> bool:
        """Acknowledge an incident."""
        return await self.update_incident(incident_id, status="acknowledged")
    
    async def resolve_incident(self, incident_id: str, resolution: str = "") -> bool:
        """Resolve an incident."""
        return await self.update_incident(
            incident_id,
            status="resolved",
            resolution=resolution,
        )
    
    async def add_note(self, incident_id: str, content: str) -> Optional[Dict[str, Any]]:
        """Add a note to an incident."""
        if not self._client:
            return None
        
        response = await self._client.post(
            f"/incidents/{incident_id}/notes",
            json={"note": {"content": content}},
        )
        
        if response.status_code == 201:
            return response.json().get("note")
        return None
    
    # Events API (for triggering alerts)
    
    async def trigger_event(
        self,
        summary: str,
        source: str,
        severity: str = "error",
        dedup_key: Optional[str] = None,
        custom_details: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Trigger an event via Events API."""
        if not self._events_client or not self.config.integration_key:
            return None
        
        payload = {
            "routing_key": self.config.integration_key,
            "event_action": "trigger",
            "payload": {
                "summary": summary,
                "source": source,
                "severity": severity,
            },
        }
        
        if dedup_key:
            payload["dedup_key"] = dedup_key
        
        if custom_details:
            payload["payload"]["custom_details"] = custom_details
        
        response = await self._events_client.post("/enqueue", json=payload)
        
        if response.status_code == 202:
            return response.json().get("dedup_key")
        
        logger.error(f"Failed to trigger event: {response.text}")
        return None
    
    async def acknowledge_event(self, dedup_key: str) -> bool:
        """Acknowledge an event."""
        if not self._events_client or not self.config.integration_key:
            return False
        
        response = await self._events_client.post(
            "/enqueue",
            json={
                "routing_key": self.config.integration_key,
                "event_action": "acknowledge",
                "dedup_key": dedup_key,
            },
        )
        
        return response.status_code == 202
    
    async def resolve_event(self, dedup_key: str) -> bool:
        """Resolve an event."""
        if not self._events_client or not self.config.integration_key:
            return False
        
        response = await self._events_client.post(
            "/enqueue",
            json={
                "routing_key": self.config.integration_key,
                "event_action": "resolve",
                "dedup_key": dedup_key,
            },
        )
        
        return response.status_code == 202
    
    # Service Operations
    
    async def get_services(self) -> List[Dict[str, Any]]:
        """Get all services."""
        if not self._client:
            return []
        
        response = await self._client.get("/services")
        
        if response.status_code == 200:
            return response.json().get("services", [])
        return []
    
    async def get_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get service by ID."""
        if not self._client:
            return None
        
        response = await self._client.get(f"/services/{service_id}")
        
        if response.status_code == 200:
            return response.json().get("service")
        return None
    
    # On-Call Operations
    
    async def get_oncalls(
        self,
        schedule_ids: Optional[List[str]] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get on-call schedules."""
        if not self._client:
            return []
        
        params: Dict[str, Any] = {}
        
        if schedule_ids:
            params["schedule_ids[]"] = schedule_ids
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        
        response = await self._client.get("/oncalls", params=params)
        
        if response.status_code == 200:
            return response.json().get("oncalls", [])
        return []
    
    def normalize_event(self, event: WebhookEvent) -> Dict[str, Any]:
        """Convert PagerDuty event to canonical format."""
        incident = event.payload.get("incident", {})
        
        return {
            "source": "pagerduty",
            "type": "incident",
            "external_id": incident.get("id"),
            "title": incident.get("title"),
            "description": incident.get("description"),
            "status": incident.get("status"),
            "urgency": incident.get("urgency"),
            "priority": incident.get("priority", {}).get("summary"),
            "service": incident.get("service", {}).get("summary"),
            "created_at": incident.get("created_at"),
            "resolved_at": incident.get("resolved_at"),
            "url": incident.get("html_url"),
            "assigned_to": [
                a.get("assignee", {}).get("summary")
                for a in incident.get("assignments", [])
            ],
        }
