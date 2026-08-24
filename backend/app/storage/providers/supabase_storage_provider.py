"""Supabase Storage provider — RC2.4 étape 4 (bucket privé, proxy ELFIS par défaut)."""

from __future__ import annotations

import io
import logging
import time
from typing import Any, BinaryIO
from uuid import uuid4

import httpx

from app.config import settings
from app.storage.storage_capabilities import SUPABASE_CAPABILITIES, StorageProviderCapabilities
from app.storage.storage_exceptions import (
    StorageNotFoundError,
    StorageProviderError,
    StorageValidationError,
)
from app.storage.storage_provider import (
    DownloadReference,
    StorageObjectMeta,
    StorageProvider,
    StoredObjectRef,
)
from app.storage.providers.supabase_http_client import (
    SupabaseStorageClientFactory,
    SupabaseStorageHttpClient,
)

logger = logging.getLogger(__name__)


class _StreamingResponseBinaryIO(io.RawIOBase):
    """File-like autour d'une réponse httpx streamée."""

    def __init__(self, response: httpx.Response) -> None:
        super().__init__()
        self._response = response
        self._iter = response.iter_bytes(65536)
        self._buf = b""
        self._closed = False

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:  # type: ignore[override]
        if self._closed:
            return b""
        if size is None or size < 0:
            parts = [self._buf]
            self._buf = b""
            for chunk in self._iter:
                parts.append(chunk)
            return b"".join(parts)
        while len(self._buf) < size:
            try:
                chunk = next(self._iter)
            except StopIteration:
                break
            self._buf += chunk
        out, self._buf = self._buf[:size], self._buf[size:]
        return out

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            try:
                self._response.close()
            except Exception:
                pass
        super().close()


def build_document_object_key(
    *,
    organization_id: int | None,
    storage_object_id: str | None = None,
    extension: str = "",
) -> str:
    """Clé stable sans PII : documents/{org}/{yyyy}/{mm}/{uuid}[.ext]."""
    from datetime import datetime

    oid = storage_object_id or uuid4().hex
    # strip dashes if uuid
    oid = oid.replace("-", "")
    ext = extension if extension.startswith(".") or not extension else f".{extension}"
    now = datetime.utcnow()
    org = int(organization_id or 0)
    return f"documents/{org}/{now.year:04d}/{now.month:02d}/{oid}{ext.lower()}"


class SupabaseStorageProvider(StorageProvider):
    name = "supabase"

    def __init__(
        self,
        *,
        client: SupabaseStorageHttpClient | None = None,
        bucket: str | None = None,
    ) -> None:
        self._client = client or SupabaseStorageClientFactory.build()
        self._bucket = (
            bucket
            or getattr(settings, "supabase_storage_bucket", None)
            or "elfis-documents"
        ).strip()
        if not self._client.configured:
            raise StorageProviderError(
                "supabase_not_configured",
                "Configuration Supabase Storage incomplète",
            )
        if not self._bucket:
            raise StorageProviderError(
                "supabase_bucket_missing",
                "Bucket Supabase Storage manquant",
            )

    @property
    def capabilities(self) -> StorageProviderCapabilities:
        return SUPABASE_CAPABILITIES

    def _path(self, namespace: str, object_key: str) -> str:
        ns = (namespace or "documents").strip().strip("/").replace("..", "")
        key = (object_key or "").strip().replace("\\", "/").lstrip("/")
        if not key or ".." in key.split("/"):
            raise StorageValidationError("invalid_object_key", "Clé objet invalide")
        # Si object_key contient déjà le namespace (migration), ne pas doubler
        if key.startswith(f"{ns}/"):
            return key
        return f"{ns}/{key}"

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
        path = self._path(namespace, object_key)
        if not overwrite and self.object_exists(namespace=namespace, object_key=object_key):
            raise StorageProviderError("object_exists", "Objet déjà présent")
        try:
            self._client.upload_bytes(
                bucket=self._bucket,
                path=path,
                content=data,
                content_type=content_type or "application/octet-stream",
                upsert=overwrite,
            )
        except RuntimeError as exc:
            code = str(exc)
            if "401" in code or "403" in code:
                raise StorageProviderError("auth_failed", "Authentification storage refusée") from exc
            if "timeout" in code.lower():
                raise StorageProviderError("timeout", "Timeout upload distant") from exc
            raise StorageProviderError("put_failed", "Échec upload distant") from exc
        except httpx.TimeoutException as exc:
            raise StorageProviderError("timeout", "Timeout upload distant") from exc
        except httpx.NetworkError as exc:
            raise StorageProviderError("network_error", "Réseau storage indisponible") from exc
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
        path = self._path(namespace, object_key)
        if not overwrite and self.object_exists(namespace=namespace, object_key=object_key):
            raise StorageProviderError("object_exists", "Objet déjà présent")
        try:
            self._client.upload_fileobj(
                bucket=self._bucket,
                path=path,
                fileobj=stream,
                content_type=content_type or "application/octet-stream",
                upsert=overwrite,
            )
        except RuntimeError as exc:
            code = str(exc)
            if "401" in code or "403" in code:
                raise StorageProviderError("auth_failed", "Authentification storage refusée") from exc
            raise StorageProviderError("put_failed", "Échec upload distant") from exc
        except httpx.TimeoutException as exc:
            raise StorageProviderError("timeout", "Timeout upload distant") from exc
        except httpx.NetworkError as exc:
            raise StorageProviderError("network_error", "Réseau storage indisponible") from exc
        return StoredObjectRef(
            provider=self.name,
            namespace=namespace,
            object_key=object_key,
            size_bytes=int(size_bytes or 0),
            checksum_sha256=(metadata or {}).get("checksum_sha256"),
            metadata={"content_type": content_type} if content_type else {},
        )

    def get_object(self, *, namespace: str, object_key: str) -> bytes:
        path = self._path(namespace, object_key)
        try:
            return self._client.download_bytes(bucket=self._bucket, path=path)
        except RuntimeError as exc:
            if "404" in str(exc):
                raise StorageNotFoundError("object_not_found", "Objet introuvable") from exc
            raise StorageProviderError("get_failed", "Échec lecture distante") from exc

    def open_stream(self, *, namespace: str, object_key: str) -> BinaryIO:
        path = self._path(namespace, object_key)
        try:
            response = self._client.download_stream(bucket=self._bucket, path=path)
        except RuntimeError as exc:
            if "404" in str(exc):
                raise StorageNotFoundError("object_not_found", "Objet introuvable") from exc
            raise StorageProviderError("stream_failed", "Échec stream distant") from exc
        return _StreamingResponseBinaryIO(response)  # type: ignore[return-value]

    def delete_object(self, *, namespace: str, object_key: str) -> bool:
        path = self._path(namespace, object_key)
        try:
            status = self._client.delete_object(bucket=self._bucket, path=path)
        except Exception as exc:
            raise StorageProviderError("delete_failed", "Échec suppression distante") from exc
        # 404 / succès : idempotent
        if status in {200, 204} or status < 400:
            return True
        if status == 404:
            return False
        raise StorageProviderError("delete_failed", f"Échec suppression distante ({status})")

    def object_exists(self, *, namespace: str, object_key: str) -> bool:
        try:
            meta = self.get_metadata(namespace=namespace, object_key=object_key)
            return bool(meta.exists)
        except Exception:
            return False

    def get_metadata(self, *, namespace: str, object_key: str) -> StorageObjectMeta:
        path = self._path(namespace, object_key)
        info = self._client.object_info(bucket=self._bucket, path=path)
        if not info:
            # fallback : tenter stream HEAD via download 404
            try:
                data = self._client.download_bytes(bucket=self._bucket, path=path)
                return StorageObjectMeta(
                    provider=self.name,
                    namespace=namespace,
                    object_key=object_key,
                    size_bytes=len(data),
                    exists=True,
                )
            except RuntimeError as exc:
                if "404" in str(exc):
                    return StorageObjectMeta(
                        provider=self.name,
                        namespace=namespace,
                        object_key=object_key,
                        size_bytes=0,
                        exists=False,
                    )
                raise StorageProviderError("metadata_failed", "Métadonnées distantes indisponibles") from exc
        size = 0
        meta = info.get("metadata") if isinstance(info.get("metadata"), dict) else {}
        try:
            size = int(meta.get("size") or info.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        return StorageObjectMeta(
            provider=self.name,
            namespace=namespace,
            object_key=object_key,
            size_bytes=size,
            exists=True,
            content_type=meta.get("mimetype") if isinstance(meta, dict) else None,
        )

    def generate_download_reference(
        self,
        *,
        namespace: str,
        object_key: str,
        expires_seconds: int = 300,
    ) -> DownloadReference:
        """Préparé — le défaut API reste le proxy ELFIS (kind=stream)."""
        ttl = int(
            expires_seconds
            or getattr(settings, "supabase_storage_download_url_ttl_seconds", 300)
            or 300
        )
        # Par défaut on expose stream ; signed URL uniquement si demandé explicitement plus tard
        return DownloadReference(kind="stream", object_key=object_key, expires_at=None)

    def create_signed_download_url(
        self,
        *,
        namespace: str,
        object_key: str,
        expires_seconds: int | None = None,
    ) -> DownloadReference:
        path = self._path(namespace, object_key)
        ttl = int(
            expires_seconds
            or getattr(settings, "supabase_storage_download_url_ttl_seconds", 300)
            or 300
        )
        try:
            url = self._client.create_signed_url(
                bucket=self._bucket, path=path, expires_in=ttl
            )
        except Exception as exc:
            raise StorageProviderError("sign_failed", "URL signée indisponible") from exc
        return DownloadReference(kind="signed_url", url=url, expires_at=None)

    def list_object_keys(self, *, namespace: str, prefix: str = "", limit: int = 100) -> list[str]:
        ns = (namespace or "").strip().strip("/")
        full_prefix = f"{ns}/{prefix}".strip("/") if prefix else ns
        items = self._client.list_prefix(bucket=self._bucket, prefix=full_prefix, limit=limit)
        keys: list[str] = []
        for item in items:
            if isinstance(item, dict) and item.get("name"):
                name = str(item["name"])
                # retour relatif au namespace si possible
                if ns and name.startswith(ns + "/"):
                    keys.append(name[len(ns) + 1 :])
                else:
                    keys.append(name)
        return keys

    def health_check(self) -> dict[str, Any]:
        started = time.perf_counter()
        probe_key = f"{uuid4().hex}.probe"
        ns = getattr(settings, "supabase_storage_temp_namespace", None) or "temp"
        # namespace dédié health
        ns = "health-probes"
        try:
            self.put_object(namespace=ns, object_key=probe_key, data=b"elfis-sb-probe", overwrite=True)
            with self.open_stream(namespace=ns, object_key=probe_key) as fh:
                data = fh.read()
            ok = data == b"elfis-sb-probe"
            deleted = self.delete_object(namespace=ns, object_key=probe_key)
            latency_ms = int((time.perf_counter() - started) * 1000)
            status = "healthy"
            if not ok:
                status = "unhealthy"
            elif not deleted:
                status = "degraded"
            elif latency_ms > 3000:
                status = "degraded"
            return {
                "provider": self.name,
                "status": status,
                "probe_ok": ok,
                "stream_ok": ok,
                "delete_ok": deleted,
                "latency_ms": latency_ms,
                "bucket_configured": bool(self._bucket),
            }
        except StorageProviderError as exc:
            return {
                "provider": self.name,
                "status": "unhealthy",
                "probe_ok": False,
                "error": exc.code,
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
        except Exception as exc:
            return {
                "provider": self.name,
                "status": "unhealthy",
                "probe_ok": False,
                "error": type(exc).__name__,
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
