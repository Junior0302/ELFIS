"""Handlers Job Queue — Accounting Pipeline."""

from __future__ import annotations

from app.accounting.accounting_exceptions import (
    AccountingDisabledError,
    AccountingNotFoundError,
    AccountingValidationError,
)
from app.accounting.accounting_schemas import AccountingPipelineRequest
from app.accounting.accounting_service import AccountingService
from app.jobs.job_context import JobContext
from app.jobs.job_exceptions import PermanentJobError, RetryableJobError
from app.jobs.job_models import ElfisJob
from app.jobs.job_registry import JobHandler
from app.jobs.job_schemas import JobExecutionResult
from app.jobs.job_types import JobNames


def _session(context: JobContext):
    if context._db is not None:
        return context._db, False
    if context._session_factory is None:
        raise RetryableJobError("session indisponible")
    return context._session_factory(), True


class AccountingProposalJobHandler(JobHandler):
    handler_name = "accounting_build_proposal_v1"
    job_name = JobNames.ACCOUNTING_BUILD_PROPOSAL

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        payload = job.payload if isinstance(job.payload, dict) else {}
        vault_document_id = str(payload.get("vault_document_id") or "").strip()
        if not vault_document_id:
            raise PermanentJobError("vault_document_id requis")
        version = int(payload.get("document_version") or 1)
        analysis_id = str(payload.get("document_analysis_id") or "").strip() or None

        context.update_progress(20, "building_proposal")
        db, own = _session(context)
        try:
            result = AccountingService(db).create_proposal(
                AccountingPipelineRequest(
                    organization_id=int(job.organization_id or 0),
                    user_id=job.user_id,
                    vault_document_id=vault_document_id,
                    document_analysis_id=analysis_id,
                    document_version=version,
                    correlation_id=job.correlation_id,
                    source_event_id=job.causation_event_id,
                    idempotency_key=job.idempotency_key,
                    job_id=job.job_id,
                )
            )
            context.update_progress(100, "done")
            return JobExecutionResult(
                status="completed",
                progress=100,
                message=result.status,
                result={
                    "proposal_id": result.proposal_id,
                    "entry_id": result.entry_id,
                    "status": result.status,
                    "requires_review": result.requires_review,
                    "balanced": bool((result.mapping_summary or {}).get("balanced")),
                },
            )
        except AccountingDisabledError as exc:
            raise PermanentJobError(exc.message) from None
        except AccountingNotFoundError as exc:
            raise PermanentJobError(exc.message) from None
        except AccountingValidationError as exc:
            raise PermanentJobError(exc.message) from None
        finally:
            if own:
                db.close()


class AccountingReprocessProposalJobHandler(JobHandler):
    handler_name = "accounting_reprocess_proposal_v1"
    job_name = JobNames.ACCOUNTING_REPROCESS_PROPOSAL

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        # V1 : même logique que build (idempotency gère la réutilisation)
        return AccountingProposalJobHandler().handle(job, context)


class AccountingValidateMappingJobHandler(JobHandler):
    """Préparé — revalidation mapping sans rebuild complet."""

    handler_name = "accounting_validate_mapping_v1"
    job_name = JobNames.ACCOUNTING_VALIDATE_MAPPING

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        payload = job.payload if isinstance(job.payload, dict) else {}
        return JobExecutionResult(
            status="completed",
            progress=100,
            message="validate_mapping_noop_v1",
            result={
                "proposal_id": payload.get("proposal_id"),
                "status": "noop",
            },
        )
