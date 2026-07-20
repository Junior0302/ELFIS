"""ELFIS AI Engine V1 — moteur IA transverse (OpenAI + tâches documentaires)."""

from __future__ import annotations

from app.ai.ai_registry import AITaskRegistry, default_ai_registry
from app.ai.ai_schemas import AIExecutionRequest, AIExecutionResult
from app.ai.ai_service import AIService
from app.ai.ai_types import AITaskNames

_bootstrapped = False


def bootstrap_ai_tasks(registry: AITaskRegistry | None = None) -> None:
    global _bootstrapped
    reg = registry or default_ai_registry
    if registry is None and _bootstrapped:
        return

    from app.ai.tasks.document_classification import DocumentClassifyTask
    from app.ai.tasks.document_extraction import DocumentExtractInvoiceTask
    from app.ai.tasks.document_quality import DocumentQualityCheckTask
    from app.config import settings

    for task_cls in (
        DocumentClassifyTask,
        DocumentExtractInvoiceTask,
        DocumentQualityCheckTask,
    ):
        task = task_cls()
        if not task.default_model:
            task.default_model = settings.elfis_ai_default_model or settings.openai_chat_model
        if not reg.has(task.task_name, task.task_version):
            reg.register(task)

    if registry is None:
        _bootstrapped = True


__all__ = [
    "AIExecutionRequest",
    "AIExecutionResult",
    "AIService",
    "AITaskNames",
    "AITaskRegistry",
    "bootstrap_ai_tasks",
    "default_ai_registry",
]
