"""Provider local — développement / tests."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from typing import Any, BinaryIO
from uuid import uuid4

from app.config import settings
from app.storage.storage_capabilities import LOCAL_CAPABILITIES, StorageProviderCapabilities
from app.storage.storage_exceptions import StorageNotFoundError, StorageProviderError, StorageValidationError
from app.storage.storage_provider import (
    DownloadReference,
    StorageObjectMeta,
    StorageProvider,
    StoredObjectRef,
)


class LocalStorageProvider(StorageProvider):
    name = "local"

    def __init__(self, root: Path | None = None) -> None:
        configured = root or Path(
            getattr(settings, "storage_local_root", None)
            or (Path(settings.storage_dir) / "elfis_objects")
        )
        self._root = configured.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def capabilities(self) -> StorageProviderCapabilities:
        return LOCAL_CAPABILITIES

    def _resolve(self, namespace: str, object_key: str) -> Path:
        ns = (namespace or "default").strip().replace("..", "")
        key = (object_key or "").strip().replace("\\", "/")
        if not key or ".." in key.split("/") or key.startswith("/"):
            raise StorageValidationError("invalid_object_key", "Clé objet invalide")
        path = (self._root / ns / key).resolve()
        try:
            path.relative_to(self._root)
        except ValueError as exc:
            raise StorageValidationError("path_traversal", "Accès hors racine refusé") from exc
        return path

    def resolve_path(self, namespace: str, object_key: str) -> Path:
        """Résolution interne contrôlée — ne pas exposer aux routes API."""
        return self._resolve(namespace, object_key)

    @property
    def root_path(self) -> Path:
        return self._root

    def list_temp_keys(self, *, older_than_seconds: int = 0) -> list[tuple[str, float]]:
        temp_root = (self._root / "_temp").resolve()
        try:
            temp_root.relative_to(self._root)
        except ValueError:
            return []
        if not temp_root.is_dir():
            return []
        now = time.time()
        out: list[tuple[str, float]] = []
        for p in temp_root.iterdir():
            if not p.is_file():
                continue
            age = now - p.stat().st_mtime
            if age >= older_than_seconds:
                out.append((p.name, age))
        return out

    def count_old_temps(self, *, older_than_seconds: int = 3600) -> int:
        return len(self.list_temp_keys(older_than_seconds=older_than_seconds))

    def disk_usage_ratio(self) -> tuple[int | None, int | None, float | None]:
        try:
            import shutil

            usage = shutil.disk_usage(self._root)
            used_ratio = 1.0 - (usage.free / usage.total) if usage.total else None
            return int(usage.free), int(usage.total), used_ratio
        except Exception:
            return None, None, None

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
        dest = self._resolve(namespace, object_key)
        if dest.is_file() and not overwrite:
            raise StorageProviderError("object_exists", "Objet déjà présent")
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".tmp_", dir=str(dest.parent))
        try:
            with os.fdopen(fd, "wb") as tmp:
                tmp.write(data)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_name, dest)
            try:
                os.chmod(dest, 0o644)
            except OSError:
                pass
        except StorageProviderError:
            raise
        except Exception as exc:
            try:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
            except OSError:
                pass
            raise StorageProviderError("put_failed", str(exc)[:200]) from exc
        return StoredObjectRef(
            provider=self.name,
            namespace=namespace,
            object_key=object_key,
            size_bytes=len(data),
            checksum_sha256=(metadata or {}).get("checksum_sha256"),
            metadata={"content_type": content_type} if content_type else {},
        )

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
        dest = self._resolve(namespace, object_key)
        if dest.is_file() and not overwrite:
            raise StorageProviderError("object_exists", "Objet déjà présent")
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".tmp_", dir=str(dest.parent))
        total = 0
        try:
            with os.fdopen(fd, "wb") as tmp:
                while True:
                    chunk = stream.read(65536)
                    if not chunk:
                        break
                    total += len(chunk)
                    tmp.write(chunk)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_name, dest)
        except Exception as exc:
            try:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
            except OSError:
                pass
            raise StorageProviderError("put_stream_failed", str(exc)[:200]) from exc
        return StoredObjectRef(
            provider=self.name,
            namespace=namespace,
            object_key=object_key,
            size_bytes=total,
            checksum_sha256=(metadata or {}).get("checksum_sha256"),
            metadata={"content_type": content_type} if content_type else {},
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
        src = self._resolve(source_namespace, source_object_key)
        dest = self._resolve(dest_namespace, dest_object_key)
        if not src.is_file():
            raise StorageNotFoundError("object_not_found", "Objet source introuvable")
        if dest.is_file() and not overwrite:
            raise StorageProviderError("object_exists", "Objet destination déjà présent")
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(str(src), str(dest))
        return StoredObjectRef(
            provider=self.name,
            namespace=dest_namespace,
            object_key=dest_object_key,
            size_bytes=dest.stat().st_size,
        )

    def get_object(self, *, namespace: str, object_key: str) -> bytes:
        path = self._resolve(namespace, object_key)
        if not path.is_file():
            raise StorageNotFoundError("object_not_found", "Objet introuvable")
        return path.read_bytes()

    def open_stream(self, *, namespace: str, object_key: str) -> BinaryIO:
        path = self._resolve(namespace, object_key)
        if not path.is_file():
            raise StorageNotFoundError("object_not_found", "Objet introuvable")
        return path.open("rb")

    def delete_object(self, *, namespace: str, object_key: str) -> bool:
        path = self._resolve(namespace, object_key)
        if not path.is_file():
            return False
        path.unlink()
        return True

    def object_exists(self, *, namespace: str, object_key: str) -> bool:
        try:
            return self._resolve(namespace, object_key).is_file()
        except StorageValidationError:
            return False

    def get_metadata(self, *, namespace: str, object_key: str) -> StorageObjectMeta:
        path = self._resolve(namespace, object_key)
        exists = path.is_file()
        size = path.stat().st_size if exists else 0
        return StorageObjectMeta(
            provider=self.name,
            namespace=namespace,
            object_key=object_key,
            size_bytes=size,
            exists=exists,
        )

    def generate_download_reference(
        self,
        *,
        namespace: str,
        object_key: str,
        expires_seconds: int = 300,
    ) -> DownloadReference:
        if not self.object_exists(namespace=namespace, object_key=object_key):
            raise StorageNotFoundError("object_not_found", "Objet introuvable")
        return DownloadReference(kind="stream", object_key=object_key)

    def health_check(self) -> dict[str, Any]:
        started = time.perf_counter()
        probe_key = f"_health/{uuid4().hex}.probe"
        ns = "_system"
        try:
            self.put_object(namespace=ns, object_key=probe_key, data=b"elfis-storage-probe")
            with self.open_stream(namespace=ns, object_key=probe_key) as fh:
                data = fh.read()
            ok = data == b"elfis-storage-probe"
            self.delete_object(namespace=ns, object_key=probe_key)
            try:
                probe_dir = self._resolve(ns, "_health")
                if probe_dir.is_dir() and not any(probe_dir.iterdir()):
                    probe_dir.rmdir()
            except Exception:
                pass
            free, total, used_ratio = self.disk_usage_ratio()
            old_temps = self.count_old_temps(older_than_seconds=3600)
            latency_ms = int((time.perf_counter() - started) * 1000)
            return {
                "provider": self.name,
                "status": "healthy" if ok else "unhealthy",
                "root_accessible": True,
                "probe_ok": ok,
                "stream_ok": ok,
                "latency_ms": latency_ms,
                "free_bytes": free,
                "total_bytes": total,
                "used_ratio": used_ratio,
                "old_temp_count": old_temps,
            }
        except Exception as exc:
            return {
                "provider": self.name,
                "status": "unhealthy",
                "root_accessible": self._root.exists(),
                "probe_ok": False,
                "error": type(exc).__name__,
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }


def new_object_key(*, extension: str = "") -> str:
    """Clé physique UUID — jamais le nom utilisateur."""
    ext = extension if extension.startswith(".") or not extension else f".{extension}"
    return f"{uuid4().hex}{ext.lower()}"
