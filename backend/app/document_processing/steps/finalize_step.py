"""Étape finalize_processing — résumé global borné."""

from __future__ import annotations

from app.document_processing.context import ProcessingContext, ProcessingStepResult
from app.document_processing.types import STEP_FINALIZE


class FinalizeProcessingStep:
    step_key = STEP_FINALIZE

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        job = context.job
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={
                "pipeline_key": job.pipeline_key,
                "document_id": job.document_id,
                "document_version_id": job.document_version_id,
                "finalized": True,
            },
        )
