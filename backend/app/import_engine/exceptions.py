"""Exceptions Import Engine."""

from __future__ import annotations


class ImportEngineError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class ImportNotFoundError(ImportEngineError):
    def __init__(self, message: str = "Import introuvable"):
        super().__init__("import_not_found", message)


class ImportStateError(ImportEngineError):
    def __init__(self, message: str = "État d'import invalide"):
        super().__init__("import_state_invalid", message)


class ImportConflictError(ImportEngineError):
    def __init__(self, message: str = "Conflit d'import"):
        super().__init__("import_conflict", message)


class ImportPermissionError(ImportEngineError):
    def __init__(self, message: str = "Permission insuffisante"):
        super().__init__("import_permission_denied", message)


class ImportValidationError(ImportEngineError):
    def __init__(self, message: str = "Document non éligible à l'import"):
        super().__init__("import_validation_failed", message)


class ImportIdempotencyError(ImportEngineError):
    def __init__(self, message: str = "Import déjà effectué"):
        super().__init__("import_duplicate", message)


class ImportRollbackError(ImportEngineError):
    def __init__(self, message: str = "Rollback incomplet"):
        super().__init__("import_rollback_incomplete", message)
