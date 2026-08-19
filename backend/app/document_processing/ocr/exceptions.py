"""Exceptions OCR."""

from __future__ import annotations


class OCRError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


class OCRValidationError(OCRError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, retryable=False)


class OCRAccessDeniedError(OCRError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, retryable=False)


class OCRNotFoundError(OCRError):
    def __init__(self, code: str = "not_found", message: str = "Introuvable") -> None:
        super().__init__(code, message, retryable=False)


class OCRProviderError(OCRError):
    pass


class OCRRetryableError(OCRProviderError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, retryable=True)


class OCRPermanentError(OCRProviderError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, retryable=False)
