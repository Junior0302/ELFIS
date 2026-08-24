"""ELFIS Storage Abstraction & Document Registry (RC2.4 étape 1)."""

from __future__ import annotations

from app.storage.document_registry_service import DocumentRegistryService
from app.storage.storage_registry import build_storage_provider, get_default_storage_provider
from app.storage.storage_service import StorageService

__all__ = [
    "DocumentRegistryService",
    "StorageService",
    "build_storage_provider",
    "get_default_storage_provider",
]
