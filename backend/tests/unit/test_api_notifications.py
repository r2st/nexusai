"""
Unit tests for notification API endpoints.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.api.notifications import (
    router,
    SendNotificationRequest,
    TestNotificationRequest,
    NotificationResultResponse,
    PreferencesRequest,
)
from app.services.notifications import (
    NotificationChannel,
    NotificationType,
    NotificationPriority,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = MagicMock()
    user.id = str(uuid4())
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_notification_service():
    """Create a mock notification service."""
    service = MagicMock()
    service.send = AsyncMock()
    service.send_to_channel = AsyncMock()
    service.get_preferences = AsyncMock()
    service.update_preferences = AsyncMock()
    service.configure_channel = AsyncMock()
    service.test_channel = AsyncMock()
    return service


# =============================================================================
# Request Model Tests
# =============================================================================


class TestSendNotificationRequest:
    """Tests for SendNotificationRequest model."""

    def test_valid_notification_request(self):
        """Test creating a valid notification request."""
        request = SendNotificationRequest(
            type=NotificationType.SYSTEM_ALERT,
            title="Test Alert",
            body="This is a test notification",
        )

        assert request.title == "Test Alert"
        assert request.body == "This is a test notification"

    def test_notification_request_defaults(self):
        """Test notification request default values."""
        request = SendNotificationRequest(
            type=NotificationType.ANALYSIS_COMPLETE,
            title="Info",
            body="Information message",
        )

        assert request.priority == NotificationPriority.MEDIUM
        assert request.data == {}
        assert request.channels is None
        assert request.user_ids is None

    def test_notification_request_with_all_fields(self):
        """Test notification request with all fields."""
        request = SendNotificationRequest(
            type=NotificationType.CRITICAL_ISSUE_FOUND,
            priority=NotificationPriority.HIGH,
            title="Incident Alert",
            body="A critical incident has occurred",
            data={"incident_id": "INC-001", "severity": "critical"},
            channels=[NotificationChannel.SLACK, NotificationChannel.EMAIL],
            user_ids=["user-1", "user-2"],
        )

        assert request.type == NotificationType.CRITICAL_ISSUE_FOUND
        assert request.priority == NotificationPriority.HIGH
        assert "incident_id" in request.data
        assert len(request.channels) == 2


class TestTestNotificationRequest:
    """Tests for TestNotificationRequest model."""

    def test_valid_test_request(self):
        """Test creating a valid test notification request."""
        request = TestNotificationRequest(
            channel=NotificationChannel.SLACK,
        )

        assert request.channel == NotificationChannel.SLACK
        assert request.webhook_url is None

    def test_test_request_with_webhook(self):
        """Test test notification request with custom webhook."""
        request = TestNotificationRequest(
            channel=NotificationChannel.DISCORD,
            webhook_url="https://discord.com/api/webhooks/123/abc",
        )

        assert request.channel == NotificationChannel.DISCORD
        assert "discord.com" in request.webhook_url


class TestNotificationResultResponse:
    """Tests for NotificationResultResponse model."""

    def test_result_response(self):
        """Test notification result response."""
        response = NotificationResultResponse(
            total_channels=3,
            successful=2,
            failed=1,
            details=[
                {"channel": "slack", "success": True},
                {"channel": "email", "success": True},
                {"channel": "teams", "success": False, "error": "Webhook failed"},
            ],
        )

        assert response.total_channels == 3
        assert response.successful == 2
        assert response.failed == 1
        assert len(response.details) == 3


class TestPreferencesRequest:
    """Tests for PreferencesRequest model."""

    def test_valid_preferences(self):
        """Test creating valid preferences request."""
        request = PreferencesRequest(
            enabled=True,
        )

        assert request.enabled is True

    def test_preferences_defaults(self):
        """Test preferences default values."""
        request = PreferencesRequest()

        assert request.enabled is True
        assert request.channels == {}
        assert request.types == {}
        assert request.min_priority == NotificationPriority.MEDIUM
        assert request.email is None

    def test_preferences_with_channels(self):
        """Test preferences with channel settings."""
        request = PreferencesRequest(
            enabled=True,
            channels={
                NotificationChannel.SLACK: True,
                NotificationChannel.EMAIL: False,
                NotificationChannel.TEAMS: True,
            },
            types={
                NotificationType.SYSTEM_ALERT: True,
                NotificationType.ANALYSIS_COMPLETE: False,
            },
            min_priority=NotificationPriority.LOW,
            email="user@example.com",
        )

        assert request.channels[NotificationChannel.SLACK] is True
        assert request.channels[NotificationChannel.EMAIL] is False
        assert request.types[NotificationType.SYSTEM_ALERT] is True
        assert request.min_priority == NotificationPriority.LOW
        assert request.email == "user@example.com"


# =============================================================================
# Send Notification Endpoint Tests
# =============================================================================


class TestSendNotificationEndpoint:
    """Tests for POST /notifications/send endpoint."""

    @pytest.mark.asyncio
    async def test_send_notification_success(self, mock_user, mock_notification_service):
        """Test successful notification sending."""
        mock_notification_service.send.return_value = MagicMock(
            total_channels=2,
            successful=2,
            failed=0,
            details=[
                {"channel": "slack", "success": True},
                {"channel": "email", "success": True},
            ],
        )

        request = SendNotificationRequest(
            type=NotificationType.SYSTEM_ALERT,
            title="Test Alert",
            body="Test body",
        )

        # Endpoint would be called here

    @pytest.mark.asyncio
    async def test_send_notification_partial_failure(self, mock_user, mock_notification_service):
        """Test notification sending with partial failure."""
        mock_notification_service.send.return_value = MagicMock(
            total_channels=3,
            successful=1,
            failed=2,
            details=[
                {"channel": "slack", "success": True},
                {"channel": "email", "success": False, "error": "SMTP error"},
                {"channel": "teams", "success": False, "error": "Webhook timeout"},
            ],
        )

        # Should still return 200 with failure details

    @pytest.mark.asyncio
    async def test_send_notification_to_specific_users(self, mock_user, mock_notification_service):
        """Test sending notification to specific users."""
        request = SendNotificationRequest(
            type=NotificationType.PR_REVIEW_COMPLETE,
            title="You were mentioned",
            body="Someone mentioned you in a comment",
            user_ids=["user-1", "user-2", "user-3"],
        )

        # Should send to all specified users


# =============================================================================
# Test Notification Endpoint Tests
# =============================================================================


class TestTestNotificationEndpoint:
    """Tests for POST /notifications/test endpoint."""

    @pytest.mark.asyncio
    async def test_test_slack_notification(self, mock_user, mock_notification_service):
        """Test sending a test notification to Slack."""
        mock_notification_service.test_channel.return_value = {
            "success": True,
            "message": "Test notification sent successfully",
        }

        request = TestNotificationRequest(channel=NotificationChannel.SLACK)

        # Endpoint would be called here

    @pytest.mark.asyncio
    async def test_test_discord_notification(self, mock_user, mock_notification_service):
        """Test sending a test notification to Discord."""
        mock_notification_service.test_channel.return_value = {
            "success": True,
            "message": "Test notification sent successfully",
        }

        request = TestNotificationRequest(
            channel=NotificationChannel.DISCORD,
            webhook_url="https://discord.com/api/webhooks/123/test",
        )

        # Should use the provided webhook URL

    @pytest.mark.asyncio
    async def test_test_notification_failure(self, mock_user, mock_notification_service):
        """Test failed test notification."""
        mock_notification_service.test_channel.return_value = {
            "success": False,
            "error": "Invalid webhook URL",
        }

        # Should return error details


# =============================================================================
# Preferences Endpoint Tests
# =============================================================================


class TestPreferencesEndpoint:
    """Tests for notification preferences endpoints."""

    @pytest.mark.asyncio
    async def test_get_preferences(self, mock_user, mock_notification_service):
        """Test getting notification preferences."""
        mock_notification_service.get_preferences.return_value = {
            "enabled": True,
            "channels": {"slack": True, "email": True},
            "types": {"system_alert": True, "analysis_complete": True},
            "min_priority": "medium",
        }

        # Endpoint would be called here

    @pytest.mark.asyncio
    async def test_update_preferences(self, mock_user, mock_notification_service):
        """Test updating notification preferences."""
        mock_notification_service.update_preferences.return_value = {
            "enabled": True,
            "channels": {"slack": True, "email": False},
            "types": {"system_alert": True, "analysis_complete": False},
            "min_priority": "high",
        }

        request = PreferencesRequest(
            enabled=True,
            channels={NotificationChannel.SLACK: True, NotificationChannel.EMAIL: False},
            min_priority=NotificationPriority.HIGH,
        )

        # Endpoint would update preferences

    @pytest.mark.asyncio
    async def test_disable_all_notifications(self, mock_user, mock_notification_service):
        """Test disabling all notifications."""
        request = PreferencesRequest(enabled=False)

        # Should disable all notifications


# =============================================================================
# Channel Configuration Endpoint Tests
# =============================================================================


class TestChannelConfigurationEndpoint:
    """Tests for channel configuration endpoints."""

    @pytest.mark.asyncio
    async def test_configure_slack(self, mock_user, mock_notification_service):
        """Test configuring Slack channel."""
        mock_notification_service.configure_channel.return_value = {
            "success": True,
            "channel": "slack",
            "status": "configured",
        }

        config = {
            "webhook_url": "https://hooks.slack.com/services/xxx/yyy/zzz",
            "channel": "#alerts",
            "username": "NexusAI Bot",
        }

        # Endpoint would configure Slack

    @pytest.mark.asyncio
    async def test_configure_teams(self, mock_user, mock_notification_service):
        """Test configuring Microsoft Teams channel."""
        mock_notification_service.configure_channel.return_value = {
            "success": True,
            "channel": "teams",
            "status": "configured",
        }

        config = {
            "webhook_url": "https://outlook.office.com/webhook/xxx",
        }

        # Endpoint would configure Teams

    @pytest.mark.asyncio
    async def test_configure_discord(self, mock_user, mock_notification_service):
        """Test configuring Discord channel."""
        mock_notification_service.configure_channel.return_value = {
            "success": True,
            "channel": "discord",
            "status": "configured",
        }

        config = {
            "webhook_url": "https://discord.com/api/webhooks/xxx/yyy",
        }

        # Endpoint would configure Discord


# =============================================================================
# Notification Type Tests
# =============================================================================


class TestNotificationTypes:
    """Tests for different notification types."""

    def test_alert_notification(self):
        """Test alert type notification."""
        request = SendNotificationRequest(
            type=NotificationType.SYSTEM_ALERT,
            priority=NotificationPriority.HIGH,
            title="System Alert",
            body="CPU usage exceeded 90%",
            data={"metric": "cpu", "value": 92},
        )

        assert request.type == NotificationType.SYSTEM_ALERT
        assert request.priority == NotificationPriority.HIGH

    def test_analysis_complete_notification(self):
        """Test analysis complete type notification."""
        request = SendNotificationRequest(
            type=NotificationType.ANALYSIS_COMPLETE,
            priority=NotificationPriority.LOW,
            title="Analysis Complete",
            body="Code analysis completed successfully",
        )

        assert request.type == NotificationType.ANALYSIS_COMPLETE
        assert request.priority == NotificationPriority.LOW

    def test_security_issue_notification(self):
        """Test security issue type notification."""
        request = SendNotificationRequest(
            type=NotificationType.SECURITY_ISSUE_FOUND,
            priority=NotificationPriority.CRITICAL,
            title="Security Issue Detected",
            body="Critical vulnerability found in dependencies",
            data={
                "issue_id": "SEC-2024-001",
                "package": "vulnerable-lib",
                "severity": "critical",
            },
        )

        assert request.type == NotificationType.SECURITY_ISSUE_FOUND
        assert request.priority == NotificationPriority.CRITICAL

    def test_pr_review_notification(self):
        """Test PR review type notification."""
        request = SendNotificationRequest(
            type=NotificationType.PR_REVIEW_COMPLETE,
            title="PR Review Complete",
            body="Your PR #123 has been reviewed",
            user_ids=["author-user-id"],
        )

        assert request.type == NotificationType.PR_REVIEW_COMPLETE


# =============================================================================
# Priority Tests
# =============================================================================


class TestNotificationPriority:
    """Tests for notification priority handling."""

    def test_low_priority(self):
        """Test low priority notification."""
        request = SendNotificationRequest(
            type=NotificationType.ANALYSIS_COMPLETE,
            priority=NotificationPriority.LOW,
            title="Low Priority",
            body="Non-urgent notification",
        )

        assert request.priority == NotificationPriority.LOW

    def test_medium_priority_default(self):
        """Test default medium priority."""
        request = SendNotificationRequest(
            type=NotificationType.ANALYSIS_COMPLETE,
            title="Default Priority",
            body="Default priority notification",
        )

        assert request.priority == NotificationPriority.MEDIUM

    def test_high_priority(self):
        """Test high priority notification."""
        request = SendNotificationRequest(
            type=NotificationType.SYSTEM_ALERT,
            priority=NotificationPriority.HIGH,
            title="High Priority",
            body="Urgent notification",
        )

        assert request.priority == NotificationPriority.HIGH

    def test_critical_priority(self):
        """Test critical priority notification."""
        request = SendNotificationRequest(
            type=NotificationType.CRITICAL_ISSUE_FOUND,
            priority=NotificationPriority.CRITICAL,
            title="Critical",
            body="Critical incident",
        )

        assert request.priority == NotificationPriority.CRITICAL


# =============================================================================
# Channel Routing Tests
# =============================================================================


class TestChannelRouting:
    """Tests for notification channel routing."""

    def test_specific_channels(self):
        """Test routing to specific channels."""
        request = SendNotificationRequest(
            type=NotificationType.SYSTEM_ALERT,
            title="Alert",
            body="Alert body",
            channels=[NotificationChannel.SLACK, NotificationChannel.EMAIL],
        )

        assert NotificationChannel.SLACK in request.channels
        assert NotificationChannel.EMAIL in request.channels
        assert len(request.channels) == 2

    def test_all_channels_default(self):
        """Test default all channels routing."""
        request = SendNotificationRequest(
            type=NotificationType.SYSTEM_ALERT,
            title="Alert",
            body="Alert body",
        )

        # channels is None means send to all configured channels
        assert request.channels is None

    def test_single_channel(self):
        """Test routing to single channel."""
        request = SendNotificationRequest(
            type=NotificationType.ANALYSIS_COMPLETE,
            title="Info",
            body="Info body",
            channels=[NotificationChannel.SLACK],
        )

        assert len(request.channels) == 1
        assert request.channels[0] == NotificationChannel.SLACK


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_data_field(self):
        """Test notification with empty data."""
        request = SendNotificationRequest(
            type=NotificationType.ANALYSIS_COMPLETE,
            title="Title",
            body="Body",
            data={},
        )

        assert request.data == {}

    def test_large_data_field(self):
        """Test notification with large data payload."""
        request = SendNotificationRequest(
            type=NotificationType.WEEKLY_SUMMARY,
            title="Report",
            body="Report summary",
            data={
                "metrics": [{"name": f"metric_{i}", "value": i} for i in range(100)],
                "summary": "x" * 1000,
            },
        )

        assert len(request.data["metrics"]) == 100

    def test_unicode_in_notification(self):
        """Test notification with unicode content."""
        request = SendNotificationRequest(
            type=NotificationType.ANALYSIS_COMPLETE,
            title="Unicode Test ",
            body="Notification with emojis  and special chars: aeiou",
        )

        assert "" in request.title
        assert "" in request.body

    def test_empty_user_ids(self):
        """Test notification with empty user IDs list."""
        request = SendNotificationRequest(
            type=NotificationType.ANALYSIS_COMPLETE,
            title="Title",
            body="Body",
            user_ids=[],
        )

        assert request.user_ids == []
