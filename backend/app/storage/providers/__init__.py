"""Providers de stockage."""

from app.storage.providers.disabled_storage_provider import DisabledStorageProvider
from app.storage.providers.local_storage_provider import LocalStorageProvider

__all__ = ["LocalStorageProvider", "DisabledStorageProvider"]
