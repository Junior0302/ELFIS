"""Exécuteur d'étapes — délègue au registre sans toucher aux statuts DB."""

from __future__ import annotations

from app.document_processing.context import ProcessingContext, ProcessingStepResult
from app.document_processing.step_registry import get_pipeline_registry


class ProcessingStepExecutor:
    """Exécute un handler enregistré ; l'orchestrateur seul mute la DB."""

    def __init__(self) -> None:
        self._registry = get_pipeline_registry()

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        handler = self._registry.get_handler(context.step.step_key)
        return await handler.execute(context)
