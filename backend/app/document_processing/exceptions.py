"""Exceptions Document Processing."""

from __future__ import annotations


class DocumentProcessingError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        self.message = message or code
        super().__init__(self.message)


class ProcessingValidationError(DocumentProcessingError):
    pass


class ProcessingNotFoundError(DocumentProcessingError):
    pass


class ProcessingAccessDeniedError(DocumentProcessingError):
    pass


class ProcessingRetryableError(DocumentProcessingError):
    """Erreur temporaire — retry selon politique."""

    def __init__(self, code: str, message: str = "", *, retryable: bool = True) -> None:
        super().__init__(code, message)
        self.retryable = retryable


class ProcessingPermanentError(DocumentProcessingError):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(code, message)
        self.retryable = False


class ProcessingCancelledError(DocumentProcessingError):
    def __init__(self, message: str = "cancelled") -> None:
        super().__init__("cancelled", message)


class ProcessingTimeoutError(DocumentProcessingError):
    def __init__(self, code: str = "timeout", message: str = "timeout") -> None:
        super().__init__(code, message)
        self.retryable = True
