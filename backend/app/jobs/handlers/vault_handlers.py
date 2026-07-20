"""Handlers job — Vault (metadata check léger, sans PDF/IA)."""

from __future__ import annotations

from app.jobs.job_context import JobContext
from app.jobs.job_exceptions import PermanentJobError, RetryableJobError
from app.jobs.job_models import ElfisJob
from app.jobs.job_registry import JobHandler
from app.jobs.job_schemas import JobExecutionResult
from app.jobs.job_types import JobNames
from app.models_vault import VaultDocument
from app.schemas_vault import VaultArchiveStatus


class VaultDocumentMetadataCheckHandler(JobHandler):
    handler_name = "vault_document_metadata_check_v1"
    job_name = JobNames.VAULT_DOCUMENT_METADATA_CHECK

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        from sqlalchemy.orm import Session

        payload = job.payload if isinstance(job.payload, dict) else {}
        vault_document_id = str(payload.get("vault_document_id") or "").strip()
        expected_type = str(payload.get("expected_document_type") or "").strip() or None

        if not vault_document_id:
            raise PermanentJobError("vault_document_id requis")

        context.update_progress(10, "loading_document")

        # Session dédiée pour lecture — pas de téléchargement Storage
        db: Session | None = None
        own = False
        try:
            if context._db is not None:
                db = context._db
            elif context._session_factory is not None:
                db = context._session_factory()
                own = True
            else:
                raise RetryableJobError("session indisponible")

            doc = (
                db.query(VaultDocument)
                .filter(VaultDocument.id == vault_document_id)
                .first()
            )
            if not doc:
                raise PermanentJobError(f"document absent: {vault_document_id}")

            if (
                context.organization_id is not None
                and doc.organization_id != context.organization_id
            ):
                raise PermanentJobError("organization_id mismatch")

            if job.organization_id is not None and doc.organization_id != job.organization_id:
                raise PermanentJobError("organization_id mismatch")

            context.heartbeat()
            context.update_progress(60, "checking_metadata")

            type_ok = True
            if expected_type:
                type_ok = doc.document_type == expected_type

            size_ok = isinstance(doc.file_size, int) and doc.file_size > 0
            archive_ok = doc.archive_status == VaultArchiveStatus.archived.value

            valid = bool(type_ok and size_ok and archive_ok)
            result = {
                "valid": valid,
                "vault_document_id": vault_document_id,
                "checks": {
                    "document_type": type_ok,
                    "file_size": size_ok,
                    "archive_status": archive_ok,
                },
            }
            context.update_progress(100, "done")
            return JobExecutionResult(
                status="completed",
                progress=100,
                message="metadata_check_ok" if valid else "metadata_check_failed",
                result=result,
            )
        finally:
            if db is not None and own:
                db.close()
