"""Étape finalize_processing."""

from __future__ import annotations

from app.document_processing.context import ProcessingContext, ProcessingStepResult
from app.document_processing.types import STEP_FINALIZE


class FinalizeProcessingStep:
    step_key = STEP_FINALIZE

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={
                "finalized": True,
                "pipeline_key": context.job.pipeline_key,
                "document_id": context.job.document_id,
                "version_id": context.job.document_version_id,
            },
        )
