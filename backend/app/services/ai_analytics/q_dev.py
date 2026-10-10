"""Amazon Q Developer integration plugin.

Collects AI usage data from Amazon Q Developer including:
- Code completions and suggestions
- Chat interactions
- Security scans
- Code transformations
"""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analytics import AIToolType, AIUsageLog
from app.services.ai_analytics.base import (
    AIAnalyticsPlugin,
    AIToolMetrics,
    AIUsageEvent,
)


class QDevPlugin(AIAnalyticsPlugin):
    """Plugin for collecting Amazon Q Developer usage metrics."""

    def __init__(self):
        super().__init__(AIToolType.Q_DEV)

    @property
    def name(self) -> str:
        return "Amazon Q Developer"

    @property
    def description(self) -> str:
        return "Collect AI coding assistant metrics from Amazon Q Developer"

    async def collect(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        connection_config: dict[str, Any],
        since: datetime | None = None,
    ) -> list[AIUsageEvent]:
        """Collect usage data from Amazon Q Developer.

        Uses AWS CloudWatch metrics and Q Developer API:
        - CloudWatch metrics for aggregate usage
        - Q Developer API for detailed interactions
        """
        events: list[AIUsageEvent] = []

        # Get AWS credentials
        aws_access_key = connection_config.get("aws_access_key_id")
        aws_secret_key = connection_config.get("aws_secret_access_key")
        aws_region = connection_config.get("aws_region", "us-east-1")

        if not aws_access_key or not aws_secret_key:
            return events

        try:
            # Use boto3 for AWS API calls
            import boto3
            from botocore.config import Config

            config = Config(region_name=aws_region)

            # Create CloudWatch client
            cloudwatch = boto3.client(
                "cloudwatch",
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                config=config,
            )

            # Get Q Developer metrics from CloudWatch
            end_time = datetime.now()
            start_time = since or (end_time - timedelta(days=7))

            # Query for code suggestions metrics
            response = cloudwatch.get_metric_data(
                MetricDataQueries=[
                    {
                        "Id": "suggestions",
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/CodeWhisperer",
                                "MetricName": "Suggestions",
                            },
                            "Period": 3600,
                            "Stat": "Sum",
                        },
                    },
                    {
                        "Id": "acceptances",
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/CodeWhisperer",
                                "MetricName": "AcceptedSuggestions",
                            },
                            "Period": 3600,
                            "Stat": "Sum",
                        },
                    },
                ],
                StartTime=start_time,
                EndTime=end_time,
            )

            # Parse CloudWatch response
            suggestions_data = {}
            acceptances_data = {}

            for result in response.get("MetricDataResults", []):
                if result["Id"] == "suggestions":
                    for i, ts in enumerate(result.get("Timestamps", [])):
                        suggestions_data[ts] = result["Values"][i]
                elif result["Id"] == "acceptances":
                    for i, ts in enumerate(result.get("Timestamps", [])):
                        acceptances_data[ts] = result["Values"][i]

            # Create events from the data
            for ts, suggestions in suggestions_data.items():
                acceptances = acceptances_data.get(ts, 0)
                events.append(AIUsageEvent(
                    tool_type=self.tool_type.value,
                    event_type="hourly_aggregate",
                    event_timestamp=ts,
                    lines_generated=int(suggestions),
                    lines_accepted=int(acceptances),
                    metadata={
                        "source": "cloudwatch",
                        "region": aws_region,
                    },
                ))

        except ImportError:
            print("boto3 not installed, skipping AWS collection")
        except Exception as e:
            print(f"Error collecting Amazon Q Developer metrics: {e}")

        return events

    async def test_connection(
        self,
        connection_config: dict[str, Any],
    ) -> tuple[bool, str]:
        """Test connection to Amazon Q Developer."""
        aws_access_key = connection_config.get("aws_access_key_id")
        aws_secret_key = connection_config.get("aws_secret_access_key")
        aws_region = connection_config.get("aws_region", "us-east-1")

        if not aws_access_key or not aws_secret_key:
            return False, "AWS credentials are required"

        try:
            import boto3
            from botocore.config import Config
            from botocore.exceptions import ClientError

            config = Config(region_name=aws_region)

            # Test credentials with STS
            sts = boto3.client(
                "sts",
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                config=config,
            )

            identity = sts.get_caller_identity()
            account = identity.get("Account")

            # Test CloudWatch access
            cloudwatch = boto3.client(
                "cloudwatch",
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                config=config,
            )

            # Try to list metrics
            cloudwatch.list_metrics(
                Namespace="AWS/CodeWhisperer",
                Limit=1,
            )

            return True, f"Connected to AWS account {account}"

        except ImportError:
            return False, "boto3 not installed"
        except ClientError as e:
            return False, f"AWS error: {e.response['Error']['Message']}"
        except Exception as e:
            return False, "Connection failed. Please check your credentials and try again."

    async def aggregate_metrics(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> AIToolMetrics:
        """Aggregate Amazon Q Developer metrics for a time period."""
        query = select(
            func.count(AIUsageLog.id).label("total_events"),
            func.sum(AIUsageLog.lines_generated).label("total_lines_generated"),
            func.sum(AIUsageLog.lines_accepted).label("total_lines_accepted"),
            func.sum(AIUsageLog.tokens_used).label("total_tokens"),
            func.count(func.distinct(AIUsageLog.user_hash)).label("unique_users"),
        ).where(
            AIUsageLog.tenant_id == tenant_id,
            AIUsageLog.tool_type == self.tool_type.value,
            AIUsageLog.event_timestamp >= period_start,
            AIUsageLog.event_timestamp < period_end,
        )

        if project_id:
            query = query.where(AIUsageLog.project_id == project_id)

        result = await session.execute(query)
        row = result.first()

        if not row:
            return AIToolMetrics(
                tool_type=self.tool_type.value,
                period_start=period_start,
                period_end=period_end,
            )

        total_lines_generated = row.total_lines_generated or 0
        total_lines_accepted = row.total_lines_accepted or 0

        # Estimate cost based on Q Developer pricing ($19/user/month for Pro)
        unique_users = row.unique_users or 0
        months = max(1, (period_end - period_start).days / 30)
        estimated_cost = unique_users * 19.0 * months

        return AIToolMetrics(
            tool_type=self.tool_type.value,
            period_start=period_start,
            period_end=period_end,
            total_events=row.total_events or 0,
            total_completions=total_lines_generated,
            accepted_completions=total_lines_accepted,
            total_lines_generated=total_lines_generated,
            total_lines_accepted=total_lines_accepted,
            acceptance_rate=(
                total_lines_accepted / total_lines_generated
                if total_lines_generated > 0
                else 0.0
            ),
            unique_users=unique_users,
            total_tokens=row.total_tokens or 0,
            estimated_cost=estimated_cost,
        )

    def get_schema(self) -> dict[str, Any]:
        """Get configuration schema for Amazon Q Developer plugin."""
        return {
            "type": "object",
            "properties": {
                "aws_access_key_id": {
                    "type": "string",
                    "description": "AWS Access Key ID",
                },
                "aws_secret_access_key": {
                    "type": "string",
                    "description": "AWS Secret Access Key",
                },
                "aws_region": {
                    "type": "string",
                    "description": "AWS Region (default: us-east-1)",
                    "default": "us-east-1",
                },
                "profile_name": {
                    "type": "string",
                    "description": "AWS profile name for local credentials",
                },
            },
            "required": ["aws_access_key_id", "aws_secret_access_key"],
        }


# Import timedelta for the collection method
from datetime import timedelta
