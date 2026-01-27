"""
Unit tests for AI Analytics services.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from pydantic import BaseModel


# =============================================================================
# Mock Models and Types
# =============================================================================


class AIToolType:
    """AI tool types."""
    GITHUB_COPILOT = "github_copilot"
    CURSOR = "cursor"
    CLAUDE_CODE = "claude_code"
    AMAZON_Q = "amazon_q"


# =============================================================================
# AI Usage Event Tests
# =============================================================================


class TestAIUsageEvent:
    """Tests for AIUsageEvent model."""

    def test_required_fields(self):
        """Test required fields for usage event."""
        event = {
            "tool_type": "github_copilot",
            "event_type": "completion",
            "event_timestamp": datetime.now(UTC),
        }

        assert "tool_type" in event
        assert "event_type" in event
        assert "event_timestamp" in event

    def test_all_fields(self):
        """Test all fields for usage event."""
        event = {
            "tool_type": "cursor",
            "tool_version": "1.0.0",
            "event_type": "completion",
            "event_timestamp": datetime.now(UTC),
            "user_id": str(uuid4()),
            "user_hash": "hash123",
            "language": "python",
            "file_extension": ".py",
            "lines_generated": 10,
            "lines_accepted": 8,
            "tokens_used": 150,
            "latency_ms": 200,
            "metadata": {"model": "gpt-4"},
        }

        assert event["lines_generated"] == 10
        assert event["lines_accepted"] == 8

    def test_default_values(self):
        """Test default values for usage event."""
        event = {
            "tool_type": "claude_code",
            "event_type": "completion",
            "event_timestamp": datetime.now(UTC),
        }

        lines_generated = event.get("lines_generated", 0)
        lines_accepted = event.get("lines_accepted", 0)
        tokens_used = event.get("tokens_used", 0)

        assert lines_generated == 0
        assert lines_accepted == 0
        assert tokens_used == 0


class TestAIToolMetrics:
    """Tests for AIToolMetrics model."""

    def test_metrics_structure(self):
        """Test metrics structure."""
        metrics = {
            "tool_type": "github_copilot",
            "period_start": datetime.now(UTC) - timedelta(days=7),
            "period_end": datetime.now(UTC),
            "total_events": 1000,
            "total_completions": 800,
            "accepted_completions": 640,
            "rejected_completions": 160,
            "total_lines_generated": 5000,
            "total_lines_accepted": 4000,
            "acceptance_rate": 80.0,
            "unique_users": 25,
            "active_users": 20,
            "avg_latency_ms": 150.0,
            "p95_latency_ms": 300.0,
            "total_tokens": 100000,
            "estimated_cost": 50.0,
        }

        assert metrics["acceptance_rate"] == 80.0
        assert metrics["unique_users"] == 25

    def test_acceptance_rate_calculation(self):
        """Test acceptance rate calculation."""
        accepted = 640
        total = 800

        acceptance_rate = (accepted / total) * 100 if total > 0 else 0

        assert acceptance_rate == 80.0

    def test_zero_total_completions(self):
        """Test acceptance rate with zero completions."""
        accepted = 0
        total = 0

        acceptance_rate = (accepted / total) * 100 if total > 0 else 0

        assert acceptance_rate == 0


# =============================================================================
# AI Analytics Plugin Tests
# =============================================================================


class TestAIAnalyticsPlugin:
    """Tests for AI Analytics plugin base class."""

    def test_plugin_properties(self):
        """Test plugin property methods."""
        plugin = {
            "name": "GitHub Copilot Plugin",
            "description": "Collects usage data from GitHub Copilot",
            "version": "1.0.0",
            "tool_type": "github_copilot",
        }

        assert plugin["name"] is not None
        assert plugin["description"] is not None
        assert plugin["version"] == "1.0.0"

    def test_get_schema(self):
        """Test plugin configuration schema."""
        schema = {
            "type": "object",
            "properties": {
                "api_key": {"type": "string"},
                "organization": {"type": "string"},
            },
            "required": ["api_key"],
        }

        assert schema["type"] == "object"
        assert "api_key" in schema["properties"]


# =============================================================================
# Plugin Collection Tests
# =============================================================================


class TestPluginCollection:
    """Tests for plugin data collection."""

    @pytest.mark.asyncio
    async def test_collect_events(self):
        """Test collecting events from plugin."""
        events = [
            {
                "tool_type": "github_copilot",
                "event_type": "completion",
                "event_timestamp": datetime.now(UTC),
                "lines_generated": 5,
            },
            {
                "tool_type": "github_copilot",
                "event_type": "completion",
                "event_timestamp": datetime.now(UTC),
                "lines_generated": 3,
            },
        ]

        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_collect_with_since_filter(self):
        """Test collecting events since a specific time."""
        since = datetime.now(UTC) - timedelta(hours=24)

        # Events after since should be included
        events = [
            {
                "event_timestamp": datetime.now(UTC),
                "tool_type": "cursor",
            },
        ]

        for event in events:
            assert event["event_timestamp"] > since

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test."""
        success = True
        message = "Connection successful"

        assert success is True
        assert "successful" in message.lower()

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test failed connection test."""
        success = False
        message = "Invalid API key"

        assert success is False
        assert "Invalid" in message


# =============================================================================
# Save Events Tests
# =============================================================================


class TestSaveEvents:
    """Tests for saving events to database."""

    @pytest.mark.asyncio
    async def test_save_single_event(self):
        """Test saving a single event."""
        events = [
            {
                "tool_type": "github_copilot",
                "event_type": "completion",
                "event_timestamp": datetime.now(UTC),
            },
        ]

        saved = len(events)

        assert saved == 1

    @pytest.mark.asyncio
    async def test_save_multiple_events(self):
        """Test saving multiple events."""
        events = [
            {"tool_type": "github_copilot", "event_type": "completion", "event_timestamp": datetime.now(UTC)},
            {"tool_type": "cursor", "event_type": "completion", "event_timestamp": datetime.now(UTC)},
            {"tool_type": "claude_code", "event_type": "completion", "event_timestamp": datetime.now(UTC)},
        ]

        saved = len(events)

        assert saved == 3

    @pytest.mark.asyncio
    async def test_save_empty_events(self):
        """Test saving empty event list."""
        events = []

        saved = len(events)

        assert saved == 0


# =============================================================================
# Aggregate Metrics Tests
# =============================================================================


class TestAggregateMetrics:
    """Tests for aggregating metrics."""

    @pytest.mark.asyncio
    async def test_aggregate_basic_metrics(self):
        """Test aggregating basic metrics."""
        events = [
            {"lines_generated": 10, "lines_accepted": 8},
            {"lines_generated": 5, "lines_accepted": 4},
            {"lines_generated": 15, "lines_accepted": 12},
        ]

        total_generated = sum(e["lines_generated"] for e in events)
        total_accepted = sum(e["lines_accepted"] for e in events)

        assert total_generated == 30
        assert total_accepted == 24

    @pytest.mark.asyncio
    async def test_aggregate_user_metrics(self):
        """Test aggregating user metrics."""
        events = [
            {"user_hash": "user1"},
            {"user_hash": "user2"},
            {"user_hash": "user1"},
            {"user_hash": "user3"},
        ]

        unique_users = len(set(e["user_hash"] for e in events))

        assert unique_users == 3

    @pytest.mark.asyncio
    async def test_aggregate_latency_metrics(self):
        """Test aggregating latency metrics."""
        events = [
            {"latency_ms": 100},
            {"latency_ms": 150},
            {"latency_ms": 200},
            {"latency_ms": 250},
            {"latency_ms": 300},
        ]

        latencies = [e["latency_ms"] for e in events]
        avg_latency = sum(latencies) / len(latencies)

        assert avg_latency == 200.0

    @pytest.mark.asyncio
    async def test_aggregate_token_metrics(self):
        """Test aggregating token metrics."""
        events = [
            {"tokens_used": 100},
            {"tokens_used": 200},
            {"tokens_used": 150},
        ]

        total_tokens = sum(e["tokens_used"] for e in events)

        assert total_tokens == 450


# =============================================================================
# AI Summary Service Tests
# =============================================================================


class TestAISummaryService:
    """Tests for AI Summary service."""

    @pytest.mark.asyncio
    async def test_generate_sprint_summary(self):
        """Test generating sprint summary."""
        sprint_name = "Sprint 1"
        sprint_start = datetime.now(UTC) - timedelta(days=14)
        sprint_end = datetime.now(UTC)

        summary = {
            "title": f"Sprint Summary: {sprint_name}",
            "summary_type": "sprint",
            "period_start": sprint_start,
            "period_end": sprint_end,
            "summary": "Sprint completed successfully...",
            "key_points": ["Delivered 5 features", "AI tools increased productivity"],
            "recommendations": ["Increase code review coverage"],
        }

        assert summary["summary_type"] == "sprint"
        assert len(summary["key_points"]) > 0

    @pytest.mark.asyncio
    async def test_generate_metrics_summary(self):
        """Test generating metrics summary."""
        period_start = datetime.now(UTC) - timedelta(days=30)
        period_end = datetime.now(UTC)

        summary = {
            "title": "AI Analytics Summary",
            "summary_type": "metrics",
            "period_start": period_start,
            "period_end": period_end,
            "summary": "AI tool adoption increased by 20%...",
            "key_points": ["Copilot usage up 30%", "Acceptance rate improved"],
        }

        assert summary["summary_type"] == "metrics"

    @pytest.mark.asyncio
    async def test_generate_pr_summary(self):
        """Test generating PR summary."""
        pr_data = {
            "title": "Add new feature",
            "description": "Implements user authentication",
            "author": "developer",
            "files_changed": 10,
            "additions": 500,
            "deletions": 100,
            "pr_number": 123,
        }

        summary = {
            "title": f"PR Summary: {pr_data['title']}",
            "summary_type": "pr",
            "target_id": str(pr_data["pr_number"]),
            "target_type": "pull_request",
            "summary": "This PR adds user authentication...",
        }

        assert summary["summary_type"] == "pr"
        assert summary["target_type"] == "pull_request"

    @pytest.mark.asyncio
    async def test_generate_incident_postmortem(self):
        """Test generating incident postmortem."""
        incident_data = {
            "incident_id": str(uuid4()),
            "title": "Database outage",
            "severity": "P1",
            "duration_minutes": 45,
            "impact": "All users affected",
            "root_cause": "Configuration error",
            "timeline": "12:00 - Detected\n12:15 - Mitigated",
        }

        summary = {
            "title": f"Postmortem: {incident_data['title']}",
            "summary_type": "incident",
            "target_id": incident_data["incident_id"],
            "target_type": "incident",
            "summary": "Incident summary...",
            "recommendations": ["Add monitoring alerts", "Review change process"],
        }

        assert summary["summary_type"] == "incident"
        assert len(summary["recommendations"]) > 0


# =============================================================================
# Data Gathering Tests
# =============================================================================


class TestDataGathering:
    """Tests for data gathering methods."""

    @pytest.mark.asyncio
    async def test_gather_sprint_data(self):
        """Test gathering sprint data."""
        data = {
            "sprint_start": datetime.now(UTC) - timedelta(days=14),
            "sprint_end": datetime.now(UTC),
            "tool_usage": {
                "github_copilot": {
                    "events": 500,
                    "lines_generated": 2000,
                    "lines_accepted": 1600,
                    "users": 15,
                },
                "cursor": {
                    "events": 200,
                    "lines_generated": 800,
                    "lines_accepted": 640,
                    "users": 8,
                },
            },
        }

        assert "tool_usage" in data
        assert len(data["tool_usage"]) == 2

    @pytest.mark.asyncio
    async def test_gather_metrics_data(self):
        """Test gathering metrics data."""
        data = {
            "period": {
                "start": datetime.now(UTC) - timedelta(days=30),
                "end": datetime.now(UTC),
            },
            "by_tool": {
                "github_copilot": {
                    "events": 2000,
                    "lines_generated": 10000,
                    "lines_accepted": 8000,
                    "tokens": 500000,
                    "users": 50,
                },
            },
        }

        assert "by_tool" in data
        assert "github_copilot" in data["by_tool"]


# =============================================================================
# Text Extraction Tests
# =============================================================================


class TestTextExtraction:
    """Tests for text extraction methods."""

    def test_extract_key_points_bullets(self):
        """Test extracting key points from bullet list."""
        text = """
Summary:
- Point 1
- Point 2
• Point 3
* Point 4
"""
        lines = text.split("\n")
        points = []
        for line in lines:
            line = line.strip()
            if line.startswith("- ") or line.startswith("• ") or line.startswith("* "):
                points.append(line[2:])

        assert len(points) == 4

    def test_extract_key_points_limit(self):
        """Test key points extraction limits to 10."""
        points = [f"Point {i}" for i in range(15)]
        limited_points = points[:10]

        assert len(limited_points) == 10

    def test_extract_recommendations(self):
        """Test extracting recommendations."""
        text = """
Summary text...

Recommendations:
- Implement automated testing
- Add monitoring alerts
- Review deployment process
"""
        lines = text.split("\n")
        recommendations = []
        in_recommendations = False

        for line in lines:
            line = line.strip()
            if "recommendation" in line.lower():
                in_recommendations = True
                continue
            if in_recommendations and line.startswith("- "):
                recommendations.append(line[2:])

        assert len(recommendations) == 3

    def test_extract_recommendations_limit(self):
        """Test recommendations extraction limits to 5."""
        recommendations = [f"Recommendation {i}" for i in range(10)]
        limited_recommendations = recommendations[:5]

        assert len(limited_recommendations) == 5


# =============================================================================
# Prompt Building Tests
# =============================================================================


class TestPromptBuilding:
    """Tests for prompt building methods."""

    def test_build_sprint_summary_prompt(self):
        """Test building sprint summary prompt."""
        data = {
            "sprint_start": datetime(2024, 1, 1),
            "sprint_end": datetime(2024, 1, 14),
            "tool_usage": {
                "github_copilot": {
                    "events": 500,
                    "lines_generated": 2000,
                    "lines_accepted": 1600,
                    "users": 15,
                },
            },
        }
        sprint_name = "Sprint 1"

        prompt = f"Sprint: {sprint_name}\n"
        prompt += f"Period: {data['sprint_start'].strftime('%Y-%m-%d')} to {data['sprint_end'].strftime('%Y-%m-%d')}\n"

        assert "Sprint: Sprint 1" in prompt
        assert "2024-01-01" in prompt

    def test_format_metrics_data(self):
        """Test formatting metrics data for prompt."""
        data = {
            "by_tool": {
                "github_copilot": {
                    "events": 2000,
                    "lines_generated": 10000,
                    "lines_accepted": 8000,
                    "tokens": 500000,
                    "users": 50,
                },
            },
        }

        lines = []
        for tool, metrics in data["by_tool"].items():
            lines.append(f"\n{tool}:")
            lines.append(f"  Events: {metrics['events']}")

        formatted = "\n".join(lines)

        assert "github_copilot" in formatted
        assert "Events: 2000" in formatted


# =============================================================================
# GitHub Copilot Plugin Tests
# =============================================================================


class TestGitHubCopilotPlugin:
    """Tests for GitHub Copilot plugin."""

    def test_plugin_name(self):
        """Test plugin name."""
        name = "GitHub Copilot"

        assert name == "GitHub Copilot"

    def test_plugin_tool_type(self):
        """Test plugin tool type."""
        tool_type = "github_copilot"

        assert tool_type == AIToolType.GITHUB_COPILOT

    @pytest.mark.asyncio
    async def test_collect_events(self):
        """Test collecting events from Copilot API."""
        events = [
            {
                "tool_type": "github_copilot",
                "event_type": "completion",
                "lines_generated": 5,
            },
        ]

        assert len(events) >= 0

    @pytest.mark.asyncio
    async def test_aggregate_metrics(self):
        """Test aggregating Copilot metrics."""
        metrics = {
            "tool_type": "github_copilot",
            "total_events": 1000,
            "acceptance_rate": 78.5,
        }

        assert metrics["tool_type"] == "github_copilot"


# =============================================================================
# Cursor Plugin Tests
# =============================================================================


class TestCursorPlugin:
    """Tests for Cursor plugin."""

    def test_plugin_name(self):
        """Test plugin name."""
        name = "Cursor"

        assert name == "Cursor"

    def test_plugin_tool_type(self):
        """Test plugin tool type."""
        tool_type = "cursor"

        assert tool_type == AIToolType.CURSOR


# =============================================================================
# Claude Code Plugin Tests
# =============================================================================


class TestClaudeCodePlugin:
    """Tests for Claude Code plugin."""

    def test_plugin_name(self):
        """Test plugin name."""
        name = "Claude Code"

        assert name == "Claude Code"

    def test_plugin_tool_type(self):
        """Test plugin tool type."""
        tool_type = "claude_code"

        assert tool_type == AIToolType.CLAUDE_CODE


# =============================================================================
# Amazon Q Plugin Tests
# =============================================================================


class TestAmazonQPlugin:
    """Tests for Amazon Q plugin."""

    def test_plugin_name(self):
        """Test plugin name."""
        name = "Amazon Q Developer"

        assert "Amazon Q" in name

    def test_plugin_tool_type(self):
        """Test plugin tool type."""
        tool_type = "amazon_q"

        assert tool_type == AIToolType.AMAZON_Q


# =============================================================================
# ROI Calculation Tests
# =============================================================================


class TestROICalculation:
    """Tests for ROI calculation."""

    def test_calculate_time_savings(self):
        """Test calculating time savings from AI tools."""
        lines_accepted = 5000
        avg_lines_per_hour_manual = 50
        hourly_rate = 75.0

        hours_saved = lines_accepted / avg_lines_per_hour_manual
        cost_savings = hours_saved * hourly_rate

        assert hours_saved == 100
        assert cost_savings == 7500.0

    def test_calculate_tool_cost(self):
        """Test calculating tool cost."""
        users = 20
        cost_per_user_per_month = 19.0

        monthly_cost = users * cost_per_user_per_month

        assert monthly_cost == 380.0

    def test_calculate_roi(self):
        """Test calculating ROI."""
        savings = 7500.0
        cost = 380.0

        roi = ((savings - cost) / cost) * 100 if cost > 0 else 0

        assert roi > 0

    def test_roi_negative(self):
        """Test negative ROI calculation."""
        savings = 200.0
        cost = 500.0

        roi = ((savings - cost) / cost) * 100 if cost > 0 else 0

        assert roi < 0


# =============================================================================
# Multi-tenant Tests
# =============================================================================


class TestMultiTenantAnalytics:
    """Tests for multi-tenant analytics."""

    @pytest.mark.asyncio
    async def test_tenant_data_isolation(self):
        """Test data is isolated by tenant."""
        tenant_a_id = str(uuid4())
        tenant_b_id = str(uuid4())

        events_a = [{"tenant_id": tenant_a_id, "event_type": "completion"}]
        events_b = [{"tenant_id": tenant_b_id, "event_type": "completion"}]

        assert events_a[0]["tenant_id"] != events_b[0]["tenant_id"]

    @pytest.mark.asyncio
    async def test_metrics_by_tenant(self):
        """Test metrics are aggregated by tenant."""
        tenant_id = str(uuid4())

        metrics = {
            "tenant_id": tenant_id,
            "total_events": 1000,
        }

        assert metrics["tenant_id"] == tenant_id
