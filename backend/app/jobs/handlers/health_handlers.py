"""Handlers job — health check."""

from __future__ import annotations

from datetime import datetime

from app.jobs.job_context import JobContext
from app.jobs.job_exceptions import PermanentJobError, RetryableJobError
from app.jobs.job_models import ElfisJob
from app.jobs.job_registry import JobHandler
from app.jobs.job_schemas import JobExecutionResult
from app.jobs.job_types import JobNames


class HealthCheckJobHandler(JobHandler):
    handler_name = "system_health_check_v1"
    job_name = JobNames.SYSTEM_HEALTH_CHECK

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        payload = job.payload if isinstance(job.payload, dict) else {}
        message = str(payload.get("message") or "ok")
        simulate = str(payload.get("simulate") or "").strip().lower()

        if simulate == "progress":
            context.update_progress(25, "starting")
            context.heartbeat()
            context.update_progress(75, "almost_done")

        if simulate == "retry":
            raise RetryableJobError(str(payload.get("error") or "temporary failure"))
        if simulate == "permanent":
            raise PermanentJobError(str(payload.get("error") or "permanent failure"))
        if simulate == "timeout":
            # Simulation : le worker compare duration vs timeout après coup —
            # on signale via Retryable pour tests dédiés timeout séparés.
            raise RetryableJobError("simulated_slow_handler")

        context.update_progress(100, "done")
        return JobExecutionResult(
            status="completed",
            progress=100,
            message="health_ok",
            result={
                "ok": True,
                "echo": message,
                "processed_at": datetime.utcnow().isoformat() + "Z",
            },
        )
