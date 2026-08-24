"""Contexte Storage — provider + options (tests injectables)."""

from __future__ import annotations

from dataclasses import dataclass

from app.storage.storage_provider import StorageProvider
from app.storage.storage_registry import get_default_storage_provider


@dataclass
class StorageContext:
    provider: StorageProvider
    namespace: str = "default"


def default_storage_context(*, namespace: str = "default") -> StorageContext:
    return StorageContext(provider=get_default_storage_provider(), namespace=namespace)
