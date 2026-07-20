"""Registry des tâches IA."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from app.ai.ai_exceptions import AIUnknownTaskError, AIValidationError
from app.ai.ai_types import ALL_KNOWN_AI_TASKS, IMPLEMENTED_AI_TASKS

if TYPE_CHECKING:
    from app.ai.ai_context import AIContext
    from app.ai.providers.base import AIProvider


class AITask(ABC):
    task_name: str
    task_version: int = 1
    default_provider: str = "openai"
    default_model: str = ""
    prompt_version: str = "v1"

    @abstractmethod
    def execute(
        self,
        input_data: dict[str, Any],
        context: "AIContext",
        provider: "AIProvider | None",
    ) -> dict[str, Any]:
        raise NotImplementedError

    def validate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise AIValidationError("sortie tâche invalide")
        return result


class AITaskRegistry:
    def __init__(self) -> None:
        self._tasks: dict[str, AITask] = {}

    def register(self, task: AITask) -> None:
        name = (task.task_name or "").strip()
        if not name:
            raise ValueError("task_name requis")
        if name not in ALL_KNOWN_AI_TASKS:
            raise AIUnknownTaskError(name)
        key = f"{name}@{task.task_version}"
        if key in self._tasks and self._tasks[key] is not task:
            raise ValueError(f"Tâche déjà enregistrée: {key}")
        self._tasks[key] = task

    def get(self, task_name: str, task_version: int = 1) -> AITask:
        key = f"{task_name}@{task_version}"
        task = self._tasks.get(key)
        if task is None:
            raise AIUnknownTaskError(task_name)
        return task

    def has(self, task_name: str, task_version: int = 1) -> bool:
        return f"{task_name}@{task_version}" in self._tasks

    def is_implemented(self, task_name: str) -> bool:
        return task_name in IMPLEMENTED_AI_TASKS and self.has(task_name)

    def clear(self) -> None:
        self._tasks.clear()


default_ai_registry = AITaskRegistry()
