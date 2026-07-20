"""Tâches IA documentaires."""

from app.ai.tasks.document_classification import DocumentClassifyTask
from app.ai.tasks.document_extraction import DocumentExtractInvoiceTask
from app.ai.tasks.document_quality import DocumentQualityCheckTask

__all__ = [
    "DocumentClassifyTask",
    "DocumentExtractInvoiceTask",
    "DocumentQualityCheckTask",
]
