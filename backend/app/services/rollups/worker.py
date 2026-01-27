"""Background worker for computing metric rollups."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.services.rollups.models import RollupGranularity
from app.services.rollups.service import RollupService, get_rollup_service

logger = structlog.get_logger()


class RollupWorker:
    """Background worker for periodic rollup computation.

    Computes rollups at different granularities:
    - Hourly: Every hour
    - Daily: At midnight
    - Weekly: Every Sunday
    - Monthly: First of month
    """

    def __init__(
        self,
        rollup_service: RollupService | None = None,
        get_session=None,
    ):
        self.rollup_service = rollup_service or get_rollup_service()
        self._get_session = get_session
        self._running = False
        self._tasks: dict[str, asyncio.Task] = {}

    async def start(self) -> None:
        """Start the rollup worker."""
        if self._running:
            return

        self._running = True

        # Start computation loops for each granularity
        self._tasks["hourly"] = asyncio.create_task(
            self._run_hourly_loop()
        )
        self._tasks["daily"] = asyncio.create_task(
            self._run_daily_loop()
        )

        logger.info("Rollup worker started")

    async def stop(self) -> None:
        """Stop the rollup worker."""
        self._running = False

        for name, task in self._tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks.clear()
        logger.info("Rollup worker stopped")

    async def _run_hourly_loop(self) -> None:
        """Run hourly rollup computation loop."""
        while self._running:
            try:
                # Wait until the top of the next hour
                now = datetime.now(UTC)
                next_hour = (now + timedelta(hours=1)).replace(
                    minute=0, second=0, microsecond=0
                )
                wait_seconds = (next_hour - now).total_seconds()

                await asyncio.sleep(wait_seconds)

                if not self._running:
                    break

                # Compute hourly rollups
                await self._compute_rollups(
                    RollupGranularity.HOURLY,
                    now - timedelta(hours=1),
                    now,
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Hourly rollup loop error", error=str(e))
                await asyncio.sleep(60)

    async def _run_daily_loop(self) -> None:
        """Run daily rollup computation loop."""
        while self._running:
            try:
                # Wait until midnight
                now = datetime.now(UTC)
                tomorrow = (now + timedelta(days=1)).replace(
                    hour=0, minute=5, second=0, microsecond=0
                )
                wait_seconds = (tomorrow - now).total_seconds()

                await asyncio.sleep(wait_seconds)

                if not self._running:
                    break

                # Compute daily rollups for yesterday
                yesterday = now.replace(hour=0, minute=0, second=0, microsecond=0)
                today = yesterday + timedelta(days=1)

                await self._compute_rollups(
                    RollupGranularity.DAILY,
                    yesterday,
                    today,
                )

                # On Sunday, compute weekly rollups
                if now.weekday() == 6:  # Sunday
                    week_start = yesterday - timedelta(days=6)
                    await self._compute_rollups(
                        RollupGranularity.WEEKLY,
                        week_start,
                        today,
                    )

                # On first of month, compute monthly rollups
                if now.day == 1:
                    month_start = yesterday.replace(day=1)
                    await self._compute_rollups(
                        RollupGranularity.MONTHLY,
                        month_start,
                        today,
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Daily rollup loop error", error=str(e))
                await asyncio.sleep(300)

    async def _compute_rollups(
        self,
        granularity: RollupGranularity,
        period_start: datetime,
        period_end: datetime,
    ) -> None:
        """Compute rollups for all tenants.

        Args:
            granularity: Time granularity
            period_start: Start of period
            period_end: End of period
        """
        if not self._get_session:
            logger.warning("No session factory configured")
            return

        async with self._get_session() as session:
            # Get all active tenants
            tenants = await self._get_active_tenants(session)

            for tenant_id in tenants:
                try:
                    # Compute DORA rollup
                    dora_rollup = await self.rollup_service.compute_dora_rollup(
                        session,
                        tenant_id,
                        period_start,
                        period_end,
                        granularity,
                    )
                    await self.rollup_service.save_rollup(session, dora_rollup)

                    # Compute SPACE rollup
                    space_rollup = await self.rollup_service.compute_space_rollup(
                        session,
                        tenant_id,
                        period_start,
                        period_end,
                        granularity,
                    )
                    await self.rollup_service.save_rollup(session, space_rollup)

                    logger.info(
                        "Computed rollups",
                        tenant_id=tenant_id,
                        granularity=granularity.value,
                        period=f"{period_start.date()} to {period_end.date()}",
                    )

                except Exception as e:
                    logger.error(
                        "Failed to compute rollups for tenant",
                        tenant_id=tenant_id,
                        error=str(e),
                    )

            await session.commit()

    async def _get_active_tenants(self, session) -> list[str]:
        """Get list of active tenant IDs."""
        from sqlalchemy import text

        result = await session.execute(
            text("SELECT DISTINCT tenant_id FROM organizations WHERE is_active = true")
        )
        return [str(row.tenant_id) for row in result.fetchall()]

    async def backfill(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
        granularities: list[RollupGranularity] | None = None,
    ) -> dict[str, Any]:
        """Backfill rollups for a time range.

        Args:
            tenant_id: Tenant ID
            start_date: Start of backfill range
            end_date: End of backfill range
            granularities: List of granularities to backfill (default: all)

        Returns:
            Backfill results
        """
        granularities = granularities or [
            RollupGranularity.DAILY,
            RollupGranularity.WEEKLY,
        ]

        results = {
            "tenant_id": tenant_id,
            "start_date": start_date,
            "end_date": end_date,
            "rollups_computed": 0,
            "errors": [],
        }

        if not self._get_session:
            results["errors"].append("No session factory configured")
            return results

        async with self._get_session() as session:
            for granularity in granularities:
                # Determine step size
                if granularity == RollupGranularity.HOURLY:
                    step = timedelta(hours=1)
                elif granularity == RollupGranularity.DAILY:
                    step = timedelta(days=1)
                elif granularity == RollupGranularity.WEEKLY:
                    step = timedelta(weeks=1)
                else:
                    step = timedelta(days=30)

                current = start_date
                while current < end_date:
                    period_end = min(current + step, end_date)

                    try:
                        # Compute DORA
                        dora = await self.rollup_service.compute_dora_rollup(
                            session, tenant_id, current, period_end, granularity
                        )
                        await self.rollup_service.save_rollup(session, dora)

                        # Compute SPACE
                        space = await self.rollup_service.compute_space_rollup(
                            session, tenant_id, current, period_end, granularity
                        )
                        await self.rollup_service.save_rollup(session, space)

                        results["rollups_computed"] += 2

                    except Exception as e:
                        results["errors"].append(
                            f"{granularity.value} {current.date()}: {str(e)}"
                        )

                    current = period_end

            await session.commit()

        logger.info(
            "Backfill completed",
            tenant_id=tenant_id,
            rollups=results["rollups_computed"],
            errors=len(results["errors"]),
        )

        return results

    async def compute_now(
        self,
        tenant_id: str,
        granularity: RollupGranularity,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Compute rollups for the current period.

        Args:
            tenant_id: Tenant ID
            granularity: Time granularity
            project_id: Optional project filter

        Returns:
            Computed rollup data
        """
        now = datetime.now(UTC)

        # Determine period bounds
        if granularity == RollupGranularity.HOURLY:
            period_start = now.replace(minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(hours=1)
        elif granularity == RollupGranularity.DAILY:
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)
        elif granularity == RollupGranularity.WEEKLY:
            period_start = now - timedelta(days=now.weekday())
            period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(weeks=1)
        else:
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Next month
            if now.month == 12:
                period_end = period_start.replace(year=now.year + 1, month=1)
            else:
                period_end = period_start.replace(month=now.month + 1)

        if not self._get_session:
            return {"error": "No session factory configured"}

        async with self._get_session() as session:
            dora = await self.rollup_service.compute_dora_rollup(
                session, tenant_id, period_start, period_end, granularity, project_id
            )
            space = await self.rollup_service.compute_space_rollup(
                session, tenant_id, period_start, period_end, granularity, project_id
            )

            await self.rollup_service.save_rollup(session, dora)
            await self.rollup_service.save_rollup(session, space)
            await session.commit()

        return {
            "period_start": period_start,
            "period_end": period_end,
            "dora": dora.model_dump(),
            "space": space.model_dump(),
        }
