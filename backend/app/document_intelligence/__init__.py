"""ELFIS Document Intelligence V1."""

from __future__ import annotations

from app.document_intelligence.document_registry import bootstrap_extractors
from app.document_intelligence.document_schemas import (
    DocumentExtractionRequest,
    DocumentExtractionResult,
)
from app.document_intelligence.document_service import DocumentIntelligenceService

__all__ = [
    "DocumentExtractionRequest",
    "DocumentExtractionResult",
    "DocumentIntelligenceService",
    "bootstrap_extractors",
]
