"""ELFIS Job Queue V1 — file de travaux durable (distincte de l'Event Bus)."""

from __future__ import annotations

from app.jobs.job_registry import JobHandlerRegistry, default_job_registry
from app.jobs.job_schemas import JobExecutionResult, JobRequest, JobResult
from app.jobs.job_service import JobService
from app.jobs.job_types import JobNames, JobStatus
from app.jobs.job_worker import JobWorker, compute_job_retry_delay_seconds

_handlers_bootstrapped = False


def bootstrap_job_handlers(registry: JobHandlerRegistry | None = None) -> None:
    """Enregistre les handlers job V1 (idempotent)."""
    global _handlers_bootstrapped
    reg = registry or default_job_registry
    if registry is None and _handlers_bootstrapped:
        return

    from app.jobs.handlers.health_handlers import HealthCheckJobHandler
    from app.jobs.handlers.vault_handlers import VaultDocumentMetadataCheckHandler
    from app.jobs.handlers.ai_handlers import (
        DocumentClassificationJobHandler,
        DocumentInvoiceExtractionJobHandler,
        DocumentQualityCheckJobHandler,
    )
    from app.jobs.handlers.document_intelligence_handlers import (
        DocumentTextExtractionJobHandler,
        DocumentOCRJobHandler,
        DocumentPrepareAnalysisJobHandler,
    )
    from app.jobs.handlers.accounting_handlers import (
        AccountingProposalJobHandler,
        AccountingReprocessProposalJobHandler,
        AccountingValidateMappingJobHandler,
    )
    from app.jobs.handlers.search_handlers import (
        SearchIndexResourceJobHandler,
        SearchRemoveResourceJobHandler,
        SearchReindexOrganizationJobHandler,
    )
    from app.jobs.handlers.document_extraction_handlers import (
        DocumentExtractionRunJobHandler,
    )
    from app.ai import bootstrap_ai_tasks
    from app.document_intelligence.document_registry import bootstrap_extractors
    from app.search.search_registry import bootstrap_indexers

    bootstrap_ai_tasks()
    bootstrap_extractors()
    bootstrap_indexers()

    health = HealthCheckJobHandler()
    if not reg.has(health.job_name):
        reg.register(job_name=health.job_name, handler=health)

    meta = VaultDocumentMetadataCheckHandler()
    if not reg.has(meta.job_name):
        reg.register(job_name=meta.job_name, handler=meta)

    for handler in (
        DocumentTextExtractionJobHandler(),
        DocumentOCRJobHandler(),
        DocumentPrepareAnalysisJobHandler(),
        DocumentClassificationJobHandler(),
        DocumentInvoiceExtractionJobHandler(),
        DocumentQualityCheckJobHandler(),
        AccountingProposalJobHandler(),
        AccountingReprocessProposalJobHandler(),
        AccountingValidateMappingJobHandler(),
        SearchIndexResourceJobHandler(),
        SearchRemoveResourceJobHandler(),
        SearchReindexOrganizationJobHandler(),
        DocumentExtractionRunJobHandler(),
    ):
        if not reg.has(handler.job_name):
            reg.register(job_name=handler.job_name, handler=handler)

    from app.jobs.handlers.billing_handlers import register_billing_job_handlers
    from app.jobs.handlers.reliability_handlers import register_reliability_job_handlers

    register_billing_job_handlers(reg)
    register_reliability_job_handlers(reg)

    if registry is None:
        _handlers_bootstrapped = True


__all__ = [
    "JobExecutionResult",
    "JobHandlerRegistry",
    "JobNames",
    "JobRequest",
    "JobResult",
    "JobService",
    "JobStatus",
    "JobWorker",
    "bootstrap_job_handlers",
    "compute_job_retry_delay_seconds",
    "default_job_registry",
]
