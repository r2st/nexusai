"""
Kubernetes Connector

Connector for Kubernetes cluster integration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncIterator
import asyncio
import logging
import ssl
import base64

import httpx

from .base import BaseConnector, ConnectorConfig, ConnectorStatus, WebhookEvent

logger = logging.getLogger(__name__)


@dataclass
class KubernetesConfig(ConnectorConfig):
    """Kubernetes-specific configuration."""
    # Cluster connection
    api_server: str = ""  # e.g., https://kubernetes.default.svc
    
    # Authentication
    token: str = ""  # Service account token
    certificate_authority: str = ""  # CA cert (base64 encoded)
    client_certificate: str = ""  # Client cert (base64 encoded)
    client_key: str = ""  # Client key (base64 encoded)
    
    # Kubeconfig (alternative)
    kubeconfig_path: str = ""
    context: str = ""
    
    # Options
    namespace: str = "default"
    verify_ssl: bool = True
    
    # Watch settings
    watch_deployments: bool = True
    watch_pods: bool = True
    watch_events: bool = True
    label_selector: str = ""


class KubernetesConnector(BaseConnector):
    """
    Kubernetes connector for cluster integration.
    
    Features:
    - Resource CRUD operations
    - Watch API for real-time updates
    - Deployment management
    - Pod logs retrieval
    - Event monitoring
    """
    
    name = "kubernetes"
    display_name = "Kubernetes"
    
    def __init__(self, config: KubernetesConfig):
        super().__init__(config)
        self.config: KubernetesConfig = config
        self._client: Optional[httpx.AsyncClient] = None
    
    async def connect(self) -> bool:
        """Establish connection to Kubernetes cluster."""
        try:
            headers = {}
            
            # Use token authentication
            if self.config.token:
                headers["Authorization"] = f"Bearer {self.config.token}"
            
            # Configure SSL
            verify: Any = self.config.verify_ssl
            
            self._client = httpx.AsyncClient(
                base_url=self.config.api_server,
                headers=headers,
                verify=verify,
                timeout=30.0,
            )
            
            # Test connection by getting API versions
            response = await self._client.get("/api")
            
            if response.status_code == 200:
                self.status = ConnectorStatus.CONNECTED
                logger.info(f"Connected to Kubernetes: {self.config.api_server}")
                return True
            else:
                self.status = ConnectorStatus.ERROR
                self.last_error = f"Auth failed: {response.status_code}"
                return False
                
        except Exception as e:
            self.status = ConnectorStatus.ERROR
            self.last_error = str(e)
            logger.error(f"Kubernetes connection failed: {e}")
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
            response = await self._client.get("/healthz")
            return response.status_code == 200
        except Exception:
            return False
    
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Kubernetes uses admission webhooks with different verification."""
        return True
    
    async def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> WebhookEvent:
        """Process Kubernetes webhook event."""
        event = WebhookEvent(
            source=self.name,
            event_type=event_type,
            payload=payload,
            received_at=datetime.utcnow(),
        )
        
        obj = payload.get("object", {})
        metadata = obj.get("metadata", {})
        
        event.resource_id = metadata.get("uid")
        event.resource_type = obj.get("kind", "").lower()
        event.metadata["name"] = metadata.get("name")
        event.metadata["namespace"] = metadata.get("namespace")
        
        return event
    
    # Helper method for API paths
    def _ns_path(self, resource: str, namespace: Optional[str] = None) -> str:
        """Build namespaced resource path."""
        ns = namespace or self.config.namespace
        return f"/api/v1/namespaces/{ns}/{resource}"
    
    def _apps_ns_path(self, resource: str, namespace: Optional[str] = None) -> str:
        """Build apps/v1 namespaced resource path."""
        ns = namespace or self.config.namespace
        return f"/apis/apps/v1/namespaces/{ns}/{resource}"
    
    # Pod Operations
    
    async def get_pods(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get pods in namespace."""
        if not self._client:
            return []
        
        params: Dict[str, str] = {}
        if label_selector:
            params["labelSelector"] = label_selector
        if field_selector:
            params["fieldSelector"] = field_selector
        
        response = await self._client.get(
            self._ns_path("pods", namespace),
            params=params,
        )
        
        if response.status_code == 200:
            return response.json().get("items", [])
        return []
    
    async def get_pod(
        self,
        name: str,
        namespace: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get pod by name."""
        if not self._client:
            return None
        
        response = await self._client.get(
            f"{self._ns_path('pods', namespace)}/{name}"
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    
    async def get_pod_logs(
        self,
        name: str,
        namespace: Optional[str] = None,
        container: Optional[str] = None,
        tail_lines: int = 100,
        since_seconds: Optional[int] = None,
        timestamps: bool = False,
    ) -> str:
        """Get pod logs."""
        if not self._client:
            return ""
        
        params: Dict[str, Any] = {"tailLines": tail_lines}
        if container:
            params["container"] = container
        if since_seconds:
            params["sinceSeconds"] = since_seconds
        if timestamps:
            params["timestamps"] = "true"
        
        response = await self._client.get(
            f"{self._ns_path('pods', namespace)}/{name}/log",
            params=params,
        )
        
        if response.status_code == 200:
            return response.text
        return ""
    
    async def delete_pod(
        self,
        name: str,
        namespace: Optional[str] = None,
        grace_period: int = 30,
    ) -> bool:
        """Delete a pod."""
        if not self._client:
            return False
        
        response = await self._client.delete(
            f"{self._ns_path('pods', namespace)}/{name}",
            params={"gracePeriodSeconds": grace_period},
        )
        
        return response.status_code in (200, 202)
    
    # Deployment Operations
    
    async def get_deployments(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get deployments in namespace."""
        if not self._client:
            return []
        
        params: Dict[str, str] = {}
        if label_selector:
            params["labelSelector"] = label_selector
        
        response = await self._client.get(
            self._apps_ns_path("deployments", namespace),
            params=params,
        )
        
        if response.status_code == 200:
            return response.json().get("items", [])
        return []
    
    async def get_deployment(
        self,
        name: str,
        namespace: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get deployment by name."""
        if not self._client:
            return None
        
        response = await self._client.get(
            f"{self._apps_ns_path('deployments', namespace)}/{name}"
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    
    async def scale_deployment(
        self,
        name: str,
        replicas: int,
        namespace: Optional[str] = None,
    ) -> bool:
        """Scale a deployment."""
        if not self._client:
            return False
        
        patch = {
            "spec": {"replicas": replicas}
        }
        
        response = await self._client.patch(
            f"{self._apps_ns_path('deployments', namespace)}/{name}",
            json=patch,
            headers={"Content-Type": "application/strategic-merge-patch+json"},
        )
        
        return response.status_code == 200
    
    async def restart_deployment(
        self,
        name: str,
        namespace: Optional[str] = None,
    ) -> bool:
        """Restart a deployment by updating annotation."""
        if not self._client:
            return False
        
        patch = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": datetime.utcnow().isoformat()
                        }
                    }
                }
            }
        }
        
        response = await self._client.patch(
            f"{self._apps_ns_path('deployments', namespace)}/{name}",
            json=patch,
            headers={"Content-Type": "application/strategic-merge-patch+json"},
        )
        
        return response.status_code == 200
    
    async def update_deployment_image(
        self,
        name: str,
        container: str,
        image: str,
        namespace: Optional[str] = None,
    ) -> bool:
        """Update deployment container image."""
        if not self._client:
            return False
        
        # Get current deployment
        deployment = await self.get_deployment(name, namespace)
        if not deployment:
            return False
        
        # Update image
        containers = deployment["spec"]["template"]["spec"]["containers"]
        for c in containers:
            if c["name"] == container:
                c["image"] = image
                break
        
        response = await self._client.put(
            f"{self._apps_ns_path('deployments', namespace)}/{name}",
            json=deployment,
        )
        
        return response.status_code == 200
    
    # Service Operations
    
    async def get_services(
        self,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get services in namespace."""
        if not self._client:
            return []
        
        response = await self._client.get(
            self._ns_path("services", namespace)
        )
        
        if response.status_code == 200:
            return response.json().get("items", [])
        return []
    
    # ConfigMap Operations
    
    async def get_configmaps(
        self,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get configmaps in namespace."""
        if not self._client:
            return []
        
        response = await self._client.get(
            self._ns_path("configmaps", namespace)
        )
        
        if response.status_code == 200:
            return response.json().get("items", [])
        return []
    
    async def create_configmap(
        self,
        name: str,
        data: Dict[str, str],
        namespace: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a configmap."""
        if not self._client:
            return None
        
        configmap = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": name},
            "data": data,
        }
        
        response = await self._client.post(
            self._ns_path("configmaps", namespace),
            json=configmap,
        )
        
        if response.status_code == 201:
            return response.json()
        return None
    
    # Event Operations
    
    async def get_events(
        self,
        namespace: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get cluster events."""
        if not self._client:
            return []
        
        params: Dict[str, str] = {}
        if field_selector:
            params["fieldSelector"] = field_selector
        
        path = self._ns_path("events", namespace) if namespace else "/api/v1/events"
        
        response = await self._client.get(path, params=params)
        
        if response.status_code == 200:
            return response.json().get("items", [])
        return []
    
    async def get_events_for_resource(
        self,
        name: str,
        kind: str,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get events for a specific resource."""
        field_selector = f"involvedObject.name={name},involvedObject.kind={kind}"
        return await self.get_events(namespace, field_selector)
    
    # Namespace Operations
    
    async def get_namespaces(self) -> List[Dict[str, Any]]:
        """Get all namespaces."""
        if not self._client:
            return []
        
        response = await self._client.get("/api/v1/namespaces")
        
        if response.status_code == 200:
            return response.json().get("items", [])
        return []
    
    # Cluster Info
    
    async def get_cluster_info(self) -> Dict[str, Any]:
        """Get cluster information."""
        if not self._client:
            return {}
        
        info: Dict[str, Any] = {}
        
        # Get version
        response = await self._client.get("/version")
        if response.status_code == 200:
            info["version"] = response.json()
        
        # Get nodes
        response = await self._client.get("/api/v1/nodes")
        if response.status_code == 200:
            nodes = response.json().get("items", [])
            info["nodes"] = len(nodes)
            info["node_names"] = [n["metadata"]["name"] for n in nodes]
        
        return info
    
    def normalize_event(self, event: WebhookEvent) -> Dict[str, Any]:
        """Convert Kubernetes event to canonical format."""
        obj = event.payload.get("object", {})
        metadata = obj.get("metadata", {})
        status = obj.get("status", {})
        
        return {
            "source": "kubernetes",
            "type": event.resource_type,
            "external_id": metadata.get("uid"),
            "name": metadata.get("name"),
            "namespace": metadata.get("namespace"),
            "labels": metadata.get("labels", {}),
            "annotations": metadata.get("annotations", {}),
            "created_at": metadata.get("creationTimestamp"),
            "status": status,
            "event_type": event.event_type,
        }
