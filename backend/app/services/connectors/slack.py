"""
Slack Connector

Connector for Slack workspace integration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import hashlib
import hmac
import logging
import time

import httpx

from .base import BaseConnector, ConnectorConfig, ConnectorStatus, DEFAULT_HTTP_TIMEOUT, WebhookEvent

logger = logging.getLogger(__name__)


@dataclass
class SlackConfig(ConnectorConfig):
    """Slack-specific configuration."""
    # OAuth tokens
    bot_token: str = ""
    user_token: str = ""
    app_token: str = ""  # For Socket Mode
    
    # App credentials
    client_id: str = ""
    client_secret: str = ""
    signing_secret: str = ""
    
    # Channels to monitor
    channels: List[str] = field(default_factory=list)
    
    # Event subscriptions
    subscribe_to_messages: bool = True
    subscribe_to_reactions: bool = True
    subscribe_to_threads: bool = True


class SlackConnector(BaseConnector):
    """
    Slack connector for workspace integration.
    
    Features:
    - Message sending/receiving
    - Channel management
    - User lookup
    - Webhook events
    - Interactive components
    """
    
    name = "slack"
    display_name = "Slack"
    
    def __init__(self, config: SlackConfig):
        super().__init__(config)
        self.config: SlackConfig = config
        self._client: Optional[httpx.AsyncClient] = None
    
    async def connect(self) -> bool:
        """Establish connection to Slack."""
        try:
            self._client = httpx.AsyncClient(
                base_url="https://slack.com/api",
                headers={
                    "Authorization": f"Bearer {self.config.bot_token}",
                    "Content-Type": "application/json",
                },
                timeout=DEFAULT_HTTP_TIMEOUT,
            )
            
            # Test connection
            response = await self._client.post("/auth.test")
            data = response.json()
            
            if data.get("ok"):
                self.status = ConnectorStatus.CONNECTED
                logger.info(f"Connected to Slack workspace: {data.get('team')}")
                return True
            else:
                self.status = ConnectorStatus.ERROR
                self.last_error = data.get("error", "Unknown error")
                return False
                
        except Exception as e:
            self.status = ConnectorStatus.ERROR
            self.last_error = str(e)
            logger.error(f"Slack connection failed: {e}")
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
            response = await self._client.post("/auth.test")
            return response.json().get("ok", False)
        except Exception:
            return False
    
    def verify_webhook(self, payload: bytes, signature: str, timestamp: str) -> bool:
        """Verify Slack request signature."""
        if not self.config.signing_secret:
            return True
        
        # Check timestamp (prevent replay attacks)
        request_timestamp = int(timestamp)
        if abs(time.time() - request_timestamp) > 60 * 5:
            return False
        
        # Compute signature
        sig_basestring = f"v0:{timestamp}:{payload.decode()}"
        computed = "v0=" + hmac.new(
            self.config.signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        return hmac.compare_digest(computed, signature)
    
    async def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> WebhookEvent:
        """Process Slack webhook event."""
        event = WebhookEvent(
            source=self.name,
            event_type=event_type,
            payload=payload,
            received_at=datetime.utcnow(),
        )
        
        # Handle different event types
        slack_event = payload.get("event", {})
        
        if event_type == "message":
            event.resource_id = slack_event.get("ts")
            event.resource_type = "message"
            event.metadata["channel"] = slack_event.get("channel")
            event.metadata["user"] = slack_event.get("user")
            event.metadata["text"] = slack_event.get("text")
        
        elif event_type == "reaction_added":
            event.resource_id = slack_event.get("item", {}).get("ts")
            event.resource_type = "reaction"
            event.metadata["reaction"] = slack_event.get("reaction")
            event.metadata["user"] = slack_event.get("user")
        
        return event
    
    # Message Operations
    
    async def send_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
        thread_ts: Optional[str] = None,
        unfurl_links: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Send a message to a channel."""
        if not self._client:
            return None
        
        payload = {
            "channel": channel,
            "text": text,
            "unfurl_links": unfurl_links,
        }
        
        if blocks:
            payload["blocks"] = blocks
        
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        response = await self._client.post("/chat.postMessage", json=payload)
        data = response.json()
        
        if data.get("ok"):
            return data
        
        logger.error(f"Failed to send message: {data.get('error')}")
        return None
    
    async def update_message(
        self,
        channel: str,
        ts: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Update an existing message."""
        if not self._client:
            return False
        
        payload = {
            "channel": channel,
            "ts": ts,
            "text": text,
        }
        
        if blocks:
            payload["blocks"] = blocks
        
        response = await self._client.post("/chat.update", json=payload)
        return response.json().get("ok", False)
    
    async def delete_message(self, channel: str, ts: str) -> bool:
        """Delete a message."""
        if not self._client:
            return False
        
        response = await self._client.post(
            "/chat.delete",
            json={"channel": channel, "ts": ts},
        )
        return response.json().get("ok", False)
    
    async def add_reaction(self, channel: str, ts: str, reaction: str) -> bool:
        """Add a reaction to a message."""
        if not self._client:
            return False
        
        response = await self._client.post(
            "/reactions.add",
            json={"channel": channel, "timestamp": ts, "name": reaction},
        )
        return response.json().get("ok", False)
    
    # Channel Operations
    
    async def get_channels(
        self,
        types: str = "public_channel,private_channel",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get list of channels."""
        if not self._client:
            return []
        
        response = await self._client.get(
            "/conversations.list",
            params={"types": types, "limit": limit},
        )
        data = response.json()
        
        if data.get("ok"):
            return data.get("channels", [])
        return []
    
    async def get_channel_info(self, channel: str) -> Optional[Dict[str, Any]]:
        """Get channel information."""
        if not self._client:
            return None
        
        response = await self._client.get(
            "/conversations.info",
            params={"channel": channel},
        )
        data = response.json()
        
        if data.get("ok"):
            return data.get("channel")
        return None
    
    async def get_channel_history(
        self,
        channel: str,
        limit: int = 100,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get channel message history."""
        if not self._client:
            return []
        
        params = {"channel": channel, "limit": limit}
        if oldest:
            params["oldest"] = oldest
        if latest:
            params["latest"] = latest
        
        response = await self._client.get("/conversations.history", params=params)
        data = response.json()
        
        if data.get("ok"):
            return data.get("messages", [])
        return []
    
    async def join_channel(self, channel: str) -> bool:
        """Join a channel."""
        if not self._client:
            return False
        
        response = await self._client.post(
            "/conversations.join",
            json={"channel": channel},
        )
        return response.json().get("ok", False)
    
    # User Operations
    
    async def get_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of users."""
        if not self._client:
            return []
        
        response = await self._client.get("/users.list", params={"limit": limit})
        data = response.json()
        
        if data.get("ok"):
            return data.get("members", [])
        return []
    
    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information."""
        if not self._client:
            return None
        
        response = await self._client.get("/users.info", params={"user": user_id})
        data = response.json()
        
        if data.get("ok"):
            return data.get("user")
        return None
    
    async def lookup_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find user by email."""
        if not self._client:
            return None
        
        response = await self._client.get("/users.lookupByEmail", params={"email": email})
        data = response.json()
        
        if data.get("ok"):
            return data.get("user")
        return None
    
    # Interactive Components
    
    async def open_modal(
        self,
        trigger_id: str,
        view: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Open a modal view."""
        if not self._client:
            return None
        
        response = await self._client.post(
            "/views.open",
            json={"trigger_id": trigger_id, "view": view},
        )
        data = response.json()
        
        if data.get("ok"):
            return data.get("view")
        return None
    
    async def update_modal(
        self,
        view_id: str,
        view: Dict[str, Any],
    ) -> bool:
        """Update a modal view."""
        if not self._client:
            return False
        
        response = await self._client.post(
            "/views.update",
            json={"view_id": view_id, "view": view},
        )
        return response.json().get("ok", False)
    
    # Block Kit Builders
    
    @staticmethod
    def text_block(text: str, block_type: str = "mrkdwn") -> Dict[str, Any]:
        """Create a text block."""
        return {
            "type": "section",
            "text": {"type": block_type, "text": text},
        }
    
    @staticmethod
    def button_block(
        text: str,
        action_id: str,
        value: str,
        style: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a button element."""
        button = {
            "type": "button",
            "text": {"type": "plain_text", "text": text},
            "action_id": action_id,
            "value": value,
        }
        if style:
            button["style"] = style
        return button
    
    @staticmethod
    def divider_block() -> Dict[str, Any]:
        """Create a divider block."""
        return {"type": "divider"}
    
    def normalize_event(self, event: WebhookEvent) -> Dict[str, Any]:
        """Convert Slack event to canonical format."""
        slack_event = event.payload.get("event", {})
        
        return {
            "source": "slack",
            "type": "message",
            "external_id": slack_event.get("ts"),
            "channel": slack_event.get("channel"),
            "user_id": slack_event.get("user"),
            "text": slack_event.get("text"),
            "thread_ts": slack_event.get("thread_ts"),
            "timestamp": datetime.fromtimestamp(float(slack_event.get("ts", 0))).isoformat(),
        }
