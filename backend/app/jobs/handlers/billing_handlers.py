"""Jobs Billing — rappels essai / sync abonnement."""

from __future__ import annotations

from app.jobs.job_context import JobContext
from app.jobs.job_models import ElfisJob
from app.jobs.job_registry import JobHandler
from app.jobs.job_schemas import JobExecutionResult
from app.jobs.job_types import JobNames


class BillingTrialRemindersJobHandler(JobHandler):
    handler_name = "billing_trial_reminders_v1"
    job_name = JobNames.BILLING_TRIAL_REMINDERS

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        from app.subscriptions.notifications import run_trial_reminders

        payload = job.payload if isinstance(job.payload, dict) else {}
        days = int(payload.get("days_before") or 3)
        count = run_trial_reminders(context.db, days_before=days)
        return JobExecutionResult(
            status="completed",
            progress=100,
            message="trial_reminders_done",
            result={"reminders": count, "days_before": days},
        )


class BillingSyncSubscriptionJobHandler(JobHandler):
    handler_name = "billing_sync_subscription_v1"
    job_name = JobNames.BILLING_SYNC_SUBSCRIPTION

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        payload = job.payload if isinstance(job.payload, dict) else {}
        org_id = int(payload["organization_id"])
        from app.billing.subscription_service import SubscriptionService

        sub = SubscriptionService(context.db).sync_from_legacy(org_id, rebuild=True)
        return JobExecutionResult(
            status="completed",
            progress=100,
            message="subscription_synced",
            result={
                "organization_id": org_id,
                "subscription_id": sub.subscription_id if sub else None,
                "status": sub.status if sub else None,
            },
        )


def register_billing_job_handlers(registry) -> None:
    for handler in (BillingTrialRemindersJobHandler(), BillingSyncSubscriptionJobHandler()):
        if not registry.has(handler.job_name):
            registry.register(job_name=handler.job_name, handler=handler)
