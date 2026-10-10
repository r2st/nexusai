"""AI SDLC Adoption Analyst Agent."""

from dataclasses import dataclass
from datetime import datetime, UTC, timedelta
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class AdoptionStage(str, Enum):
    """Stages of AI tool adoption."""

    AWARENESS = "awareness"      # Know about AI tools
    TRIAL = "trial"              # Trying out AI tools
    ADOPTION = "adoption"        # Regular use
    PROFICIENCY = "proficiency"  # Advanced use
    ADVOCACY = "advocacy"        # Promoting to others


class AITool(str, Enum):
    """Supported AI development tools."""

    GITHUB_COPILOT = "github_copilot"
    CURSOR = "cursor"
    CLAUDE_CODE = "claude_code"
    AMAZON_Q = "amazon_q"
    TABNINE = "tabnine"
    CODEWHISPERER = "codewhisperer"
    REPLIT_AI = "replit_ai"
    SOURCEGRAPH_CODY = "sourcegraph_cody"


@dataclass
class UserAdoptionMetrics:
    """Adoption metrics for a single user."""

    user_id: str
    adoption_stage: AdoptionStage
    primary_tool: AITool | None
    tools_used: list[AITool]
    suggestions_accepted: int
    suggestions_shown: int
    acceptance_rate: float
    active_days: int
    last_active: datetime | None
    productivity_score: float | None = None


@dataclass
class TeamAdoptionMetrics:
    """Aggregated adoption metrics for a team."""

    team_id: str
    team_name: str
    total_members: int
    adopters: int
    adoption_rate: float
    avg_acceptance_rate: float
    top_tool: AITool | None
    tool_distribution: dict[str, int]
    stage_distribution: dict[str, int]
    weekly_trend: list[float]


@dataclass
class AdoptionAnalysisResult:
    """Complete adoption analysis result."""

    organization_id: str
    period_start: datetime
    period_end: datetime
    overall_adoption_rate: float
    total_users: int
    active_users: int
    teams: list[TeamAdoptionMetrics]
    top_performers: list[UserAdoptionMetrics]
    low_adopters: list[UserAdoptionMetrics]
    roi_analysis: dict[str, Any]
    recommendations: list[str]
    insights: list[str]


class AISDLCAdoptionAgent:
    """Agent specialized in analyzing AI tool adoption in SDLC.

    This agent:
    - Tracks AI tool usage across development teams
    - Calculates adoption rates and trends
    - Identifies adoption blockers
    - Measures ROI of AI tools
    - Provides recommendations for improving adoption
    """

    # Industry benchmarks
    BENCHMARKS = {
        "elite_acceptance_rate": 35.0,
        "high_acceptance_rate": 25.0,
        "target_adoption_rate": 80.0,
        "avg_time_saved_per_week": 5.0,  # hours
        "productivity_gain": 30.0,  # percentage
    }

    def __init__(self, db_session=None):
        self.db = db_session
        self.agent_id = "ai-sdlc-adoption-agent"
        self.agent_name = "AI SDLC Adoption Analyst"
        self.capabilities = [
            "adoption_tracking",
            "usage_analysis",
            "roi_calculation",
            "trend_analysis",
            "recommendation_generation",
        ]

    async def analyze(
        self,
        organization_id: str,
        period_days: int = 30,
    ) -> AdoptionAnalysisResult:
        """Perform complete adoption analysis."""
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=period_days)

        logger.info(
            "Starting adoption analysis",
            organization_id=organization_id,
            period_days=period_days,
        )

        # Get team metrics
        teams = await self._analyze_teams(organization_id, period_start, period_end)

        # Calculate overall metrics
        total_users = sum(t.total_members for t in teams)
        active_users = sum(t.adopters for t in teams)
        overall_adoption = (active_users / total_users * 100) if total_users > 0 else 0

        # Get top performers and low adopters
        top_performers = await self._get_top_performers(organization_id, period_start, period_end)
        low_adopters = await self._get_low_adopters(organization_id, period_start, period_end)

        # Calculate ROI
        roi = await self._calculate_roi(organization_id, active_users, teams)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            overall_adoption, teams, top_performers, low_adopters
        )

        # Generate insights
        insights = self._generate_insights(overall_adoption, teams, roi)

        result = AdoptionAnalysisResult(
            organization_id=organization_id,
            period_start=period_start,
            period_end=period_end,
            overall_adoption_rate=overall_adoption,
            total_users=total_users,
            active_users=active_users,
            teams=teams,
            top_performers=top_performers,
            low_adopters=low_adopters,
            roi_analysis=roi,
            recommendations=recommendations,
            insights=insights,
        )

        logger.info(
            "Adoption analysis completed",
            organization_id=organization_id,
            adoption_rate=overall_adoption,
        )

        return result

    async def _analyze_teams(
        self,
        organization_id: str,
        start: datetime,
        end: datetime,
    ) -> list[TeamAdoptionMetrics]:
        """Analyze adoption metrics by team."""
        # In production, this would query the database
        # Mock data for demonstration

        teams = [
            TeamAdoptionMetrics(
                team_id="team-1",
                team_name="Platform Engineering",
                total_members=12,
                adopters=10,
                adoption_rate=83.3,
                avg_acceptance_rate=32.5,
                top_tool=AITool.GITHUB_COPILOT,
                tool_distribution={
                    "github_copilot": 8,
                    "cursor": 3,
                    "claude_code": 2,
                },
                stage_distribution={
                    "proficiency": 5,
                    "adoption": 4,
                    "trial": 1,
                    "awareness": 2,
                },
                weekly_trend=[75.0, 78.0, 80.0, 83.3],
            ),
            TeamAdoptionMetrics(
                team_id="team-2",
                team_name="Product Development",
                total_members=18,
                adopters=12,
                adoption_rate=66.7,
                avg_acceptance_rate=28.0,
                top_tool=AITool.CURSOR,
                tool_distribution={
                    "cursor": 10,
                    "github_copilot": 4,
                    "claude_code": 1,
                },
                stage_distribution={
                    "proficiency": 3,
                    "adoption": 7,
                    "trial": 2,
                    "awareness": 6,
                },
                weekly_trend=[55.0, 60.0, 63.0, 66.7],
            ),
            TeamAdoptionMetrics(
                team_id="team-3",
                team_name="Data Engineering",
                total_members=8,
                adopters=7,
                adoption_rate=87.5,
                avg_acceptance_rate=35.0,
                top_tool=AITool.GITHUB_COPILOT,
                tool_distribution={
                    "github_copilot": 6,
                    "amazon_q": 2,
                },
                stage_distribution={
                    "advocacy": 2,
                    "proficiency": 4,
                    "adoption": 1,
                    "awareness": 1,
                },
                weekly_trend=[80.0, 82.0, 85.0, 87.5],
            ),
        ]

        return teams

    async def _get_top_performers(
        self,
        organization_id: str,
        start: datetime,
        end: datetime,
        limit: int = 5,
    ) -> list[UserAdoptionMetrics]:
        """Get top AI tool users."""
        # Mock data
        return [
            UserAdoptionMetrics(
                user_id="user-1",
                adoption_stage=AdoptionStage.ADVOCACY,
                primary_tool=AITool.GITHUB_COPILOT,
                tools_used=[AITool.GITHUB_COPILOT, AITool.CURSOR],
                suggestions_accepted=1250,
                suggestions_shown=3200,
                acceptance_rate=39.0,
                active_days=28,
                last_active=datetime.now(UTC),
                productivity_score=95.0,
            ),
            UserAdoptionMetrics(
                user_id="user-2",
                adoption_stage=AdoptionStage.PROFICIENCY,
                primary_tool=AITool.CURSOR,
                tools_used=[AITool.CURSOR, AITool.CLAUDE_CODE],
                suggestions_accepted=980,
                suggestions_shown=2800,
                acceptance_rate=35.0,
                active_days=25,
                last_active=datetime.now(UTC),
                productivity_score=88.0,
            ),
        ]

    async def _get_low_adopters(
        self,
        organization_id: str,
        start: datetime,
        end: datetime,
        limit: int = 5,
    ) -> list[UserAdoptionMetrics]:
        """Get users with low adoption."""
        return [
            UserAdoptionMetrics(
                user_id="user-50",
                adoption_stage=AdoptionStage.AWARENESS,
                primary_tool=None,
                tools_used=[],
                suggestions_accepted=0,
                suggestions_shown=0,
                acceptance_rate=0.0,
                active_days=0,
                last_active=None,
            ),
            UserAdoptionMetrics(
                user_id="user-51",
                adoption_stage=AdoptionStage.TRIAL,
                primary_tool=AITool.GITHUB_COPILOT,
                tools_used=[AITool.GITHUB_COPILOT],
                suggestions_accepted=15,
                suggestions_shown=200,
                acceptance_rate=7.5,
                active_days=3,
                last_active=datetime.now(UTC) - timedelta(days=20),
            ),
        ]

    async def _calculate_roi(
        self,
        organization_id: str,
        active_users: int,
        teams: list[TeamAdoptionMetrics],
    ) -> dict[str, Any]:
        """Calculate ROI of AI tool investment."""
        # Industry benchmarks
        avg_developer_hourly_rate = 75.0  # USD
        time_saved_per_week = self.BENCHMARKS["avg_time_saved_per_week"]
        weeks_per_year = 48

        # Cost estimates
        copilot_cost_per_user_month = 19.0
        cursor_cost_per_user_month = 20.0
        avg_tool_cost = (copilot_cost_per_user_month + cursor_cost_per_user_month) / 2

        # Calculations
        annual_cost = active_users * avg_tool_cost * 12
        hours_saved_per_year = active_users * time_saved_per_week * weeks_per_year
        value_generated = hours_saved_per_year * avg_developer_hourly_rate

        roi_percentage = ((value_generated - annual_cost) / annual_cost * 100) if annual_cost > 0 else 0

        return {
            "annual_cost": annual_cost,
            "annual_savings": value_generated,
            "net_benefit": value_generated - annual_cost,
            "roi_percentage": roi_percentage,
            "hours_saved_per_dev": time_saved_per_week,
            "hours_saved_annually": hours_saved_per_year,
            "cost_per_user": avg_tool_cost,
            "productivity_gain": self.BENCHMARKS["productivity_gain"],
            "payback_period_months": (annual_cost / (value_generated / 12)) if value_generated > 0 else float("inf"),
        }

    def _generate_recommendations(
        self,
        adoption_rate: float,
        teams: list[TeamAdoptionMetrics],
        top_performers: list[UserAdoptionMetrics],
        low_adopters: list[UserAdoptionMetrics],
    ) -> list[str]:
        """Generate adoption improvement recommendations."""
        recommendations = []

        # Overall adoption recommendations
        if adoption_rate < 50:
            recommendations.append(
                "Launch an organization-wide AI tools awareness campaign with demos and success stories"
            )
        elif adoption_rate < 80:
            recommendations.append(
                "Focus on moving users from trial to adoption stage through targeted training"
            )

        # Team-specific recommendations
        low_adoption_teams = [t for t in teams if t.adoption_rate < 60]
        for team in low_adoption_teams:
            recommendations.append(
                f"Schedule hands-on training session for {team.team_name} team (current adoption: {team.adoption_rate:.0f}%)"
            )

        # Use champions
        if top_performers:
            recommendations.append(
                "Create an AI Champions program with top performers to mentor and guide adoption"
            )

        # Address low adopters
        if low_adopters:
            non_users = len([u for u in low_adopters if u.adoption_stage == AdoptionStage.AWARENESS])
            if non_users > 0:
                recommendations.append(
                    f"Conduct 1-on-1 onboarding sessions with {non_users} developers who haven't tried AI tools"
                )

        # Tool-specific
        recommendations.append(
            "Standardize on 2-3 approved AI tools to simplify training and support"
        )

        return recommendations

    def _generate_insights(
        self,
        adoption_rate: float,
        teams: list[TeamAdoptionMetrics],
        roi: dict[str, Any],
    ) -> list[str]:
        """Generate insights from adoption data."""
        insights = []

        # Adoption comparison
        if adoption_rate >= 80:
            insights.append(
                f"🌟 Your {adoption_rate:.0f}% adoption rate places you in the top quartile of organizations"
            )
        elif adoption_rate >= 50:
            insights.append(
                f"📈 At {adoption_rate:.0f}% adoption, you're above average but have room for growth"
            )

        # ROI insights
        if roi["roi_percentage"] > 100:
            insights.append(
                f"💰 Your AI tool investment is generating {roi['roi_percentage']:.0f}% ROI "
                f"(${roi['net_benefit']:,.0f} annual net benefit)"
            )

        # Team comparison
        if teams:
            best_team = max(teams, key=lambda t: t.adoption_rate)
            insights.append(
                f"✅ {best_team.team_name} leads adoption at {best_team.adoption_rate:.0f}% - "
                "consider them as a model for other teams"
            )

            # Trend analysis
            improving_teams = [t for t in teams if len(t.weekly_trend) >= 2 and t.weekly_trend[-1] > t.weekly_trend[0]]
            if improving_teams:
                insights.append(
                    f"📊 {len(improving_teams)} teams showing positive adoption trends over the past month"
                )

        return insights

    def format_for_handoff(self, result: AdoptionAnalysisResult) -> dict[str, Any]:
        """Format analysis result for handoff to next agent."""
        return {
            "agent": self.agent_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "organization_id": result.organization_id,
            "period": {
                "start": result.period_start.isoformat(),
                "end": result.period_end.isoformat(),
            },
            "adoption_rate": result.overall_adoption_rate,
            "active_users": result.active_users,
            "total_users": result.total_users,
            "acceptance_rate": sum(t.avg_acceptance_rate for t in result.teams) / len(result.teams) if result.teams else 0,
            "top_tool": max(
                (tool for team in result.teams if team.top_tool for tool in [team.top_tool]),
                key=lambda t: sum(1 for team in result.teams if team.top_tool == t),
                default=None,
            ),
            "by_provider": [
                {"name": tool.value, "users": sum(team.tool_distribution.get(tool.value, 0) for team in result.teams)}
                for tool in AITool
                if any(team.tool_distribution.get(tool.value, 0) for team in result.teams)
            ],
            "roi": result.roi_analysis,
            "recommendations": result.recommendations,
            "insights": result.insights,
            "handoff_context": "AI SDLC adoption analysis complete. Ready for dashboard or summary.",
        }
