"""Étape inspect_storage_metadata — métadonnées techniques uniquement."""

from __future__ import annotations

from app.document_processing.context import ProcessingContext, ProcessingStepResult
from app.document_processing.exceptions import ProcessingPermanentError
from app.document_processing.types import STEP_INSPECT


class InspectStorageMetadataStep:
    step_key = STEP_INSPECT

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        obj = context.storage_object
        ver = context.version
        if obj is None:
            raise ProcessingPermanentError("object_missing", "StorageObject absent")
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={
                "size_bytes": int(obj.size_bytes or 0),
                "mime": obj.mime_type_detected or obj.mime_type_declared,
                "checksum_present": bool(obj.checksum_sha256),
                "provider": obj.provider,
                "version_number": ver.version_number,
                # pas d'object_key / path
            },
        )
