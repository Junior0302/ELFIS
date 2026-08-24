"""Provider désactivé — refus explicite de toute opération."""

from __future__ import annotations

from typing import Any, BinaryIO

from app.storage.storage_capabilities import DISABLED_CAPABILITIES, StorageProviderCapabilities
from app.storage.storage_exceptions import StorageDisabledError
from app.storage.storage_provider import StorageObjectMeta, StorageProvider, StoredObjectRef


class DisabledStorageProvider(StorageProvider):
    name = "disabled"

    @property
    def capabilities(self) -> StorageProviderCapabilities:
        return DISABLED_CAPABILITIES

    def put_object(self, **kwargs: Any) -> StoredObjectRef:
        raise StorageDisabledError("storage_disabled", "Stockage désactivé")

    def get_object(self, **kwargs: Any) -> bytes:
        raise StorageDisabledError("storage_disabled", "Stockage désactivé")

    def open_stream(self, **kwargs: Any) -> BinaryIO:
        raise StorageDisabledError("storage_disabled", "Stockage désactivé")

    def delete_object(self, **kwargs: Any) -> bool:
        raise StorageDisabledError("storage_disabled", "Stockage désactivé")

    def object_exists(self, **kwargs: Any) -> bool:
        return False

    def get_metadata(self, **kwargs: Any) -> StorageObjectMeta:
        raise StorageDisabledError("storage_disabled", "Stockage désactivé")

    def health_check(self) -> dict[str, Any]:
        return {"provider": self.name, "status": "disabled", "probe_ok": False}
