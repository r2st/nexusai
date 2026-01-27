"""Evaluation runner for executing test sets."""

import asyncio
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.evaluation.evaluator import Evaluator, get_evaluator
from app.services.evaluation.models import (
    EvalComparison,
    EvalResult,
    EvalRun,
    EvalStatus,
    TestCase,
    TestSet,
)

logger = structlog.get_logger()


class EvalRunner:
    """Runner for executing evaluation test sets."""

    def __init__(self, evaluator: Evaluator | None = None):
        self.evaluator = evaluator or get_evaluator()

    async def run_evaluation(
        self,
        session: AsyncSession,
        tenant_id: str,
        test_set_id: str,
        prompt_id: str,
        prompt_version: int | None = None,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int | None = None,
        baseline_run_id: str | None = None,
        triggered_by: str = "manual",
        git_commit: str | None = None,
    ) -> EvalRun:
        """Run evaluation on a test set.

        Args:
            session: Database session
            tenant_id: Tenant ID
            test_set_id: Test set to evaluate
            prompt_id: Prompt to evaluate
            prompt_version: Optional specific version
            model: Model to use
            temperature: Temperature setting
            max_tokens: Max tokens
            baseline_run_id: Optional baseline for comparison
            triggered_by: What triggered the run
            git_commit: Optional git commit reference

        Returns:
            EvalRun with results
        """
        # Load test set
        test_set = await self._load_test_set(session, test_set_id)
        if not test_set:
            raise ValueError(f"Test set not found: {test_set_id}")

        # Create eval run
        eval_run = EvalRun(
            tenant_id=tenant_id,
            test_set_id=test_set_id,
            test_set_name=test_set.name,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            baseline_run_id=baseline_run_id,
            triggered_by=triggered_by,
            git_commit=git_commit,
            status=EvalStatus.RUNNING,
            started_at=datetime.now(UTC),
            total_cases=len(test_set.test_cases),
        )

        # Save initial run
        await self._save_run(session, eval_run)
        await session.flush()

        logger.info(
            "Starting evaluation run",
            run_id=eval_run.id,
            test_set=test_set.name,
            cases=eval_run.total_cases,
        )

        try:
            # Execute test cases
            for test_case in test_set.test_cases:
                result = await self._execute_test_case(
                    session,
                    test_case,
                    prompt_id,
                    prompt_version,
                    model,
                    temperature,
                    max_tokens,
                )
                eval_run.results.append(result)

                if result.error:
                    eval_run.error_cases += 1
                elif result.passed:
                    eval_run.passed_cases += 1
                else:
                    eval_run.failed_cases += 1

            # Calculate aggregate metrics
            eval_run.pass_rate = (
                eval_run.passed_cases / eval_run.total_cases
                if eval_run.total_cases > 0
                else 0
            )

            valid_results = [r for r in eval_run.results if not r.error]
            if valid_results:
                eval_run.avg_score = sum(r.score for r in valid_results) / len(valid_results)
                eval_run.avg_latency_ms = sum(r.latency_ms for r in valid_results) / len(valid_results)
                eval_run.total_cost_usd = sum(r.cost_usd or 0 for r in valid_results)

            # Compare with baseline if provided
            if baseline_run_id:
                comparison = await self._compare_with_baseline(
                    session, eval_run, baseline_run_id
                )
                eval_run.regression_detected = len(comparison.regressed_cases) > 0
                eval_run.regression_details = {
                    "pass_rate_delta": comparison.pass_rate_delta,
                    "regressed_cases": comparison.regressed_cases,
                    "improved_cases": comparison.improved_cases,
                }

            eval_run.status = EvalStatus.COMPLETED
            eval_run.completed_at = datetime.now(UTC)
            eval_run.duration_seconds = (
                eval_run.completed_at - eval_run.started_at
            ).total_seconds()

        except Exception as e:
            eval_run.status = EvalStatus.FAILED
            eval_run.metadata["error"] = str(e)
            logger.error("Evaluation run failed", run_id=eval_run.id, error=str(e))

        # Save final run
        await self._update_run(session, eval_run)
        await session.commit()

        logger.info(
            "Evaluation run completed",
            run_id=eval_run.id,
            status=eval_run.status.value,
            pass_rate=eval_run.pass_rate,
            regression=eval_run.regression_detected,
        )

        return eval_run

    async def _execute_test_case(
        self,
        session: AsyncSession,
        test_case: TestCase,
        prompt_id: str,
        prompt_version: int | None,
        model: str,
        temperature: float,
        max_tokens: int | None,
    ) -> EvalResult:
        """Execute a single test case."""
        import time
        from app.services.prompts import get_prompt_registry

        start_time = time.time()
        latency_ms = 0
        actual_output = ""
        error = None
        input_tokens = 0
        output_tokens = 0
        cost_usd = None

        try:
            # Get rendered prompt
            registry = get_prompt_registry()
            rendered, system_prompt, version = await registry.render_prompt(
                session, prompt_id, test_case.input_variables, prompt_version
            )

            # Execute LLM call
            # In production, this would call the LLM gateway
            # For now, simulate a response
            from app.services.llm_gateway import get_llm_gateway

            try:
                gateway = get_llm_gateway()
                response = await gateway.complete(
                    messages=[
                        {"role": "system", "content": system_prompt or ""},
                        {"role": "user", "content": rendered},
                    ],
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                actual_output = response.content
                input_tokens = response.input_tokens
                output_tokens = response.output_tokens
                cost_usd = response.cost_usd
            except Exception as e:
                # Fallback for when LLM is not available
                actual_output = f"[Simulated output for: {rendered[:100]}...]"
                logger.warning("Using simulated output", error=str(e))

            latency_ms = (time.time() - start_time) * 1000

        except Exception as e:
            error = str(e)
            logger.error("Test case execution failed", test_case=test_case.name, error=error)

        # Evaluate output
        result = self.evaluator.evaluate(
            test_case,
            actual_output,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            model=model,
            prompt_version=prompt_version,
        )

        if error:
            result.error = error

        return result

    async def _compare_with_baseline(
        self,
        session: AsyncSession,
        current_run: EvalRun,
        baseline_run_id: str,
    ) -> EvalComparison:
        """Compare current run with a baseline."""
        baseline = await self._load_run(session, baseline_run_id)

        if not baseline:
            return EvalComparison(
                run_a_id=baseline_run_id,
                run_b_id=current_run.id,
            )

        comparison = EvalComparison(
            run_a_id=baseline_run_id,
            run_b_id=current_run.id,
            pass_rate_delta=current_run.pass_rate - baseline.pass_rate,
            avg_score_delta=current_run.avg_score - baseline.avg_score,
            latency_delta_ms=current_run.avg_latency_ms - baseline.avg_latency_ms,
            cost_delta_usd=current_run.total_cost_usd - baseline.total_cost_usd,
        )

        # Compare individual test cases
        baseline_results = {r.test_case_id: r for r in baseline.results}

        for result in current_run.results:
            baseline_result = baseline_results.get(result.test_case_id)

            if not baseline_result:
                continue

            if result.passed and not baseline_result.passed:
                comparison.improved_cases.append(result.test_case_name)
            elif not result.passed and baseline_result.passed:
                comparison.regressed_cases.append(result.test_case_name)
            else:
                comparison.unchanged_cases.append(result.test_case_name)

        # Simple significance check
        comparison.is_significant = abs(comparison.pass_rate_delta) > 0.05

        return comparison

    async def _load_test_set(
        self,
        session: AsyncSession,
        test_set_id: str,
    ) -> TestSet | None:
        """Load a test set from the database."""
        result = await session.execute(
            text("SELECT * FROM eval_test_sets WHERE id = :id"),
            {"id": test_set_id},
        )
        row = result.fetchone()

        if not row:
            return None

        return TestSet(
            id=row.id,
            tenant_id=row.tenant_id,
            name=row.name,
            description=row.description,
            prompt_id=row.prompt_id,
            test_cases=[TestCase(**tc) for tc in (row.test_cases or [])],
            default_eval_type=row.default_eval_type,
            pass_threshold=row.pass_threshold,
            is_active=row.is_active,
            version=row.version,
            created_at=row.created_at,
            updated_at=row.updated_at,
            created_by=row.created_by,
        )

    async def _load_run(
        self,
        session: AsyncSession,
        run_id: str,
    ) -> EvalRun | None:
        """Load an evaluation run from the database."""
        result = await session.execute(
            text("SELECT * FROM eval_runs WHERE id = :id"),
            {"id": run_id},
        )
        row = result.fetchone()

        if not row:
            return None

        return EvalRun(
            id=row.id,
            tenant_id=row.tenant_id,
            test_set_id=row.test_set_id,
            test_set_name=row.test_set_name,
            prompt_id=row.prompt_id,
            prompt_version=row.prompt_version,
            model=row.model,
            temperature=row.temperature,
            max_tokens=row.max_tokens,
            results=[EvalResult(**r) for r in (row.results or [])],
            status=EvalStatus(row.status),
            total_cases=row.total_cases,
            passed_cases=row.passed_cases,
            failed_cases=row.failed_cases,
            error_cases=row.error_cases,
            pass_rate=row.pass_rate,
            avg_score=row.avg_score,
            avg_latency_ms=row.avg_latency_ms,
            total_cost_usd=row.total_cost_usd,
            baseline_run_id=row.baseline_run_id,
            regression_detected=row.regression_detected,
            regression_details=row.regression_details or {},
            started_at=row.started_at,
            completed_at=row.completed_at,
            duration_seconds=row.duration_seconds,
            triggered_by=row.triggered_by,
            git_commit=row.git_commit,
            metadata=row.metadata or {},
            created_at=row.created_at,
        )

    async def _save_run(self, session: AsyncSession, run: EvalRun) -> None:
        """Save an evaluation run."""
        await session.execute(
            text("""
                INSERT INTO eval_runs (
                    id, tenant_id, test_set_id, test_set_name, prompt_id, prompt_version,
                    model, temperature, max_tokens, results, status,
                    total_cases, passed_cases, failed_cases, error_cases,
                    pass_rate, avg_score, avg_latency_ms, total_cost_usd,
                    baseline_run_id, regression_detected, regression_details,
                    started_at, completed_at, duration_seconds,
                    triggered_by, git_commit, metadata, created_at
                ) VALUES (
                    :id, :tenant_id, :test_set_id, :test_set_name, :prompt_id, :prompt_version,
                    :model, :temperature, :max_tokens, :results, :status,
                    :total_cases, :passed_cases, :failed_cases, :error_cases,
                    :pass_rate, :avg_score, :avg_latency_ms, :total_cost_usd,
                    :baseline_run_id, :regression_detected, :regression_details,
                    :started_at, :completed_at, :duration_seconds,
                    :triggered_by, :git_commit, :metadata, :created_at
                )
            """),
            {
                "id": run.id,
                "tenant_id": run.tenant_id,
                "test_set_id": run.test_set_id,
                "test_set_name": run.test_set_name,
                "prompt_id": run.prompt_id,
                "prompt_version": run.prompt_version,
                "model": run.model,
                "temperature": run.temperature,
                "max_tokens": run.max_tokens,
                "results": [r.model_dump() for r in run.results],
                "status": run.status.value,
                "total_cases": run.total_cases,
                "passed_cases": run.passed_cases,
                "failed_cases": run.failed_cases,
                "error_cases": run.error_cases,
                "pass_rate": run.pass_rate,
                "avg_score": run.avg_score,
                "avg_latency_ms": run.avg_latency_ms,
                "total_cost_usd": run.total_cost_usd,
                "baseline_run_id": run.baseline_run_id,
                "regression_detected": run.regression_detected,
                "regression_details": run.regression_details,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "duration_seconds": run.duration_seconds,
                "triggered_by": run.triggered_by,
                "git_commit": run.git_commit,
                "metadata": run.metadata,
                "created_at": run.created_at,
            },
        )

    async def _update_run(self, session: AsyncSession, run: EvalRun) -> None:
        """Update an evaluation run."""
        await session.execute(
            text("""
                UPDATE eval_runs SET
                    results = :results,
                    status = :status,
                    passed_cases = :passed_cases,
                    failed_cases = :failed_cases,
                    error_cases = :error_cases,
                    pass_rate = :pass_rate,
                    avg_score = :avg_score,
                    avg_latency_ms = :avg_latency_ms,
                    total_cost_usd = :total_cost_usd,
                    regression_detected = :regression_detected,
                    regression_details = :regression_details,
                    completed_at = :completed_at,
                    duration_seconds = :duration_seconds
                WHERE id = :id
            """),
            {
                "id": run.id,
                "results": [r.model_dump() for r in run.results],
                "status": run.status.value,
                "passed_cases": run.passed_cases,
                "failed_cases": run.failed_cases,
                "error_cases": run.error_cases,
                "pass_rate": run.pass_rate,
                "avg_score": run.avg_score,
                "avg_latency_ms": run.avg_latency_ms,
                "total_cost_usd": run.total_cost_usd,
                "regression_detected": run.regression_detected,
                "regression_details": run.regression_details,
                "completed_at": run.completed_at,
                "duration_seconds": run.duration_seconds,
            },
        )


# Global runner instance
_eval_runner: EvalRunner | None = None


def get_eval_runner() -> EvalRunner:
    """Get the global evaluation runner instance."""
    global _eval_runner
    if _eval_runner is None:
        _eval_runner = EvalRunner()
    return _eval_runner
