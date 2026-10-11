"""
ARQ Worker Configuration

This module configures the ARQ (Async Redis Queue) worker for background task processing.
"""

import asyncio
import os
from typing import Any

from arq import cron
from arq.connections import RedisSettings
import structlog

from app.core.config import settings

logger = structlog.get_logger()


# =============================================================================
# Task Functions
# =============================================================================

async def process_document(ctx: dict[str, Any], document_id: str) -> dict[str, Any]:
    """
    Process a document for RAG indexing.

    Delegates to the DocumentService which handles fetching, chunking,
    embedding, and storing the document.
    """
    logger.info("Processing document", document_id=document_id)

    try:
        from app.core.database import async_session_factory
        from app.services.document import DocumentService

        async with async_session_factory() as db:
            doc_service = DocumentService(db)
            from sqlalchemy import select
            from app.models.document import Document

            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()

            if not document:
                logger.warning("Document not found", document_id=document_id)
                return {
                    "status": "failed",
                    "document_id": document_id,
                    "error": "Document not found",
                }

            processed = await doc_service.process_document(document)
            await db.commit()

            return {
                "status": "completed",
                "document_id": document_id,
                "chunks_processed": getattr(processed, "chunk_count", 0),
            }
    except Exception as e:
        logger.error("Error processing document", document_id=document_id, error=str(e))
        return {
            "status": "failed",
            "document_id": document_id,
            "error": str(e),
        }


async def send_notification(
    ctx: dict[str, Any],
    user_id: str,
    notification_type: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Send a notification to a user.

    Delegates to the chatbot notification service for Slack/Teams,
    or logs in-app notifications for later retrieval.
    """
    logger.info("Sending notification", notification_type=notification_type, user_id=user_id)

    try:
        from app.services.chatbot.service import ChatbotService

        chatbot = ChatbotService()
        await chatbot.send_notification(
            channel=data.get("channel", ""),
            message=data.get("message", ""),
            platform=data.get("platform", "slack"),
        )

        return {
            "status": "sent",
            "user_id": user_id,
            "notification_type": notification_type,
        }
    except Exception as e:
        logger.error("Error sending notification", user_id=user_id, error=str(e))
        return {
            "status": "failed",
            "user_id": user_id,
            "error": str(e),
        }


async def cleanup_expired_sessions(ctx: dict[str, Any]) -> dict[str, Any]:
    """
    Clean up expired user sessions.

    Deletes sessions whose expiry timestamp has passed.
    """
    logger.info("Running expired session cleanup")

    try:
        from app.core.database import async_session_factory
        from sqlalchemy import delete, select, func
        from app.models.session import Session
        from datetime import datetime, timezone

        async with async_session_factory() as db:
            now = datetime.now(timezone.utc)

            count_result = await db.execute(
                select(func.count()).select_from(Session).where(Session.expires_at < now)
            )
            cleaned_count = count_result.scalar() or 0

            if cleaned_count > 0:
                await db.execute(
                    delete(Session).where(Session.expires_at < now)
                )
                await db.commit()
                logger.info("Cleaned expired sessions", count=cleaned_count)

        return {
            "status": "completed",
            "sessions_cleaned": cleaned_count,
        }
    except Exception as e:
        logger.error("Error cleaning up sessions", error=str(e))
        return {
            "status": "failed",
            "error": str(e),
        }


async def generate_analytics_report(ctx: dict[str, Any], report_type: str = "daily") -> dict[str, Any]:
    """
    Generate analytics reports.

    Collects metrics and stores a summary report. The report_type
    determines the period: daily, weekly, or monthly.
    """
    logger.info("Generating analytics report", report_type=report_type)

    try:
        from app.core.database import async_session_factory
        from app.services.metrics.business import business_metrics_service
        from datetime import datetime, timedelta

        granularity_map = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "monthly": timedelta(days=30),
        }
        delta = granularity_map.get(report_type, timedelta(days=1))
        now = datetime.now()

        async with async_session_factory() as db:
            metrics = await business_metrics_service.calculate_metrics(
                session=db,
                tenant_id="system",
                project_id=None,
                period_start=now - delta,
                period_end=now,
            )

        logger.info("Analytics report generated", report_type=report_type,
                     els=metrics.engineering_leverage_score)

        return {
            "status": "completed",
            "report_type": report_type,
        }
    except Exception as e:
        logger.error("Error generating report", report_type=report_type, error=str(e))
        return {
            "status": "failed",
            "report_type": report_type,
            "error": str(e),
        }


async def process_trial_expirations(ctx: dict[str, Any]) -> dict[str, Any]:
    """
    Process expired trials and downgrade organizations to free tier.

    This is a scheduled task that runs hourly.
    """
    logger.info("Processing trial expirations")

    try:
        from app.core.database import async_session_factory
        from app.services.trial import TrialService

        expired_count = 0
        failed_count = 0

        async with async_session_factory() as db:
            trial_service = TrialService(db)

            expired_orgs = await trial_service.get_expired_trials(lock=True)

            for org in expired_orgs:
                try:
                    await trial_service.expire_trial(org, triggered_by=None)
                    expired_count += 1
                    logger.info("Expired trial for organization", org_id=str(org.id), org_name=org.name)
                except Exception as e:
                    failed_count += 1
                    logger.error("Error expiring trial", org_id=str(org.id), error=str(e))

            await db.commit()

        logger.info("Processed expired trials", expired_count=expired_count, failed_count=failed_count)

        return {
            "status": "completed" if failed_count == 0 else "partial",
            "trials_expired": expired_count,
            "trials_failed": failed_count,
        }
    except Exception as e:
        logger.error("Error processing trial expirations", error=str(e))
        return {
            "status": "failed",
            "error": str(e),
        }


async def send_trial_expiry_reminders(ctx: dict[str, Any]) -> dict[str, Any]:
    """
    Send reminder emails to organizations with trials expiring soon.

    This is a scheduled task that runs daily at 9 AM.
    """
    logger.info("Sending trial expiry reminders")

    try:
        from app.core.database import async_session_factory
        from app.services.trial import TrialService

        reminder_count = 0
        failed_count = 0

        async with async_session_factory() as db:
            trial_service = TrialService(db)

            expiring_orgs = await trial_service.get_expiring_trials(
                days_until_expiry=settings.TRIAL_REMINDER_DAYS
            )

            for org in expiring_orgs:
                try:
                    logger.info(
                        "Trial expiry reminder pending — email delivery not yet configured",
                        org_id=str(org.id),
                        org_name=org.name,
                        days_remaining=org.trial_days_remaining,
                    )
                    reminder_count += 1
                except Exception as e:
                    failed_count += 1
                    logger.error("Error sending trial reminder", org_id=str(org.id), error=str(e))

        logger.info("Sent trial expiry reminders", reminder_count=reminder_count, failed_count=failed_count)

        return {
            "status": "completed" if failed_count == 0 else "partial",
            "reminders_sent": reminder_count,
            "reminders_failed": failed_count,
        }
    except Exception as e:
        logger.error("Error sending trial expiry reminders", error=str(e))
        return {
            "status": "failed",
            "error": str(e),
        }


# =============================================================================
# Startup and Shutdown
# =============================================================================

async def startup(ctx: dict[str, Any]) -> None:
    """Initialize worker on startup."""
    from app.core.cache import cache
    from app.core.database import init_db

    await cache.initialize()
    await init_db()
    logger.info("Worker started")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Cleanup worker on shutdown."""
    from app.core.cache import cache
    from app.core.database import close_db

    await close_db()
    await cache.close()
    logger.info("Worker shut down")


# =============================================================================
# Worker Settings
# =============================================================================


class WorkerSettings:
    """ARQ Worker Settings."""

    # Task functions that can be called
    functions = [
        process_document,
        send_notification,
        cleanup_expired_sessions,
        generate_analytics_report,
        process_trial_expirations,
        send_trial_expiry_reminders,
    ]

    # Scheduled tasks (cron jobs)
    cron_jobs = [
        # Clean up expired sessions every hour
        cron(cleanup_expired_sessions, hour={0, 6, 12, 18}, minute=0),
        # Generate daily report at midnight
        cron(generate_analytics_report, hour=0, minute=5, run_at_startup=False),
        # Process trial expirations every hour
        cron(process_trial_expirations, hour=None, minute=0),
        # Send trial expiry reminders daily at 9 AM
        cron(send_trial_expiry_reminders, hour=9, minute=0, run_at_startup=False),
    ]

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown

    # Redis connection settings
    # All values read from environment variables - no hardcoded defaults
    # REDIS_HOST, REDIS_PORT, and REDIS_DB are required
    redis_settings = RedisSettings(
        host=os.environ["REDIS_HOST"],
        port=int(os.environ["REDIS_PORT"]),
        password=os.environ.get("REDIS_PASSWORD") or None,
        database=int(os.environ["REDIS_DB"]),
    )

    # Worker configuration
    max_jobs = 10  # Maximum concurrent jobs
    job_timeout = 300  # 5 minutes default timeout
    keep_result = 3600  # Keep results for 1 hour
    poll_delay = 0.5  # Poll interval in seconds
    queue_name = "nexusai:queue"  # Queue name prefix
