"""Exceptions Document Intelligence."""

from __future__ import annotations


class DocumentIntelligenceError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class DocumentValidationError(DocumentIntelligenceError):
    def __init__(self, message: str):
        super().__init__("validation_error", message)


class DocumentNotFoundError(DocumentIntelligenceError):
    def __init__(self, message: str = "Document introuvable"):
        super().__init__("not_found", message)


class DocumentDisabledError(DocumentIntelligenceError):
    def __init__(self, message: str = "Document Intelligence désactivé"):
        super().__init__("disabled", message)


class DocumentExtractionError(DocumentIntelligenceError):
    def __init__(self, message: str):
        super().__init__("extraction_error", message)


class DocumentOCRUnavailableError(DocumentIntelligenceError):
    def __init__(self, message: str = "OCR non configuré"):
        super().__init__("ocr_unavailable", message)
