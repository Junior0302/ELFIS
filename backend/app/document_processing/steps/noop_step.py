"""Étape noop — simule traitement court (pas de lecture fichier)."""

from __future__ import annotations

import asyncio

from app.document_processing.context import ProcessingContext, ProcessingStepResult
from app.document_processing.exceptions import ProcessingPermanentError, ProcessingRetryableError
from app.document_processing.types import STEP_NOOP


class NoopProcessingStep:
    step_key = STEP_NOOP

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = context.job.metadata_json or {}
        mode = str(meta.get("noop_mode") or "ok")
        # Simulation courte — aucun contenu document
        await asyncio.sleep(0)
        if mode == "retryable":
            raise ProcessingRetryableError("noop_retryable", "Échec noop volontaire retryable")
        if mode == "permanent":
            raise ProcessingPermanentError("noop_permanent", "Échec noop permanent")
        if mode == "timeout":
            # Le timeout réel est géré par l'orchestrateur ; ici on signale
            raise ProcessingRetryableError("timeout", "Timeout noop simulé")
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={"noop": True, "mode": mode},
        )
