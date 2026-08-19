"""Package classification documentaire déterministe."""

from app.document_processing.classification.taxonomy import DocumentTypeRegistry, get_document_type_registry

__all__ = ["DocumentTypeRegistry", "get_document_type_registry"]
