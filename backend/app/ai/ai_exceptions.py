"""Exceptions AI Engine."""

from __future__ import annotations


class AIError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class AIValidationError(AIError):
    def __init__(self, message: str):
        super().__init__("validation_error", message)


class AIUnknownTaskError(AIError):
    def __init__(self, task_name: str):
        super().__init__("unknown_task", f"Tâche IA inconnue: {task_name}")


class AIProviderError(AIError):
    def __init__(self, message: str):
        super().__init__("provider_error", message)


class AIDisabledError(AIError):
    def __init__(self, message: str = "ELFIS AI désactivé"):
        super().__init__("ai_disabled", message)


class AINotFoundError(AIError):
    def __init__(self, message: str = "Exécution IA introuvable"):
        super().__init__("not_found", message)


class AIBlockedError(AIError):
    def __init__(self, message: str):
        super().__init__("blocked", message)
