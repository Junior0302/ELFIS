"""Contrat abstrait StorageProvider + capacités."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, BinaryIO, Iterator

from app.storage.storage_capabilities import StorageProviderCapabilities


@dataclass
class StoredObjectRef:
    provider: str
    namespace: str
    object_key: str
    size_bytes: int = 0
    checksum_sha256: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StorageObjectMeta:
    provider: str
    namespace: str
    object_key: str
    size_bytes: int
    exists: bool
    checksum_sha256: str | None = None
    content_type: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class DownloadReference:
    """Référence de téléchargement — jamais un chemin physique exposé."""

    kind: str  # stream | signed_url
    expires_at: str | None = None
    # signed_url optionnelle — ne pas logger / persister
    url: str | None = None
    object_key: str | None = None


class StorageProvider(ABC):
    name: str

    @property
    def capabilities(self) -> StorageProviderCapabilities:
        return StorageProviderCapabilities()

    @abstractmethod
    def put_object(
        self,
        *,
        namespace: str,
        object_key: str,
        data: bytes,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> StoredObjectRef:
        ...

    def put_stream(
        self,
        *,
        namespace: str,
        object_key: str,
        stream: BinaryIO,
        size_bytes: int | None = None,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> StoredObjectRef:
        """Défaut : lit par chunks puis put_object (sous-classes distantes override)."""
        chunks: list[bytes] = []
        total = 0
        while True:
            part = stream.read(65536)
            if not part:
                break
            chunks.append(part)
            total += len(part)
            if size_bytes is not None and total > size_bytes:
                raise ValueError("stream_larger_than_declared")
        data = b"".join(chunks)
        return self.put_object(
            namespace=namespace,
            object_key=object_key,
            data=data,
            content_type=content_type,
            metadata=metadata,
            overwrite=overwrite,
        )

    @abstractmethod
    def get_object(self, *, namespace: str, object_key: str) -> bytes:
        ...

    @abstractmethod
    def open_stream(self, *, namespace: str, object_key: str) -> BinaryIO:
        ...

    @abstractmethod
    def delete_object(self, *, namespace: str, object_key: str) -> bool:
        ...

    @abstractmethod
    def object_exists(self, *, namespace: str, object_key: str) -> bool:
        ...

    @abstractmethod
    def get_metadata(self, *, namespace: str, object_key: str) -> StorageObjectMeta:
        ...

    def copy_object(
        self,
        *,
        source_namespace: str,
        source_object_key: str,
        dest_namespace: str,
        dest_object_key: str,
        overwrite: bool = False,
    ) -> StoredObjectRef:
        data = self.get_object(namespace=source_namespace, object_key=source_object_key)
        return self.put_object(
            namespace=dest_namespace,
            object_key=dest_object_key,
            data=data,
            overwrite=overwrite,
        )

    def move_object(
        self,
        *,
        source_namespace: str,
        source_object_key: str,
        dest_namespace: str,
        dest_object_key: str,
        overwrite: bool = False,
    ) -> StoredObjectRef:
        """Par défaut : copy + delete source (non atomique)."""
        ref = self.copy_object(
            source_namespace=source_namespace,
            source_object_key=source_object_key,
            dest_namespace=dest_namespace,
            dest_object_key=dest_object_key,
            overwrite=overwrite,
        )
        self.delete_object(namespace=source_namespace, object_key=source_object_key)
        return ref

    def generate_download_reference(
        self,
        *,
        namespace: str,
        object_key: str,
        expires_seconds: int = 300,
    ) -> DownloadReference:
        return DownloadReference(kind="stream", object_key=object_key)

    def health_check(self) -> dict[str, Any]:
        return {"provider": self.name, "status": "unknown"}

    def iter_chunks(
        self,
        *,
        namespace: str,
        object_key: str,
        chunk_size: int = 65536,
    ) -> Iterator[bytes]:
        with self.open_stream(namespace=namespace, object_key=object_key) as fh:
            while True:
                chunk = fh.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    def list_object_keys(self, *, namespace: str, prefix: str = "", limit: int = 100) -> list[str]:
        """Optionnel — listing préfixe (orphelins). Défaut vide."""
        return []
