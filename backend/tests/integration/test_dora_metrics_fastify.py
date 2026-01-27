"""
Integration tests for DORA metrics with fastify/fastify-cli project.

Tests the complete DORA metrics flow:
1. DevLake connection setup for GitHub
2. Project creation and scope configuration
3. DORA metrics retrieval and validation
4. Metrics calculation and performance level classification

NOTE: These tests require DevLake to be running and configured.
Set GITHUB_TOKEN environment variable with a valid token for live tests.
"""

import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.devlake.service import DevLakeService, DORAMetrics
from app.services.metrics.dora import DORAMetricsService, DORAMetrics as DORAMetricsModel


# =============================================================================
# Test Configuration
# =============================================================================

# Project configuration for fastify/fastify-cli
GITHUB_REPO_OWNER = "fastify"
GITHUB_REPO_NAME = "fastify-cli"
GITHUB_FULL_REPO = f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}"
PROJECT_NAME = "sumaninster"

# Get token from environment (never hardcode tokens in tests)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", os.getenv("GH_TOKEN", ""))


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def devlake_service():
    """Create a DevLake service instance."""
    return DevLakeService()


@pytest.fixture
def dora_metrics_service():
    """Create a DORA metrics service instance."""
    return DORAMetricsService()


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    from sqlalchemy.ext.asyncio import AsyncSession
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_fastify_dora_metrics():
    """Sample DORA metrics response for fastify-cli project.

    Based on typical open-source project characteristics:
    - Regular releases (deployment frequency)
    - PR-based workflow (lead time)
    - Active issue management (MTTR proxy)
    - Stable releases (low change failure rate)
    """
    return DORAMetrics(
        deployment_frequency=0.25,  # ~Weekly releases
        deployment_frequency_rating="high",
        lead_time_for_changes_hours=48.0,  # ~2 days PR cycle
        lead_time_rating="high",
        mean_time_to_recovery_hours=24.0,  # ~1 day issue resolution
        mttr_rating="high",
        change_failure_rate=5.0,  # Low failure rate
        cfr_rating="elite",
        overall_rating="high",
        time_range="past_6_months",
        project_name=PROJECT_NAME,
    )


@pytest.fixture
def mock_github_connection():
    """Mock GitHub connection response."""
    return {
        "id": 1,
        "name": f"{PROJECT_NAME}-github",
        "plugin": "github",
        "endpoint": "https://api.github.com/",
        "authMethod": "AccessToken",
    }


@pytest.fixture
def mock_project_response():
    """Mock DevLake project response."""
    return {
        "name": PROJECT_NAME,
        "description": f"DORA metrics for {GITHUB_FULL_REPO}",
    }


# =============================================================================
# DevLake Service Tests
# =============================================================================


class TestDevLakeServiceConnection:
    """Test DevLake service connectivity."""

    @pytest.mark.asyncio
    async def test_health_check_mock(self, devlake_service):
        """Test DevLake health check with mock."""
        with patch.object(devlake_service, '_get_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "pong"

            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)

            with patch('httpx.AsyncClient', return_value=mock_async_client):
                result = await devlake_service.health_check()
                assert result is True

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, devlake_service):
        """Test DevLake health check when service is unavailable."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await devlake_service.health_check()
            assert result is False


class TestDevLakeGitHubConnection:
    """Test DevLake GitHub connection management."""

    @pytest.mark.asyncio
    async def test_create_github_connection_success(
        self, devlake_service, mock_github_connection
    ):
        """Test successful GitHub connection creation."""
        with patch.object(devlake_service, '_get_client') as mock_get_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_github_connection
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_client

            result = await devlake_service.create_connection(
                plugin="github",
                name=f"{PROJECT_NAME}-github",
                endpoint="https://api.github.com/",
                token="test_token",
                auth_method="AccessToken",
            )

            assert result["id"] == 1
            assert result["plugin"] == "github"
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_github_connection_duplicate(self, devlake_service):
        """Test GitHub connection creation when connection already exists."""
        with patch.object(devlake_service, '_get_client') as mock_get_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": False,
                "message": "Connection name already exists",
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_client

            with pytest.raises(ValueError, match="already exists"):
                await devlake_service.create_connection(
                    plugin="github",
                    name=f"{PROJECT_NAME}-github",
                    endpoint="https://api.github.com/",
                    token="test_token",
                )

    @pytest.mark.asyncio
    async def test_list_github_connections(self, devlake_service, mock_github_connection):
        """Test listing GitHub connections."""
        with patch.object(devlake_service, '_get_client') as mock_get_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [mock_github_connection]
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_client

            connections = await devlake_service.list_connections(plugin="github")

            assert len(connections) == 1
            assert connections[0]["plugin"] == "github"


class TestDevLakeProjectManagement:
    """Test DevLake project management for DORA metrics."""

    @pytest.mark.asyncio
    async def test_create_project_success(
        self, devlake_service, mock_project_response
    ):
        """Test successful project creation."""
        with patch.object(devlake_service, '_get_client') as mock_get_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_project_response
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_client

            result = await devlake_service.create_project(
                name=PROJECT_NAME,
                description=f"DORA metrics for {GITHUB_FULL_REPO}",
            )

            assert result["name"] == PROJECT_NAME

    @pytest.mark.asyncio
    async def test_get_project_success(self, devlake_service, mock_project_response):
        """Test getting a project by name."""
        with patch.object(devlake_service, '_get_client') as mock_get_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_project_response
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_client

            result = await devlake_service.get_project(PROJECT_NAME)

            assert result is not None
            assert result["name"] == PROJECT_NAME

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, devlake_service):
        """Test getting a non-existent project."""
        with patch.object(devlake_service, '_get_client') as mock_get_client:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_client

            result = await devlake_service.get_project("non-existent-project")

            assert result is None


# =============================================================================
# DORA Metrics Tests
# =============================================================================


class TestDORAMetricsRetrieval:
    """Test DORA metrics retrieval from DevLake."""

    @pytest.mark.asyncio
    async def test_get_dora_metrics_success(
        self, devlake_service, sample_fastify_dora_metrics
    ):
        """Test successful DORA metrics retrieval."""
        mock_api_response = {
            "deployment_frequency": 0.25,
            "lead_time_for_changes_hours": 48.0,
            "mean_time_to_recovery_hours": 24.0,
            "change_failure_rate": 5.0,
            "overall_rating": "high",
        }

        with patch.object(devlake_service, '_get_client') as mock_get_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_api_response
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_client

            metrics = await devlake_service.get_dora_metrics(
                project_name=PROJECT_NAME,
                time_range="past_6_months",
            )

            assert metrics.project_name == PROJECT_NAME
            assert metrics.deployment_frequency == 0.25
            assert metrics.lead_time_for_changes_hours == 48.0
            assert metrics.mean_time_to_recovery_hours == 24.0
            assert metrics.change_failure_rate == 5.0

    @pytest.mark.asyncio
    async def test_get_dora_metrics_api_error(self, devlake_service):
        """Test DORA metrics retrieval when API returns error."""
        with patch.object(devlake_service, '_get_client') as mock_get_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error", request=MagicMock(), response=mock_response
            )

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_client

            # Should return empty metrics, not raise
            metrics = await devlake_service.get_dora_metrics(
                project_name=PROJECT_NAME,
                time_range="past_6_months",
            )

            assert metrics.project_name == PROJECT_NAME
            assert metrics.deployment_frequency == 0.0


class TestDORAMetricsRatings:
    """Test DORA metrics rating calculations."""

    @pytest.fixture
    def service(self):
        return DevLakeService()

    @pytest.mark.parametrize("freq,expected_rating", [
        (2.0, "elite"),    # Multiple deploys per day
        (1.0, "elite"),    # Daily deploys
        (0.5, "high"),     # Multiple per week
        (0.14, "high"),    # Weekly
        (0.1, "medium"),   # 2-3 times per month
        (0.033, "medium"), # Monthly
        (0.01, "low"),     # Less than monthly
        (0.0, "low"),
    ])
    def test_deployment_frequency_rating(self, service, freq, expected_rating):
        """Test deployment frequency rating classification."""
        rating = service._rate_deployment_frequency(freq)
        assert rating == expected_rating

    @pytest.mark.parametrize("hours,expected_rating", [
        (0.5, "elite"),    # 30 minutes
        (1.0, "elite"),    # 1 hour
        (12.0, "high"),    # 12 hours
        (24.0, "high"),    # 1 day
        (72.0, "medium"),  # 3 days
        (168.0, "medium"), # 1 week
        (336.0, "low"),    # 2 weeks
    ])
    def test_lead_time_rating(self, service, hours, expected_rating):
        """Test lead time rating classification."""
        rating = service._rate_lead_time(hours)
        assert rating == expected_rating

    @pytest.mark.parametrize("hours,expected_rating", [
        (0.5, "elite"),    # 30 minutes
        (1.0, "elite"),    # 1 hour
        (12.0, "high"),    # 12 hours
        (24.0, "high"),    # 1 day
        (72.0, "medium"),  # 3 days
        (168.0, "medium"), # 1 week
        (336.0, "low"),    # 2 weeks
    ])
    def test_mttr_rating(self, service, hours, expected_rating):
        """Test MTTR rating classification."""
        rating = service._rate_mttr(hours)
        assert rating == expected_rating

    @pytest.mark.parametrize("rate,expected_rating", [
        (5.0, "elite"),    # 5%
        (15.0, "elite"),   # 15%
        (20.0, "high"),    # 20%
        (30.0, "high"),    # 30%
        (35.0, "medium"),  # 35%
        (45.0, "medium"),  # 45%
        (50.0, "low"),     # 50%
    ])
    def test_cfr_rating(self, service, rate, expected_rating):
        """Test change failure rate rating classification."""
        rating = service._rate_cfr(rate)
        assert rating == expected_rating


# =============================================================================
# DORA Metrics Service Tests
# =============================================================================


class TestDORAMetricsServiceCalculation:
    """Test DORA metrics service calculation."""

    @pytest.mark.asyncio
    async def test_calculate_metrics_for_fastify_project(
        self, dora_metrics_service, mock_db_session
    ):
        """Test DORA metrics calculation for fastify-cli project."""
        mock_devlake_metrics = MagicMock()
        mock_devlake_metrics.deployment_frequency = 0.25
        mock_devlake_metrics.lead_time_for_changes = 48.0
        mock_devlake_metrics.mean_time_to_recovery = 24.0
        mock_devlake_metrics.change_failure_rate = 5.0

        with patch(
            "app.services.metrics.dora.devlake_service.get_dora_metrics",
            new_callable=AsyncMock,
            return_value=mock_devlake_metrics,
        ):
            metrics = await dora_metrics_service.calculate_metrics(
                session=mock_db_session,
                tenant_id="test-tenant",
                project_name=PROJECT_NAME,
            )

            assert metrics.deployment_frequency == 0.25
            assert metrics.lead_time_for_changes == 48.0
            assert metrics.mean_time_to_recovery == 24.0
            assert metrics.change_failure_rate == 5.0
            # Check performance levels
            assert metrics.deployment_frequency_level in ["high", "medium"]
            assert metrics.lead_time_level in ["high", "medium"]
            assert metrics.mttr_level in ["high", "elite"]
            assert metrics.change_failure_rate_level == "elite"

    @pytest.mark.asyncio
    async def test_calculate_metrics_with_date_range(
        self, dora_metrics_service, mock_db_session
    ):
        """Test DORA metrics calculation with specific date range."""
        mock_devlake_metrics = MagicMock()
        mock_devlake_metrics.deployment_frequency = 0.3
        mock_devlake_metrics.lead_time_for_changes = 36.0
        mock_devlake_metrics.mean_time_to_recovery = 12.0
        mock_devlake_metrics.change_failure_rate = 3.0

        period_start = datetime.now() - timedelta(days=90)
        period_end = datetime.now()

        with patch(
            "app.services.metrics.dora.devlake_service.get_dora_metrics",
            new_callable=AsyncMock,
            return_value=mock_devlake_metrics,
        ):
            metrics = await dora_metrics_service.calculate_metrics(
                session=mock_db_session,
                tenant_id="test-tenant",
                project_name=PROJECT_NAME,
                period_start=period_start,
                period_end=period_end,
            )

            assert metrics.period_start == period_start
            assert metrics.period_end == period_end


# =============================================================================
# End-to-End Integration Tests (with Live DevLake)
# =============================================================================


@pytest.mark.skipif(
    not GITHUB_TOKEN,
    reason="GITHUB_TOKEN environment variable not set"
)
@pytest.mark.integration
class TestDORAMetricsLiveIntegration:
    """Live integration tests requiring running DevLake instance.

    These tests are skipped unless:
    1. GITHUB_TOKEN environment variable is set
    2. DevLake is running and accessible

    Run with: pytest -m integration tests/integration/test_dora_metrics_fastify.py
    """

    @pytest.mark.asyncio
    async def test_live_devlake_health_check(self, devlake_service):
        """Test live DevLake health check."""
        is_healthy = await devlake_service.health_check()

        if not is_healthy:
            pytest.skip("DevLake is not running - skipping live integration tests")

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_live_create_github_connection(self, devlake_service):
        """Test creating a live GitHub connection for fastify-cli."""
        # Check DevLake health first
        if not await devlake_service.health_check():
            pytest.skip("DevLake is not running")

        try:
            connection = await devlake_service.create_connection(
                plugin="github",
                name=f"{PROJECT_NAME}-github-test",
                endpoint="https://api.github.com/",
                token=GITHUB_TOKEN,
                auth_method="AccessToken",
            )

            # Connection response format varies by DevLake version
            # Check for common fields that indicate success
            assert connection is not None
            # DevLake may return 'id', 'ID', or 'connectionId'
            has_id = any(
                key in connection
                for key in ["id", "ID", "connectionId", "connection_id"]
            )
            assert has_id or "name" in connection, f"Unexpected connection response: {connection}"

        except ValueError as e:
            if "already exists" in str(e):
                # Connection already exists, which is fine
                pass
            else:
                raise

    @pytest.mark.asyncio
    async def test_live_create_project(self, devlake_service):
        """Test creating a live project in DevLake."""
        if not await devlake_service.health_check():
            pytest.skip("DevLake is not running")

        try:
            project = await devlake_service.create_project(
                name=f"{PROJECT_NAME}-test",
                description=f"Test project for {GITHUB_FULL_REPO}",
            )

            assert project["name"] == f"{PROJECT_NAME}-test"

        except ValueError as e:
            if "already exists" in str(e):
                # Project already exists, which is fine
                pass
            else:
                raise

    @pytest.mark.asyncio
    async def test_live_get_dora_metrics(self, devlake_service):
        """Test retrieving live DORA metrics for a configured project."""
        if not await devlake_service.health_check():
            pytest.skip("DevLake is not running")

        # Try to get metrics - may return empty if project not fully configured
        metrics = await devlake_service.get_dora_metrics(
            project_name=PROJECT_NAME,
            time_range="past_6_months",
        )

        # Verify metrics object structure
        assert metrics.project_name == PROJECT_NAME
        assert metrics.time_range == "past_6_months"
        assert hasattr(metrics, 'deployment_frequency')
        assert hasattr(metrics, 'lead_time_for_changes_hours')
        assert hasattr(metrics, 'mean_time_to_recovery_hours')
        assert hasattr(metrics, 'change_failure_rate')

        # Log metrics for debugging
        print(f"\nDORA Metrics for {PROJECT_NAME}:")
        print(f"  Deployment Frequency: {metrics.deployment_frequency} ({metrics.deployment_frequency_rating})")
        print(f"  Lead Time: {metrics.lead_time_for_changes_hours}h ({metrics.lead_time_rating})")
        print(f"  MTTR: {metrics.mean_time_to_recovery_hours}h ({metrics.mttr_rating})")
        print(f"  Change Failure Rate: {metrics.change_failure_rate}% ({metrics.cfr_rating})")
        print(f"  Overall Rating: {metrics.overall_rating}")


# =============================================================================
# Complete DORA Workflow Test
# =============================================================================


class TestDORAMetricsCompleteWorkflow:
    """Test complete DORA metrics workflow."""

    @pytest.mark.asyncio
    async def test_complete_dora_workflow_mocked(
        self, devlake_service, dora_metrics_service, mock_db_session
    ):
        """Test complete DORA workflow: connection -> project -> metrics."""

        # Step 1: Mock creating GitHub connection
        mock_connection = {
            "id": 1,
            "name": f"{PROJECT_NAME}-github",
            "plugin": "github",
        }

        # Step 2: Mock creating project
        mock_project = {
            "name": PROJECT_NAME,
            "description": f"DORA metrics for {GITHUB_FULL_REPO}",
        }

        # Step 3: Mock DORA metrics from DevLake
        mock_devlake_metrics = MagicMock()
        mock_devlake_metrics.deployment_frequency = 0.3
        mock_devlake_metrics.lead_time_for_changes = 36.0
        mock_devlake_metrics.mean_time_to_recovery = 18.0
        mock_devlake_metrics.change_failure_rate = 8.0

        with patch.object(
            devlake_service, 'create_connection',
            new_callable=AsyncMock,
            return_value=mock_connection
        ):
            with patch.object(
                devlake_service, 'create_project',
                new_callable=AsyncMock,
                return_value=mock_project
            ):
                with patch(
                    "app.services.metrics.dora.devlake_service.get_dora_metrics",
                    new_callable=AsyncMock,
                    return_value=mock_devlake_metrics,
                ):
                    # Execute workflow
                    # 1. Create connection
                    connection = await devlake_service.create_connection(
                        plugin="github",
                        name=f"{PROJECT_NAME}-github",
                        endpoint="https://api.github.com/",
                        token="mock_token",
                    )
                    assert connection["plugin"] == "github"

                    # 2. Create project
                    project = await devlake_service.create_project(
                        name=PROJECT_NAME,
                        description=f"DORA metrics for {GITHUB_FULL_REPO}",
                    )
                    assert project["name"] == PROJECT_NAME

                    # 3. Calculate DORA metrics
                    metrics = await dora_metrics_service.calculate_metrics(
                        session=mock_db_session,
                        tenant_id="test-tenant",
                        project_name=PROJECT_NAME,
                    )

                    # Verify metrics
                    assert metrics.deployment_frequency == 0.3
                    assert metrics.lead_time_for_changes == 36.0
                    assert metrics.mean_time_to_recovery == 18.0
                    assert metrics.change_failure_rate == 8.0

                    # Verify performance levels are calculated
                    assert metrics.deployment_frequency_level is not None
                    assert metrics.lead_time_level is not None
                    assert metrics.mttr_level is not None
                    assert metrics.change_failure_rate_level is not None
                    assert metrics.overall_level is not None

                    # Log summary
                    print(f"\nDORA Workflow Test Results for {PROJECT_NAME}:")
                    print(f"  Project: {GITHUB_FULL_REPO}")
                    print(f"  Deployment Frequency: {metrics.deployment_frequency_level}")
                    print(f"  Lead Time: {metrics.lead_time_level}")
                    print(f"  MTTR: {metrics.mttr_level}")
                    print(f"  Change Failure Rate: {metrics.change_failure_rate_level}")
                    print(f"  Overall Level: {metrics.overall_level}")
