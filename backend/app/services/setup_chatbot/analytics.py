"""Analytics - Conversation analytics and feedback for setup chatbot."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any
import statistics
import logging

logger = logging.getLogger(__name__)


# ===================
# Feedback System
# ===================

class FeedbackType(str, Enum):
    """Types of feedback."""
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    CONFUSING = "confusing"
    TOO_SLOW = "too_slow"
    ERROR_RECOVERY = "error_recovery"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    OTHER = "other"


class FeedbackSentiment(str, Enum):
    """Feedback sentiment."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@dataclass
class ConversationFeedback:
    """User feedback for a conversation."""
    feedback_id: str
    session_id: str
    message_id: str | None
    timestamp: datetime
    feedback_type: FeedbackType
    sentiment: FeedbackSentiment
    rating: int | None = None  # 1-5
    comment: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "feedback_id": self.feedback_id,
            "session_id": self.session_id,
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
            "feedback_type": self.feedback_type.value,
            "sentiment": self.sentiment.value,
            "rating": self.rating,
            "comment": self.comment,
            "context": self.context,
        }


class FeedbackCollector:
    """Collects and manages user feedback."""

    def __init__(self, max_feedback: int = 10000):
        self._feedback: list[ConversationFeedback] = []
        self._max_feedback = max_feedback
        self._feedback_by_session: dict[str, list[ConversationFeedback]] = defaultdict(list)

    def submit_feedback(
        self,
        session_id: str,
        feedback_type: FeedbackType,
        sentiment: FeedbackSentiment,
        message_id: str | None = None,
        rating: int | None = None,
        comment: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> ConversationFeedback:
        """Submit feedback for a conversation."""
        from uuid import uuid4

        feedback = ConversationFeedback(
            feedback_id=str(uuid4()),
            session_id=session_id,
            message_id=message_id,
            timestamp=datetime.now(UTC),
            feedback_type=feedback_type,
            sentiment=sentiment,
            rating=rating,
            comment=comment,
            context=context or {},
        )

        self._feedback.append(feedback)
        self._feedback_by_session[session_id].append(feedback)

        # Trim if needed
        if len(self._feedback) > self._max_feedback:
            removed = self._feedback.pop(0)
            if removed.session_id in self._feedback_by_session:
                session_feedback = self._feedback_by_session[removed.session_id]
                if removed in session_feedback:
                    session_feedback.remove(removed)

        logger.info(
            f"Feedback received: {feedback_type.value} ({sentiment.value}) "
            f"for session {session_id}"
        )

        return feedback

    def get_session_feedback(self, session_id: str) -> list[ConversationFeedback]:
        """Get all feedback for a session."""
        return self._feedback_by_session.get(session_id, [])

    def get_recent_feedback(
        self,
        hours: int = 24,
        feedback_type: FeedbackType | None = None,
        sentiment: FeedbackSentiment | None = None,
    ) -> list[ConversationFeedback]:
        """Get recent feedback."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        feedback = [f for f in self._feedback if f.timestamp >= cutoff]

        if feedback_type:
            feedback = [f for f in feedback if f.feedback_type == feedback_type]
        if sentiment:
            feedback = [f for f in feedback if f.sentiment == sentiment]

        return feedback

    def get_feedback_summary(self, hours: int = 24) -> dict[str, Any]:
        """Get a summary of recent feedback."""
        recent = self.get_recent_feedback(hours=hours)

        if not recent:
            return {
                "total_count": 0,
                "period_hours": hours,
            }

        # Count by type
        by_type = defaultdict(int)
        for f in recent:
            by_type[f.feedback_type.value] += 1

        # Count by sentiment
        by_sentiment = defaultdict(int)
        for f in recent:
            by_sentiment[f.sentiment.value] += 1

        # Calculate average rating
        ratings = [f.rating for f in recent if f.rating is not None]
        avg_rating = statistics.mean(ratings) if ratings else None

        return {
            "total_count": len(recent),
            "period_hours": hours,
            "by_type": dict(by_type),
            "by_sentiment": dict(by_sentiment),
            "average_rating": avg_rating,
            "positive_percentage": (by_sentiment.get("positive", 0) / len(recent)) * 100 if recent else 0,
        }


# Singleton feedback collector
feedback_collector = FeedbackCollector()


# ===================
# Conversation Metrics
# ===================

@dataclass
class ConversationMetrics:
    """Metrics for a single conversation."""
    session_id: str
    tenant_id: str
    user_id: str
    started_at: datetime
    ended_at: datetime | None = None
    message_count: int = 0
    user_message_count: int = 0
    assistant_message_count: int = 0
    flow_type: str | None = None
    flow_completed: bool = False
    flow_cancelled: bool = False
    errors_count: int = 0
    retry_count: int = 0
    total_duration_seconds: float = 0
    avg_response_time_ms: float = 0
    quick_replies_used: int = 0
    help_requests: int = 0
    successful_actions: list[str] = field(default_factory=list)
    failed_actions: list[str] = field(default_factory=list)

    @property
    def completion_rate(self) -> float:
        """Get the flow completion rate."""
        if not self.flow_type:
            return 0
        return 100.0 if self.flow_completed else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "message_count": self.message_count,
            "user_message_count": self.user_message_count,
            "assistant_message_count": self.assistant_message_count,
            "flow_type": self.flow_type,
            "flow_completed": self.flow_completed,
            "flow_cancelled": self.flow_cancelled,
            "errors_count": self.errors_count,
            "retry_count": self.retry_count,
            "total_duration_seconds": self.total_duration_seconds,
            "avg_response_time_ms": self.avg_response_time_ms,
            "quick_replies_used": self.quick_replies_used,
            "help_requests": self.help_requests,
            "successful_actions": self.successful_actions,
            "failed_actions": self.failed_actions,
        }


class ConversationAnalytics:
    """Collects and analyzes conversation metrics."""

    def __init__(self, max_metrics: int = 10000):
        self._metrics: dict[str, ConversationMetrics] = {}
        self._completed_metrics: list[ConversationMetrics] = []
        self._max_metrics = max_metrics
        self._response_times: list[float] = []  # Recent response times

    def start_session(
        self,
        session_id: str,
        tenant_id: str,
        user_id: str,
        flow_type: str | None = None,
    ) -> ConversationMetrics:
        """Start tracking a new session."""
        metrics = ConversationMetrics(
            session_id=session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            started_at=datetime.now(UTC),
            flow_type=flow_type,
        )
        self._metrics[session_id] = metrics
        return metrics

    def get_metrics(self, session_id: str) -> ConversationMetrics | None:
        """Get metrics for a session."""
        return self._metrics.get(session_id)

    def record_message(
        self,
        session_id: str,
        role: str,
        response_time_ms: float | None = None,
        is_quick_reply: bool = False,
    ) -> None:
        """Record a message in a session."""
        metrics = self._metrics.get(session_id)
        if not metrics:
            return

        metrics.message_count += 1
        if role == "user":
            metrics.user_message_count += 1
            if is_quick_reply:
                metrics.quick_replies_used += 1
        elif role == "assistant":
            metrics.assistant_message_count += 1
            if response_time_ms:
                self._response_times.append(response_time_ms)
                # Keep only recent times
                if len(self._response_times) > 1000:
                    self._response_times.pop(0)

    def record_error(self, session_id: str, is_retry: bool = False) -> None:
        """Record an error in a session."""
        metrics = self._metrics.get(session_id)
        if not metrics:
            return

        metrics.errors_count += 1
        if is_retry:
            metrics.retry_count += 1

    def record_help_request(self, session_id: str) -> None:
        """Record a help request."""
        metrics = self._metrics.get(session_id)
        if metrics:
            metrics.help_requests += 1

    def record_action(
        self,
        session_id: str,
        action: str,
        success: bool,
    ) -> None:
        """Record an action result."""
        metrics = self._metrics.get(session_id)
        if not metrics:
            return

        if success:
            metrics.successful_actions.append(action)
        else:
            metrics.failed_actions.append(action)

    def complete_session(
        self,
        session_id: str,
        completed: bool = True,
        cancelled: bool = False,
    ) -> ConversationMetrics | None:
        """Complete a session and finalize metrics."""
        metrics = self._metrics.get(session_id)
        if not metrics:
            return None

        metrics.ended_at = datetime.now(UTC)
        metrics.flow_completed = completed
        metrics.flow_cancelled = cancelled
        metrics.total_duration_seconds = (
            metrics.ended_at - metrics.started_at
        ).total_seconds()

        # Calculate average response time
        if self._response_times:
            metrics.avg_response_time_ms = statistics.mean(self._response_times[-100:])

        # Move to completed
        self._completed_metrics.append(metrics)
        if len(self._completed_metrics) > self._max_metrics:
            self._completed_metrics.pop(0)

        del self._metrics[session_id]
        return metrics

    def get_aggregate_stats(
        self,
        hours: int = 24,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Get aggregate statistics."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)

        # Combine active and completed
        all_metrics = list(self._metrics.values()) + self._completed_metrics
        recent = [m for m in all_metrics if m.started_at >= cutoff]

        if tenant_id:
            recent = [m for m in recent if m.tenant_id == tenant_id]

        if not recent:
            return {
                "period_hours": hours,
                "total_sessions": 0,
            }

        completed = [m for m in recent if m.ended_at is not None]
        flows = [m for m in recent if m.flow_type is not None]

        # Flow completion rate
        flow_completed = [m for m in flows if m.flow_completed]
        completion_rate = (len(flow_completed) / len(flows)) * 100 if flows else 0

        # Flow type breakdown
        flow_types = defaultdict(int)
        for m in flows:
            if m.flow_type:
                flow_types[m.flow_type] += 1

        # Error rate
        total_messages = sum(m.message_count for m in recent)
        total_errors = sum(m.errors_count for m in recent)
        error_rate = (total_errors / total_messages) * 100 if total_messages else 0

        # Average session duration
        durations = [m.total_duration_seconds for m in completed if m.total_duration_seconds > 0]
        avg_duration = statistics.mean(durations) if durations else 0

        # Quick reply usage
        quick_reply_usage = sum(m.quick_replies_used for m in recent)
        quick_reply_rate = (quick_reply_usage / total_messages) * 100 if total_messages else 0

        return {
            "period_hours": hours,
            "total_sessions": len(recent),
            "active_sessions": len(self._metrics),
            "completed_sessions": len(completed),
            "total_messages": total_messages,
            "flow_completion_rate": round(completion_rate, 1),
            "flow_types": dict(flow_types),
            "error_rate": round(error_rate, 2),
            "avg_session_duration_seconds": round(avg_duration, 1),
            "quick_reply_usage_rate": round(quick_reply_rate, 1),
            "help_requests": sum(m.help_requests for m in recent),
            "successful_actions": sum(len(m.successful_actions) for m in recent),
            "failed_actions": sum(len(m.failed_actions) for m in recent),
        }

    def get_flow_funnel(
        self,
        flow_type: str,
        hours: int = 24,
    ) -> dict[str, Any]:
        """Get funnel analysis for a specific flow."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)

        all_metrics = list(self._metrics.values()) + self._completed_metrics
        flow_metrics = [
            m for m in all_metrics
            if m.flow_type == flow_type and m.started_at >= cutoff
        ]

        if not flow_metrics:
            return {
                "flow_type": flow_type,
                "started": 0,
                "completed": 0,
                "cancelled": 0,
                "abandoned": 0,
            }

        completed = len([m for m in flow_metrics if m.flow_completed])
        cancelled = len([m for m in flow_metrics if m.flow_cancelled])
        abandoned = len([m for m in flow_metrics if not m.flow_completed and not m.flow_cancelled and m.ended_at])
        in_progress = len([m for m in flow_metrics if not m.ended_at])

        return {
            "flow_type": flow_type,
            "started": len(flow_metrics),
            "completed": completed,
            "cancelled": cancelled,
            "abandoned": abandoned,
            "in_progress": in_progress,
            "completion_rate": (completed / len(flow_metrics)) * 100 if flow_metrics else 0,
            "drop_off_rate": ((cancelled + abandoned) / len(flow_metrics)) * 100 if flow_metrics else 0,
        }


# Singleton analytics
conversation_analytics = ConversationAnalytics()


# ===================
# Performance Metrics
# ===================

@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot."""
    timestamp: datetime
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    requests_per_minute: float
    error_rate: float
    cache_hit_rate: float = 0


class PerformanceMonitor:
    """Monitors chatbot performance."""

    def __init__(self, window_minutes: int = 5):
        self._window_minutes = window_minutes
        self._response_times: list[tuple[datetime, float]] = []
        self._requests: list[datetime] = []
        self._errors: list[datetime] = []
        self._cache_hits: int = 0
        self._cache_misses: int = 0

    def record_request(
        self,
        response_time_ms: float,
        is_error: bool = False,
        cache_hit: bool = False,
    ) -> None:
        """Record a request."""
        now = datetime.now(UTC)

        self._response_times.append((now, response_time_ms))
        self._requests.append(now)

        if is_error:
            self._errors.append(now)

        if cache_hit:
            self._cache_hits += 1
        else:
            self._cache_misses += 1

        # Cleanup old data
        self._cleanup()

    def _cleanup(self) -> None:
        """Remove old data outside the window."""
        cutoff = datetime.now(UTC) - timedelta(minutes=self._window_minutes * 2)

        self._response_times = [
            (t, rt) for t, rt in self._response_times if t >= cutoff
        ]
        self._requests = [t for t in self._requests if t >= cutoff]
        self._errors = [t for t in self._errors if t >= cutoff]

    def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        now = datetime.now(UTC)
        window_start = now - timedelta(minutes=self._window_minutes)

        # Filter to window
        window_times = [rt for t, rt in self._response_times if t >= window_start]
        window_requests = [t for t in self._requests if t >= window_start]
        window_errors = [t for t in self._errors if t >= window_start]

        if not window_times:
            return PerformanceMetrics(
                timestamp=now,
                avg_response_time_ms=0,
                p50_response_time_ms=0,
                p95_response_time_ms=0,
                p99_response_time_ms=0,
                requests_per_minute=0,
                error_rate=0,
            )

        sorted_times = sorted(window_times)

        # Calculate percentiles
        def percentile(data: list[float], p: float) -> float:
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = f + 1
            if c >= len(data):
                return data[-1]
            return data[f] * (c - k) + data[c] * (k - f)

        # Calculate cache hit rate
        total_cache = self._cache_hits + self._cache_misses
        cache_hit_rate = (self._cache_hits / total_cache) * 100 if total_cache else 0

        return PerformanceMetrics(
            timestamp=now,
            avg_response_time_ms=statistics.mean(window_times),
            p50_response_time_ms=percentile(sorted_times, 50),
            p95_response_time_ms=percentile(sorted_times, 95),
            p99_response_time_ms=percentile(sorted_times, 99),
            requests_per_minute=len(window_requests) / self._window_minutes,
            error_rate=(len(window_errors) / len(window_requests)) * 100 if window_requests else 0,
            cache_hit_rate=cache_hit_rate,
        )

    def is_healthy(self) -> tuple[bool, list[str]]:
        """Check if performance is healthy."""
        metrics = self.get_metrics()
        issues = []

        # Check response time
        if metrics.p95_response_time_ms > 5000:
            issues.append(f"High P95 response time: {metrics.p95_response_time_ms:.0f}ms")

        # Check error rate
        if metrics.error_rate > 5:
            issues.append(f"High error rate: {metrics.error_rate:.1f}%")

        # Check if getting requests
        if metrics.requests_per_minute < 0.1 and len(self._requests) > 10:
            issues.append("Low request rate")

        return len(issues) == 0, issues


# Singleton performance monitor
performance_monitor = PerformanceMonitor()


# ===================
# Usage Analytics
# ===================

class UsageAnalytics:
    """Tracks feature usage and user behavior."""

    def __init__(self):
        self._feature_usage: dict[str, int] = defaultdict(int)
        self._plugin_usage: dict[str, int] = defaultdict(int)
        self._flow_starts: dict[str, int] = defaultdict(int)
        self._flow_completions: dict[str, int] = defaultdict(int)
        self._command_usage: dict[str, int] = defaultdict(int)
        self._quick_reply_usage: dict[str, int] = defaultdict(int)
        self._error_types: dict[str, int] = defaultdict(int)
        self._user_sessions: dict[str, int] = defaultdict(int)  # user_id -> session count

    def track_feature(self, feature: str) -> None:
        """Track feature usage."""
        self._feature_usage[feature] += 1

    def track_plugin(self, plugin: str) -> None:
        """Track plugin usage."""
        self._plugin_usage[plugin] += 1

    def track_flow_start(self, flow_type: str) -> None:
        """Track flow start."""
        self._flow_starts[flow_type] += 1

    def track_flow_completion(self, flow_type: str) -> None:
        """Track flow completion."""
        self._flow_completions[flow_type] += 1

    def track_command(self, command: str) -> None:
        """Track command usage."""
        self._command_usage[command] += 1

    def track_quick_reply(self, value: str) -> None:
        """Track quick reply usage."""
        self._quick_reply_usage[value] += 1

    def track_error(self, error_type: str) -> None:
        """Track error occurrence."""
        self._error_types[error_type] += 1

    def track_user_session(self, user_id: str) -> None:
        """Track user session."""
        self._user_sessions[user_id] += 1

    def get_usage_report(self) -> dict[str, Any]:
        """Get comprehensive usage report."""
        return {
            "features": dict(self._feature_usage),
            "plugins": dict(self._plugin_usage),
            "flows": {
                "starts": dict(self._flow_starts),
                "completions": dict(self._flow_completions),
            },
            "commands": dict(self._command_usage),
            "quick_replies": dict(self._quick_reply_usage),
            "errors": dict(self._error_types),
            "unique_users": len(self._user_sessions),
            "total_sessions": sum(self._user_sessions.values()),
        }

    def get_top_plugins(self, limit: int = 10) -> list[tuple[str, int]]:
        """Get most used plugins."""
        return sorted(
            self._plugin_usage.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:limit]

    def get_top_commands(self, limit: int = 10) -> list[tuple[str, int]]:
        """Get most used commands."""
        return sorted(
            self._command_usage.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:limit]

    def get_flow_completion_rates(self) -> dict[str, float]:
        """Get completion rates by flow type."""
        rates = {}
        for flow_type, starts in self._flow_starts.items():
            completions = self._flow_completions.get(flow_type, 0)
            rates[flow_type] = (completions / starts) * 100 if starts else 0
        return rates


# Singleton usage analytics
usage_analytics = UsageAnalytics()


# ===================
# Dashboard Data
# ===================

def get_analytics_dashboard(
    hours: int = 24,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Get comprehensive analytics dashboard data."""
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "period_hours": hours,
        "conversation_stats": conversation_analytics.get_aggregate_stats(hours, tenant_id),
        "performance": performance_monitor.get_metrics().__dict__,
        "feedback_summary": feedback_collector.get_feedback_summary(hours),
        "usage": usage_analytics.get_usage_report(),
        "flow_funnels": {
            flow: conversation_analytics.get_flow_funnel(flow, hours)
            for flow in ["connection", "project", "pipeline", "onboarding"]
        },
        "top_plugins": usage_analytics.get_top_plugins(5),
        "top_commands": usage_analytics.get_top_commands(5),
    }
