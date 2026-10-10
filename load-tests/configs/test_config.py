"""
Load Test Configuration
-----------------------
Central configuration for all load testing scenarios.
Supports environment variable overrides for CI/CD integration.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TestProfile(Enum):
    SMOKE = "smoke"           # Quick sanity check: 10 users, 1 minute
    LOAD = "load"             # Standard load: 1,000 users, 5 minutes
    STRESS = "stress"         # Stress test: 5,000 users, 10 minutes
    SPIKE = "spike"           # Spike test: 0 → 10,000 users in 30s
    ENDURANCE = "endurance"   # Soak test: 2,000 users, 30 minutes
    BREAKPOINT = "breakpoint" # Find breaking point: ramp to 15,000 users


@dataclass
class TargetConfig:
    """API target configuration."""
    base_url: str = os.getenv("TARGET_URL", "http://localhost:8000")
    api_prefix: str = "/api/v1"
    ws_url: str = os.getenv("WS_URL", "ws://localhost:8000/api/v1/ws")


@dataclass
class SLAConfig:
    """Service Level Agreement thresholds."""
    p50_response_ms: int = 100       # Median response time
    p95_response_ms: int = 200       # P95 response time (primary SLA)
    p99_response_ms: int = 500       # P99 response time
    max_response_ms: int = 2000      # Absolute maximum
    error_rate_threshold: float = 0.01   # Max 1% error rate
    min_throughput_rps: int = 500     # Minimum requests per second
    target_concurrent_users: int = 10_000


@dataclass
class UserCredentials:
    """Test user credentials (dev-seeded users)."""
    admin_email: str = "admin@nexusai.dev"
    admin_password: str = "admin123"
    user_email: str = "user@nexusai.dev"
    user_password: str = "user123"
    viewer_email: str = "viewer@nexusai.dev"
    viewer_password: str = "viewer123"


@dataclass
class ProfileConfig:
    """Configuration for each test profile."""
    users: int
    spawn_rate: int             # Users spawned per second
    duration_seconds: int
    stages: list = field(default_factory=list)  # For staged load patterns


# Pre-defined test profiles
PROFILES: dict[str, ProfileConfig] = {
    TestProfile.SMOKE.value: ProfileConfig(
        users=10,
        spawn_rate=2,
        duration_seconds=60,
    ),
    TestProfile.LOAD.value: ProfileConfig(
        users=1_000,
        spawn_rate=50,
        duration_seconds=300,
    ),
    TestProfile.STRESS.value: ProfileConfig(
        users=5_000,
        spawn_rate=100,
        duration_seconds=600,
    ),
    TestProfile.SPIKE.value: ProfileConfig(
        users=10_000,
        spawn_rate=500,
        duration_seconds=300,
        stages=[
            {"duration": 60, "users": 100},     # Warm up
            {"duration": 30, "users": 10_000},   # Spike!
            {"duration": 120, "users": 10_000},  # Hold
            {"duration": 60, "users": 100},      # Cool down
        ],
    ),
    TestProfile.ENDURANCE.value: ProfileConfig(
        users=2_000,
        spawn_rate=50,
        duration_seconds=1800,
    ),
    TestProfile.BREAKPOINT.value: ProfileConfig(
        users=15_000,
        spawn_rate=200,
        duration_seconds=900,
        stages=[
            {"duration": 60, "users": 1_000},
            {"duration": 60, "users": 3_000},
            {"duration": 60, "users": 5_000},
            {"duration": 60, "users": 7_500},
            {"duration": 60, "users": 10_000},
            {"duration": 60, "users": 12_000},
            {"duration": 60, "users": 15_000},
            {"duration": 120, "users": 15_000},
            {"duration": 60, "users": 0},
        ],
    ),
}


# Endpoint weights (percentage of traffic each endpoint receives)
ENDPOINT_WEIGHTS: dict[str, int] = {
    "health_check": 5,
    "auth_login": 5,
    "auth_refresh": 10,
    "list_conversations": 15,
    "create_conversation": 5,
    "send_message": 10,
    "list_documents": 10,
    "search_documents": 10,
    "get_metrics_dora": 10,
    "get_metrics_space": 5,
    "list_organizations": 10,
    "get_organization": 5,
}


def get_config(profile: str = "smoke") -> tuple[TargetConfig, SLAConfig, ProfileConfig]:
    """Get configuration for a given test profile."""
    target = TargetConfig()
    sla = SLAConfig()
    prof = PROFILES.get(profile, PROFILES["smoke"])
    return target, sla, prof
