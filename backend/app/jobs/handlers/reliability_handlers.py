"""Jobs reliability V1."""

from __future__ import annotations

from datetime import datetime

from app.jobs.job_context import JobContext
from app.jobs.job_models import ElfisJob
from app.jobs.job_registry import JobHandler
from app.jobs.job_schemas import JobExecutionResult
from app.jobs.job_types import JobNames
from app.reliability.cleanup_service import CleanupService
from app.reliability.readiness_service import ReadinessService


class ReliabilityCleanupHandler(JobHandler):
    handler_name = "reliability_cleanup_expired_records_v1"
    job_name = JobNames.RELIABILITY_CLEANUP_EXPIRED_RECORDS

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        payload = job.payload if isinstance(job.payload, dict) else {}
        force_dry = payload.get("dry_run")
        if force_dry is not None:
            force_dry = bool(force_dry)
        summary = CleanupService(context.db).run(force_dry_run=force_dry)
        context.update_progress(100, "cleanup_done")
        return JobExecutionResult(
            status="completed",
            progress=100,
            message="cleanup_completed",
            result={**summary, "processed_at": datetime.utcnow().isoformat() + "Z"},
        )


class ReliabilityHealthHandler(JobHandler):
    handler_name = "reliability_check_system_health_v1"
    job_name = JobNames.RELIABILITY_CHECK_SYSTEM_HEALTH

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        result = ReadinessService(context.db).readiness()
        return JobExecutionResult(
            status="completed",
            progress=100,
            message="health_checked",
            result=result,
        )


class ReliabilityStaleJobsHandler(JobHandler):
    handler_name = "reliability_detect_stale_jobs_v1"
    job_name = JobNames.RELIABILITY_DETECT_STALE_JOBS

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        result = ReadinessService(context.db).detect_stale_jobs()
        context.db.commit()
        return JobExecutionResult(
            status="completed",
            progress=100,
            message="stale_jobs_scanned",
            result=result,
        )


class ReliabilityStaleEventsHandler(JobHandler):
    handler_name = "reliability_detect_stale_events_v1"
    job_name = JobNames.RELIABILITY_DETECT_STALE_EVENTS

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        result = ReadinessService(context.db).detect_stale_events()
        context.db.commit()
        return JobExecutionResult(
            status="completed",
            progress=100,
            message="stale_events_scanned",
            result=result,
        )


def register_reliability_job_handlers(registry) -> None:
    for handler in (
        ReliabilityCleanupHandler(),
        ReliabilityHealthHandler(),
        ReliabilityStaleJobsHandler(),
        ReliabilityStaleEventsHandler(),
    ):
        if not registry.has(handler.job_name):
            registry.register(job_name=handler.job_name, handler=handler)
