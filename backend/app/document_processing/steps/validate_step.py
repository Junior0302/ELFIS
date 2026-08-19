"""Étape validate_document_available."""

from __future__ import annotations

from app.document_processing.context import ProcessingContext, ProcessingStepResult
from app.document_processing.exceptions import ProcessingPermanentError
from app.document_processing.types import STEP_VALIDATE
from app.storage.storage_types import DocumentStatus, StorageObjectStatus


class ValidateDocumentAvailableStep:
    step_key = STEP_VALIDATE

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        doc = context.document
        ver = context.version
        if doc.organization_id != context.job.organization_id:
            raise ProcessingPermanentError("permission_denied", "Organisation incohérente")
        if doc.status == DocumentStatus.PURGED.value:
            raise ProcessingPermanentError("document_purged", "Document purgé")
        if doc.status == DocumentStatus.DELETED.value:
            return ProcessingStepResult(
                success=False,
                status="blocked",
                error_code="document_deleted",
                error_message_sanitized="Document soft-deleted",
                retryable=False,
            )
        if ver.document_id != doc.id:
            raise ProcessingPermanentError("version_not_found", "Version hors document")
        obj = context.storage_object
        if obj is None:
            raise ProcessingPermanentError("object_missing", "StorageObject absent")
        if obj.status == StorageObjectStatus.QUARANTINED.value:
            return ProcessingStepResult(
                success=False,
                status="blocked",
                error_code="object_quarantined",
                error_message_sanitized="Objet en quarantaine",
                retryable=False,
            )
        if obj.status != StorageObjectStatus.AVAILABLE.value:
            raise ProcessingPermanentError("object_unavailable", "Objet non disponible")
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={
                "document_status": doc.status,
                "version_number": ver.version_number,
                "storage_status": obj.status,
            },
        )
