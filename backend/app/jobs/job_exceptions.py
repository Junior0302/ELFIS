"""Exceptions Job Queue."""

from __future__ import annotations


class JobError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class JobValidationError(JobError):
    def __init__(self, message: str):
        super().__init__("validation_error", message)


class JobNotFoundError(JobError):
    def __init__(self, message: str = "Job introuvable"):
        super().__init__("not_found", message)


class JobDuplicateError(JobError):
    def __init__(self, message: str, *, existing_job_id: str | None = None):
        self.existing_job_id = existing_job_id
        super().__init__("duplicate", message)


class JobUnknownTypeError(JobError):
    def __init__(self, job_name: str):
        super().__init__("unknown_job", f"Type de job inconnu: {job_name}")


class RetryableJobError(Exception):
    """Erreur temporaire — le worker planifie un retry."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class PermanentJobError(Exception):
    """Erreur permanente — pas de retry automatique."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
