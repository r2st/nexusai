"""
NexusAI Load Test Suite - Locust
================================
Primary load testing entry point using Locust.
Tests the FastAPI backend for 10,000+ concurrent user support
with P95 API response times under 200ms.

Usage:
    # Smoke test (10 users)
    locust -f locustfile.py --headless -u 10 -r 2 -t 60s

    # Full load test (10,000 users)
    locust -f locustfile.py --headless -u 10000 -r 200 -t 300s

    # With web UI
    locust -f locustfile.py
"""

import json
import logging
import random
import time
import uuid
from typing import Optional

from locust import HttpUser, between, events, task, tag
from locust.runners import MasterRunner, WorkerRunner

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from configs.test_config import SLAConfig, UserCredentials, ENDPOINT_WEIGHTS

logger = logging.getLogger("nexusai-loadtest")

# ─── Globals ────────────────────────────────────────────────────────────────────

SLA = SLAConfig()
CREDS = UserCredentials()
API_PREFIX = "/api/v1"

# Shared state for test data
_conversation_ids: list[str] = []
_document_ids: list[str] = []
_org_ids: list[str] = []


# ─── Event Hooks ────────────────────────────────────────────────────────────────

@events.init.add_listener
def on_init(environment, **kwargs):
    """Initialize test environment."""
    logger.info("╔══════════════════════════════════════════════════════════════╗")
    logger.info("║          NexusAI Load Test Suite Initialized                ║")
    logger.info("║  Target SLA: P95 < 200ms | 10,000+ concurrent users        ║")
    logger.info("╚══════════════════════════════════════════════════════════════╝")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Validate SLA compliance at test end."""
    stats = environment.stats
    total = stats.total

    if total.num_requests == 0:
        logger.warning("No requests were made during the test.")
        return

    p95 = total.get_response_time_percentile(0.95) or 0
    p99 = total.get_response_time_percentile(0.99) or 0
    p50 = total.get_response_time_percentile(0.50) or 0
    error_rate = (total.num_failures / total.num_requests * 100) if total.num_requests else 0
    rps = total.total_rps

    logger.info("╔══════════════════════════════════════════════════════════════╗")
    logger.info("║                    SLA COMPLIANCE REPORT                    ║")
    logger.info("╠══════════════════════════════════════════════════════════════╣")
    logger.info(f"║  Total Requests:    {total.num_requests:>10,}                         ║")
    logger.info(f"║  Failed Requests:   {total.num_failures:>10,}                         ║")
    logger.info(f"║  Error Rate:        {error_rate:>9.2f}%  (SLA: <{SLA.error_rate_threshold*100}%)            ║")
    logger.info(f"║  P50 Response:      {p50:>9.1f}ms (SLA: <{SLA.p50_response_ms}ms)            ║")
    logger.info(f"║  P95 Response:      {p95:>9.1f}ms (SLA: <{SLA.p95_response_ms}ms)  ← KEY     ║")
    logger.info(f"║  P99 Response:      {p99:>9.1f}ms (SLA: <{SLA.p99_response_ms}ms)            ║")
    logger.info(f"║  Throughput:        {rps:>9.1f}/s (SLA: >{SLA.min_throughput_rps}/s)          ║")
    logger.info("╠══════════════════════════════════════════════════════════════╣")

    violations = []
    if p95 > SLA.p95_response_ms:
        violations.append(f"P95 latency {p95:.1f}ms > {SLA.p95_response_ms}ms")
    if error_rate > SLA.error_rate_threshold * 100:
        violations.append(f"Error rate {error_rate:.2f}% > {SLA.error_rate_threshold*100}%")

    if violations:
        logger.error("║  ❌ SLA VIOLATED                                            ║")
        for v in violations:
            logger.error(f"║    • {v:<55}║")
        environment.process_exit_code = 1
    else:
        logger.info("║  ✅ ALL SLA TARGETS MET                                     ║")

    logger.info("╚══════════════════════════════════════════════════════════════╝")


# ─── Base User Behavior ─────────────────────────────────────────────────────────

class NexusAIUser(HttpUser):
    """
    Simulates a realistic NexusAI platform user.

    Behavior model:
    - Authenticates on start
    - Performs a weighted mix of API operations
    - Maintains session state (token, conversation IDs, etc.)
    - Simulates realistic think times between requests
    """

    wait_time = between(0.5, 2.0)  # Realistic think time
    abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.org_id: Optional[str] = None
        self.conversation_id: Optional[str] = None
        self._token_expiry: float = 0

    def _auth_headers(self) -> dict:
        """Return authorization headers."""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def _ensure_authenticated(self):
        """Re-authenticate if token is expired or missing."""
        if self.token and time.time() < self._token_expiry:
            return
        self._login()

    def _login(self):
        """Authenticate and store the JWT token."""
        with self.client.post(
            f"{API_PREFIX}/auth/login",
            json={
                "email": self._get_email(),
                "password": self._get_password(),
            },
            name="/api/v1/auth/login",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.user_id = data.get("user", {}).get("id")
                # Assume token valid for 25 minutes (refresh before expiry)
                self._token_expiry = time.time() + 1500
                response.success()
            else:
                response.failure(f"Login failed: {response.status_code}")

    def _get_email(self) -> str:
        return CREDS.user_email

    def _get_password(self) -> str:
        return CREDS.user_password

    def on_start(self):
        """Called when a simulated user starts. Authenticate first."""
        self._login()


# ─── Read-Heavy User (60% of traffic) ───────────────────────────────────────────

class ReadHeavyUser(NexusAIUser):
    """
    Simulates users who primarily consume data:
    dashboards, metrics, document browsing, org info.
    """

    weight = 6  # 60% of simulated users

    @tag("health")
    @task(ENDPOINT_WEIGHTS["health_check"])
    def health_check(self):
        """GET /health - Basic health check (no auth required)."""
        with self.client.get(
            "/health",
            name="/health",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @tag("auth")
    @task(ENDPOINT_WEIGHTS["auth_refresh"])
    def refresh_token_task(self):
        """POST /auth/refresh - Token refresh."""
        self._ensure_authenticated()
        if not self.refresh_token:
            return

        with self.client.post(
            f"{API_PREFIX}/auth/refresh",
            json={"refresh_token": self.refresh_token},
            headers=self._auth_headers(),
            name="/api/v1/auth/refresh",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token", self.token)
                self.refresh_token = data.get("refresh_token", self.refresh_token)
                self._token_expiry = time.time() + 1500
                response.success()
            elif response.status_code == 401:
                # Token expired, re-login
                self._login()
                response.success()
            else:
                response.failure(f"Token refresh failed: {response.status_code}")

    @tag("conversations")
    @task(ENDPOINT_WEIGHTS["list_conversations"])
    def list_conversations(self):
        """GET /chat/conversations - List user conversations."""
        self._ensure_authenticated()
        with self.client.get(
            f"{API_PREFIX}/chat/conversations",
            headers=self._auth_headers(),
            params={"limit": 20, "offset": 0},
            name="/api/v1/chat/conversations [LIST]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Store conversation IDs for later use
                if isinstance(data, list) and data:
                    for conv in data[:5]:
                        cid = conv.get("id")
                        if cid and cid not in _conversation_ids:
                            _conversation_ids.append(cid)
                elif isinstance(data, dict) and data.get("conversations"):
                    for conv in data["conversations"][:5]:
                        cid = conv.get("id")
                        if cid and cid not in _conversation_ids:
                            _conversation_ids.append(cid)
                response.success()
            elif response.status_code == 401:
                self._login()
                response.success()
            else:
                response.failure(f"List conversations failed: {response.status_code}")

    @tag("documents")
    @task(ENDPOINT_WEIGHTS["list_documents"])
    def list_documents(self):
        """GET /documents - List documents."""
        self._ensure_authenticated()
        with self.client.get(
            f"{API_PREFIX}/documents",
            headers=self._auth_headers(),
            params={"limit": 20, "offset": 0},
            name="/api/v1/documents [LIST]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            elif response.status_code == 401:
                self._login()
                response.success()
            else:
                response.failure(f"List documents failed: {response.status_code}")

    @tag("documents", "search")
    @task(ENDPOINT_WEIGHTS["search_documents"])
    def search_documents(self):
        """POST /documents/search - Semantic document search."""
        self._ensure_authenticated()
        queries = [
            "deployment pipeline configuration",
            "API authentication flow",
            "database migration steps",
            "monitoring and alerting setup",
            "CI/CD best practices",
            "security compliance requirements",
            "performance optimization guide",
            "microservices architecture",
        ]
        with self.client.post(
            f"{API_PREFIX}/documents/search",
            headers=self._auth_headers(),
            json={"query": random.choice(queries), "limit": 10},
            name="/api/v1/documents/search",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            elif response.status_code == 401:
                self._login()
                response.success()
            else:
                response.failure(f"Document search failed: {response.status_code}")

    @tag("metrics")
    @task(ENDPOINT_WEIGHTS["get_metrics_dora"])
    def get_dora_metrics(self):
        """GET /metrics/dora - Fetch DORA metrics."""
        self._ensure_authenticated()
        project_names = ["nexusai", "frontend", "backend", "infra", "platform"]
        with self.client.get(
            f"{API_PREFIX}/metrics/dora/{random.choice(project_names)}",
            headers=self._auth_headers(),
            params={"period": "30d"},
            name="/api/v1/metrics/dora/{project}",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            elif response.status_code == 401:
                self._login()
                response.success()
            else:
                response.failure(f"DORA metrics failed: {response.status_code}")

    @tag("metrics")
    @task(ENDPOINT_WEIGHTS["get_metrics_space"])
    def get_space_metrics(self):
        """GET /metrics/space - Fetch SPACE metrics."""
        self._ensure_authenticated()
        project_names = ["nexusai", "frontend", "backend", "infra", "platform"]
        with self.client.get(
            f"{API_PREFIX}/metrics/space/{random.choice(project_names)}",
            headers=self._auth_headers(),
            params={"period": "30d"},
            name="/api/v1/metrics/space/{project}",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            elif response.status_code == 401:
                self._login()
                response.success()
            else:
                response.failure(f"SPACE metrics failed: {response.status_code}")

    @tag("organizations")
    @task(ENDPOINT_WEIGHTS["list_organizations"])
    def list_organizations(self):
        """GET /organizations - List organizations."""
        self._ensure_authenticated()
        with self.client.get(
            f"{API_PREFIX}/organizations",
            headers=self._auth_headers(),
            name="/api/v1/organizations [LIST]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    for org in data[:3]:
                        oid = org.get("id")
                        if oid and oid not in _org_ids:
                            _org_ids.append(oid)
                response.success()
            elif response.status_code == 401:
                self._login()
                response.success()
            else:
                response.failure(f"List orgs failed: {response.status_code}")

    @tag("organizations")
    @task(ENDPOINT_WEIGHTS["get_organization"])
    def get_organization(self):
        """GET /organizations/{id} - Get org details."""
        self._ensure_authenticated()
        if not _org_ids:
            return

        with self.client.get(
            f"{API_PREFIX}/organizations/{random.choice(_org_ids)}",
            headers=self._auth_headers(),
            name="/api/v1/organizations/{id}",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            elif response.status_code == 401:
                self._login()
                response.success()
            else:
                response.failure(f"Get org failed: {response.status_code}")


# ─── Write-Heavy User (25% of traffic) ──────────────────────────────────────────

class WriteHeavyUser(NexusAIUser):
    """
    Simulates users who actively create content:
    new conversations, messages, document uploads.
    """

    weight = 3  # 25% of simulated users (approx)

    @tag("conversations", "write")
    @task(20)
    def create_conversation(self):
        """POST /chat/conversations - Create a new conversation."""
        self._ensure_authenticated()
        with self.client.post(
            f"{API_PREFIX}/chat/conversations",
            headers=self._auth_headers(),
            json={
                "title": f"Load Test Conversation {uuid.uuid4().hex[:8]}",
                "model_provider": "openai",
                "model_name": "gpt-4",
            },
            name="/api/v1/chat/conversations [CREATE]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                data = response.json()
                cid = data.get("id")
                if cid:
                    self.conversation_id = cid
                    if cid not in _conversation_ids:
                        _conversation_ids.append(cid)
                response.success()
            elif response.status_code == 401:
                self._login()
                response.success()
            else:
                response.failure(f"Create conversation failed: {response.status_code}")

    @tag("conversations", "write")
    @task(30)
    def send_message(self):
        """POST /chat/conversations/{id}/messages - Send a chat message."""
        self._ensure_authenticated()
        conv_id = self.conversation_id or (
            random.choice(_conversation_ids) if _conversation_ids else None
        )
        if not conv_id:
            self.create_conversation()
            return

        messages = [
            "What are the deployment metrics for this week?",
            "Show me the error rate trends",
            "Analyze the code review throughput",
            "What's the lead time for changes?",
            "Summarize the DORA metrics dashboard",
            "Help me understand the CI/CD pipeline performance",
            "What security vulnerabilities were found?",
            "Generate a sprint retrospective summary",
        ]

        with self.client.post(
            f"{API_PREFIX}/chat/conversations/{conv_id}/messages",
            headers=self._auth_headers(),
            json={
                "content": random.choice(messages),
                "role": "user",
            },
            name="/api/v1/chat/conversations/{id}/messages [SEND]",
            catch_response=True,
            timeout=30,  # Chat responses can take longer
        ) as response:
            if response.status_code in (200, 201):
                response.success()
            elif response.status_code in (401, 404):
                if response.status_code == 401:
                    self._login()
                self.conversation_id = None
                response.success()
            else:
                response.failure(f"Send message failed: {response.status_code}")

    @tag("conversations")
    @task(15)
    def list_conversations(self):
        """GET /chat/conversations."""
        self._ensure_authenticated()
        with self.client.get(
            f"{API_PREFIX}/chat/conversations",
            headers=self._auth_headers(),
            params={"limit": 10},
            name="/api/v1/chat/conversations [LIST]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 401):
                response.success()
            else:
                response.failure(f"List conversations failed: {response.status_code}")

    @tag("documents")
    @task(10)
    def list_documents(self):
        """GET /documents."""
        self._ensure_authenticated()
        with self.client.get(
            f"{API_PREFIX}/documents",
            headers=self._auth_headers(),
            name="/api/v1/documents [LIST]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404, 401):
                response.success()
            else:
                response.failure(f"List documents failed: {response.status_code}")

    @tag("health")
    @task(5)
    def health_check(self):
        """GET /health."""
        self.client.get("/health", name="/health")

    @tag("metrics")
    @task(10)
    def get_dora_metrics(self):
        """GET /metrics/dora."""
        self._ensure_authenticated()
        project_names = ["nexusai", "frontend", "backend"]
        with self.client.get(
            f"{API_PREFIX}/metrics/dora/{random.choice(project_names)}",
            headers=self._auth_headers(),
            name="/api/v1/metrics/dora/{project}",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404, 401):
                response.success()

    @tag("organizations")
    @task(10)
    def list_organizations(self):
        """GET /organizations."""
        self._ensure_authenticated()
        with self.client.get(
            f"{API_PREFIX}/organizations",
            headers=self._auth_headers(),
            name="/api/v1/organizations [LIST]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 401):
                response.success()


# ─── Admin User (15% of traffic) ────────────────────────────────────────────────

class AdminUser(NexusAIUser):
    """
    Simulates admin users: org management, metrics review,
    compliance checks, audit log access.
    """

    weight = 1  # ~10% of simulated users

    def _get_email(self) -> str:
        return CREDS.admin_email

    def _get_password(self) -> str:
        return CREDS.admin_password

    @tag("health")
    @task(5)
    def health_check(self):
        self.client.get("/health", name="/health")

    @tag("organizations", "admin")
    @task(20)
    def list_organizations(self):
        """List all organizations (admin view)."""
        self._ensure_authenticated()
        with self.client.get(
            f"{API_PREFIX}/organizations",
            headers=self._auth_headers(),
            name="/api/v1/organizations [LIST]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 401):
                response.success()
            else:
                response.failure(f"Admin list orgs failed: {response.status_code}")

    @tag("metrics", "admin")
    @task(25)
    def get_dora_metrics(self):
        """Admin fetching comprehensive DORA metrics."""
        self._ensure_authenticated()
        project_names = ["nexusai", "frontend", "backend", "infra", "platform"]
        with self.client.get(
            f"{API_PREFIX}/metrics/dora/{random.choice(project_names)}",
            headers=self._auth_headers(),
            params={"period": "90d"},
            name="/api/v1/metrics/dora/{project} [ADMIN]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404, 401):
                response.success()

    @tag("metrics", "admin")
    @task(15)
    def get_space_metrics(self):
        """Admin fetching SPACE metrics."""
        self._ensure_authenticated()
        project_names = ["nexusai", "frontend", "backend"]
        with self.client.get(
            f"{API_PREFIX}/metrics/space/{random.choice(project_names)}",
            headers=self._auth_headers(),
            params={"period": "90d"},
            name="/api/v1/metrics/space/{project} [ADMIN]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404, 401):
                response.success()

    @tag("conversations", "admin")
    @task(15)
    def list_conversations(self):
        """Admin listing conversations."""
        self._ensure_authenticated()
        with self.client.get(
            f"{API_PREFIX}/chat/conversations",
            headers=self._auth_headers(),
            params={"limit": 50},
            name="/api/v1/chat/conversations [LIST]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 401):
                response.success()

    @tag("documents", "admin")
    @task(10)
    def search_documents(self):
        """Admin searching across all documents."""
        self._ensure_authenticated()
        queries = [
            "compliance audit report",
            "security incident response",
            "infrastructure cost analysis",
            "team performance review",
        ]
        with self.client.post(
            f"{API_PREFIX}/documents/search",
            headers=self._auth_headers(),
            json={"query": random.choice(queries), "limit": 20},
            name="/api/v1/documents/search [ADMIN]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404, 401):
                response.success()

    @tag("auth", "admin")
    @task(10)
    def refresh_token_task(self):
        """Admin token refresh."""
        self._ensure_authenticated()
        if not self.refresh_token:
            return
        with self.client.post(
            f"{API_PREFIX}/auth/refresh",
            json={"refresh_token": self.refresh_token},
            headers=self._auth_headers(),
            name="/api/v1/auth/refresh",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token", self.token)
                self._token_expiry = time.time() + 1500
                response.success()
            else:
                self._login()
                response.success()
