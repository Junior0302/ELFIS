"""Jobs Banking — sync connexion + sweep de récupération."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from app.banking.engine import BankingEngineError, SyncAlreadyInProgressError
from app.banking.errors import classify_connector_error, public_sync_error_message
from app.banking.sync_jobs import (
    connection_sync_idempotency_key,
    delayed_schedule,
    enqueue_connection_sync,
    enqueue_sync_sweep,
)
from app.banking.sync_status import RETRYABLE_ERROR_CODES
from app.config import settings
from app.jobs.job_context import JobContext
from app.jobs.job_exceptions import PermanentJobError, RetryableJobError
from app.jobs.job_models import ElfisJob
from app.jobs.job_registry import JobHandler
from app.jobs.job_schemas import JobExecutionResult
from app.jobs.job_types import JobNames
from app.observability.metrics import metrics_registry

logger = logging.getLogger(__name__)


class BankingSyncConnectionJobHandler(JobHandler):
    handler_name = "banking_sync_connection_v1"
    job_name = JobNames.BANKING_SYNC_CONNECTION

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        from app.banking.sync_engine import SyncEngine

        payload = job.payload if isinstance(job.payload, dict) else {}
        try:
            organization_id = int(payload["organization_id"])
            connection_id = int(payload["connection_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PermanentJobError("Payload banking.sync_connection.v1 invalide.") from exc
        trigger = str(payload.get("trigger") or "scheduled")
        correlation_id = str(payload.get("correlation_id") or job.correlation_id or "")

        from app.banking.banking_models import ElfisBankConnection
        from app.banking.consent import needs_reauth, reauth_reason_for, safe_consent_log

        connection = context.db.get(ElfisBankConnection, connection_id)
        if connection is not None and needs_reauth(connection):
            reason = reauth_reason_for(connection) or "user_action_required"
            safe_consent_log("banking_reauth_required", connection, reason_code=reason)
            return JobExecutionResult(
                status="completed",
                progress=100,
                message="user_action_required",
                result={
                    "skipped": True,
                    "reason": "user_action_required",
                    "organization_id": organization_id,
                    "connection_id": connection_id,
                    "trigger": trigger,
                    "reauth_reason": reason,
                },
            )

        try:
            runs = SyncEngine(context.db, max_attempts=1).run_sync(
                organization_id,
                connection_id=connection_id,
                trigger=trigger,
            )
        except SyncAlreadyInProgressError:
            logger.info(
                "banking_sync_completed",
                extra={
                    "organization_id": organization_id,
                    "connection_id": connection_id,
                    "trigger": trigger,
                    "skipped": "already_in_progress",
                    "correlation_id": correlation_id,
                },
            )
            return JobExecutionResult(
                status="completed",
                progress=100,
                message="already_in_progress",
                result={
                    "skipped": True,
                    "reason": "already_in_progress",
                    "organization_id": organization_id,
                    "connection_id": connection_id,
                    "trigger": trigger,
                },
            )
        except BankingEngineError as exc:
            raise PermanentJobError(str(exc)) from exc

        run = runs[0] if runs else None
        if run is None:
            raise PermanentJobError("Synchronisation sans run.")
        if run.status == "completed":
            return JobExecutionResult(
                status="completed",
                progress=100,
                message="sync_completed",
                result={
                    "organization_id": organization_id,
                    "connection_id": connection_id,
                    "trigger": trigger,
                    "run_id": run.id,
                    "transactions_created": run.transactions_created,
                    "transactions_updated": run.transactions_updated,
                    "duration_ms": run.duration_ms,
                },
            )

        from app.banking.banking_models import ElfisBankConnection

        connection = context.db.get(ElfisBankConnection, connection_id)
        error_code = (connection.last_sync_error_code if connection else None) or "unknown"
        if error_code in RETRYABLE_ERROR_CODES:
            delay = max(15, int(getattr(settings, "elfis_job_retry_base_seconds", 15) or 15))
            metrics_registry.incr(
                "elfis_banking_sync_retry_total",
                labels={"trigger": trigger, "error_code": error_code},
            )
            logger.info(
                "banking_sync_retry_scheduled",
                extra={
                    "organization_id": organization_id,
                    "connection_id": connection_id,
                    "provider": connection.provider if connection else None,
                    "trigger": trigger,
                    "error_code": error_code,
                    "retry_delay_seconds": delay,
                },
            )
            raise RetryableJobError(public_sync_error_message(error_code))
        raise PermanentJobError(public_sync_error_message(error_code))


class BankingSyncSweepJobHandler(JobHandler):
    handler_name = "banking_sync_sweep_v1"
    job_name = JobNames.BANKING_SYNC_SWEEP

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        payload = job.payload if isinstance(job.payload, dict) else {}
        stale_hours = payload.get("stale_hours")
        limit = payload.get("limit")
        from app.banking.sweep import select_stale_connections, watch_consent_lifecycle

        watch_consent_lifecycle(context.db)
        connections = select_stale_connections(
            context.db,
            stale_hours=int(stale_hours) if stale_hours is not None else None,
            limit=int(limit) if limit is not None else None,
        )
        jitter = max(0, int(settings.banking_sync_sweep_jitter_seconds))
        queued = 0
        skipped = 0
        from app.banking.sync_jobs import BankingSyncEnqueueError

        for connection in connections:
            trigger = "recovery" if connection.status == "error" else "scheduled"
            try:
                result = enqueue_connection_sync(
                    context.db,
                    organization_id=connection.organization_id,
                    connection_id=connection.id,
                    trigger=trigger,
                    scheduled_at=delayed_schedule(jitter),
                    idempotency_key=connection_sync_idempotency_key(connection.id, trigger),
                    provider=connection.provider,
                )
            except BankingSyncEnqueueError:
                skipped += 1
                continue
            if result.created:
                queued += 1
            else:
                skipped += 1

        if settings.banking_sync_sweep_reschedule:
            interval = max(15, int(settings.banking_sync_stale_hours) * 60)
            enqueue_sync_sweep(
                context.db,
                scheduled_at=datetime.utcnow() + timedelta(minutes=interval),
                payload={"source": "reschedule"},
            )

        return JobExecutionResult(
            status="completed",
            progress=100,
            message="sweep_completed",
            result={"eligible": len(connections), "queued": queued, "skipped": skipped},
        )


def register_banking_job_handlers(registry) -> None:
    for handler in (BankingSyncConnectionJobHandler(), BankingSyncSweepJobHandler()):
        if not registry.has(handler.job_name):
            registry.register(job_name=handler.job_name, handler=handler)
