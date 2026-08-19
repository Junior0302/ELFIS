"""Abstraction StorageProvider — Document Intake (pas d'appel FS direct métier)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoragePutResult:
    provider: str
    location: str  # logical root label
    object_key: str  # relative key only
    size_bytes: int
    version: str | None = None
    metadata: dict | None = None


@dataclass(frozen=True)
class StorageObjectMeta:
    provider: str
    location: str
    object_key: str
    size_bytes: int
    exists: bool
    version: str | None = None
    metadata: dict | None = None


class StorageProvider(ABC):
    name: str

    @abstractmethod
    def put(
        self,
        *,
        organization_id: int,
        content: bytes,
        extension: str,
        namespace: str = "temp",
        object_key: str | None = None,
    ) -> StoragePutResult: ...

    @abstractmethod
    def get_stream(self, *, organization_id: int, object_key: str) -> BinaryIO: ...

    @abstractmethod
    def delete(self, *, organization_id: int, object_key: str) -> None: ...

    @abstractmethod
    def exists(self, *, organization_id: int, object_key: str) -> bool: ...

    @abstractmethod
    def move(
        self,
        *,
        organization_id: int,
        from_key: str,
        to_key: str,
    ) -> StoragePutResult: ...

    @abstractmethod
    def copy(
        self,
        *,
        organization_id: int,
        from_key: str,
        to_key: str,
    ) -> StoragePutResult: ...

    @abstractmethod
    def get_metadata(self, *, organization_id: int, object_key: str) -> StorageObjectMeta: ...

    @abstractmethod
    def generate_internal_location(self, *, organization_id: int, namespace: str = "temp") -> str: ...

    @abstractmethod
    def health_check(self) -> dict: ...


class LocalStorageProvider(StorageProvider):
    name = "local"

    def __init__(self, root: Path | None = None) -> None:
        base = root or Path(getattr(settings, "storage_dir", None) or "storage")
        self._root = base / "document_intake"
        self._root.mkdir(parents=True, exist_ok=True)

    def _org(self, organization_id: int) -> Path:
        d = self._root / f"org_{organization_id}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _safe_key(self, object_key: str) -> str:
        safe = object_key.replace("\\", "/").lstrip("/")
        parts = [p for p in safe.split("/") if p and p not in {".", ".."}]
        if not parts:
            raise ValueError("invalid object key")
        return "/".join(parts)

    def _path(self, organization_id: int, object_key: str) -> Path:
        return self._org(organization_id) / self._safe_key(object_key)

    def generate_internal_location(self, *, organization_id: int, namespace: str = "temp") -> str:
        return f"local://document_intake/org_{organization_id}/{namespace}"

    def put(
        self,
        *,
        organization_id: int,
        content: bytes,
        extension: str,
        namespace: str = "temp",
        object_key: str | None = None,
    ) -> StoragePutResult:
        ns = namespace if namespace in {"temp", "quarantine"} else "temp"
        ext = extension if extension.startswith(".") else (f".{extension}" if extension else "")
        key = object_key or f"{ns}/{uuid4().hex}{ext}"
        key = self._safe_key(key)
        path = self._path(organization_id, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        try:
            path.chmod(0o600)
        except OSError:
            pass
        return StoragePutResult(
            provider=self.name,
            location=self.generate_internal_location(organization_id=organization_id, namespace=ns),
            object_key=key,
            size_bytes=len(content),
            version="1",
            metadata={"schema_version": 1},
        )

    def get_stream(self, *, organization_id: int, object_key: str) -> BinaryIO:
        return self._path(organization_id, object_key).open("rb")

    def delete(self, *, organization_id: int, object_key: str) -> None:
        p = self._path(organization_id, object_key)
        if p.is_file():
            p.unlink()

    def exists(self, *, organization_id: int, object_key: str) -> bool:
        return self._path(organization_id, object_key).is_file()

    def move(
        self, *, organization_id: int, from_key: str, to_key: str
    ) -> StoragePutResult:
        src = self._path(organization_id, from_key)
        dst = self._path(organization_id, to_key)
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.replace(dst)
        return StoragePutResult(
            provider=self.name,
            location=self.generate_internal_location(organization_id=organization_id),
            object_key=self._safe_key(to_key),
            size_bytes=dst.stat().st_size,
            version="1",
        )

    def copy(
        self, *, organization_id: int, from_key: str, to_key: str
    ) -> StoragePutResult:
        data = self._path(organization_id, from_key).read_bytes()
        return self.put(
            organization_id=organization_id,
            content=data,
            extension="",
            object_key=to_key,
        )

    def get_metadata(self, *, organization_id: int, object_key: str) -> StorageObjectMeta:
        p = self._path(organization_id, object_key)
        exists = p.is_file()
        return StorageObjectMeta(
            provider=self.name,
            location=self.generate_internal_location(organization_id=organization_id),
            object_key=self._safe_key(object_key),
            size_bytes=p.stat().st_size if exists else 0,
            exists=exists,
            version="1",
        )

    def health_check(self) -> dict:
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            probe = self._root / ".health"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return {"provider": self.name, "ok": True, "root": "document_intake"}
        except Exception as exc:
            return {"provider": self.name, "ok": False, "error": type(exc).__name__}


_FUTURE_PROVIDERS = frozenset({"s3", "azure_blob", "gcs", "minio"})


def get_storage_provider(name: str | None = None) -> StorageProvider:
    """Factory — sélection via config uniquement."""
    configured = (
        name
        or getattr(settings, "document_intake_storage_provider", None)
        or "local"
    )
    key = str(configured).strip().lower()
    if key == "local":
        return LocalStorageProvider()
    if key in _FUTURE_PROVIDERS:
        raise ValueError(f"Storage provider '{key}' non implémenté (Sprint futur)")
    raise ValueError(f"Storage provider inconnu: {key}")


# Compat Sprint 2 — wrappers déléguant au provider local
def store_bytes(
    *,
    organization_id: int,
    content: bytes,
    extension: str,
    quarantined: bool = False,
) -> tuple[str, Path]:
    provider = get_storage_provider("local")
    ns = "quarantine" if quarantined else "temp"
    result = provider.put(
        organization_id=organization_id,
        content=content,
        extension=extension,
        namespace=ns,
    )
    # Path résolu uniquement pour tests internes — non exposé API
    local = LocalStorageProvider()
    path = local._path(organization_id, result.object_key)  # noqa: SLF001
    return result.object_key, path


def resolve_path(organization_id: int, storage_key: str) -> Path:
    return LocalStorageProvider()._path(organization_id, storage_key)  # noqa: SLF001


def delete_stored(organization_id: int, storage_key: str) -> None:
    get_storage_provider("local").delete(organization_id=organization_id, object_key=storage_key)
