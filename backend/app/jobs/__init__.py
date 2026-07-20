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
    from app.ai import bootstrap_ai_tasks

    bootstrap_ai_tasks()

    health = HealthCheckJobHandler()
    if not reg.has(health.job_name):
        reg.register(job_name=health.job_name, handler=health)

    meta = VaultDocumentMetadataCheckHandler()
    if not reg.has(meta.job_name):
        reg.register(job_name=meta.job_name, handler=meta)

    for handler in (
        DocumentClassificationJobHandler(),
        DocumentInvoiceExtractionJobHandler(),
        DocumentQualityCheckJobHandler(),
    ):
        if not reg.has(handler.job_name):
            reg.register(job_name=handler.job_name, handler=handler)

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
