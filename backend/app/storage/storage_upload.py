"""Upload streaming — lecture par chunks, temp local, promotion locale ou remote put."""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, BinaryIO
from uuid import uuid4

from app.config import settings
from app.storage.providers.local_storage_provider import LocalStorageProvider, new_object_key
from app.storage.storage_exceptions import StorageError, StorageProviderError, StorageValidationError
from app.storage.storage_provider import StorageProvider
from app.storage.storage_reject_codes import StorageRejectCode
from app.storage.storage_security import validate_filename_only, validate_upload_head_and_meta
from app.storage.storage_security import FileValidationResult

logger = logging.getLogger(__name__)

TEMP_NAMESPACE = "_temp"


@dataclass
class StreamedUploadResult:
    namespace: str
    object_key: str
    size_bytes: int
    checksum_sha256: str
    head: bytes
    validation: FileValidationResult
    temp_cleaned: bool = True
    provider: str = "local"


@dataclass
class _TempWrite:
    namespace: str
    object_key: str
    path: Path
    fh: BinaryIO
    hasher: Any = field(default_factory=hashlib.sha256)
    size: int = 0
    head: bytes = b""
    is_os_temp: bool = False


class StreamingUploadPipeline:
    """
    Cycle de vie :
    1. validation nom
    2. écriture temporaire sécurisée (FS provider local OU tempfile OS pour distant)
    3. chunks → taille + sha256 + head
    4. validation sécurité finale
    5. promotion :
       - local : atomic move vers namespace définitif
       - distant : put_stream vers clé définitive puis suppression temp OS
    6. suppression temp

    Flux distant documenté :
    streaming client → temporaire local OS → provider distant.
    """

    def __init__(self, provider: StorageProvider) -> None:
        self._provider = provider
        self._chunk = int(
            getattr(settings, "storage_upload_chunk_size_bytes", 65_536) or 65_536
        )
        self._max = int(
            getattr(settings, "storage_max_file_size_bytes", 15 * 1024 * 1024) or 15 * 1024 * 1024
        )
        self._temp: _TempWrite | None = None

    async def consume_upload_file(
        self,
        *,
        filename: str,
        declared_mime: str | None,
        chunk_iterator: AsyncIterator[bytes],
        organization_id: int | None = None,
    ) -> StreamedUploadResult:
        validate_filename_only(filename)
        self._open_temp(filename)
        assert self._temp is not None
        try:
            async for chunk in chunk_iterator:
                if not chunk:
                    continue
                self._write_chunk(chunk)
            return self._finalize(
                filename=filename,
                declared_mime=declared_mime,
                organization_id=organization_id,
            )
        except Exception:
            self._abort_temp()
            raise

    def consume_sync_chunks(
        self,
        *,
        filename: str,
        declared_mime: str | None,
        chunks: list[bytes] | tuple[bytes, ...],
        organization_id: int | None = None,
    ) -> StreamedUploadResult:
        validate_filename_only(filename)
        self._open_temp(filename)
        try:
            for chunk in chunks:
                if chunk:
                    self._write_chunk(chunk)
            return self._finalize(
                filename=filename,
                declared_mime=declared_mime,
                organization_id=organization_id,
            )
        except Exception:
            self._abort_temp()
            raise

    def _open_temp(self, filename: str) -> None:
        validate_filename_only(filename)
        temp_key = f"{uuid4().hex}.part"
        caps = getattr(self._provider, "capabilities", None)
        prefers_os = bool(caps and getattr(caps, "prefers_local_temp_then_remote_put", False))

        if isinstance(self._provider, LocalStorageProvider) and not prefers_os:
            path = self._provider.resolve_path(TEMP_NAMESPACE, temp_key)
            path.parent.mkdir(parents=True, exist_ok=True)
            fh = path.open("wb")
            self._temp = _TempWrite(
                namespace=TEMP_NAMESPACE,
                object_key=temp_key,
                path=path,
                fh=fh,
                is_os_temp=False,
            )
            return

        # Distant (ou fallback) : tempfile OS hors racine provider
        fd, tmp_name = tempfile.mkstemp(prefix="elfis_up_", suffix=".part")
        path = Path(tmp_name)
        fh = os.fdopen(fd, "wb")
        self._temp = _TempWrite(
            namespace="os_temp",
            object_key=temp_key,
            path=path,
            fh=fh,
            is_os_temp=True,
        )

    def _write_chunk(self, chunk: bytes) -> None:
        assert self._temp is not None
        new_size = self._temp.size + len(chunk)
        if new_size > self._max:
            raise StorageValidationError(
                StorageRejectCode.FILE_TOO_LARGE.value,
                f"Fichier trop volumineux (max {self._max} octets)",
            )
        if len(self._temp.head) < 64:
            need = 64 - len(self._temp.head)
            self._temp.head += chunk[:need]
        self._temp.hasher.update(chunk)
        self._temp.fh.write(chunk)
        self._temp.size = new_size

    def _finalize(
        self,
        *,
        filename: str,
        declared_mime: str | None,
        organization_id: int | None = None,
    ) -> StreamedUploadResult:
        assert self._temp is not None
        try:
            self._temp.fh.flush()
            try:
                os.fsync(self._temp.fh.fileno())
            except OSError:
                pass
        finally:
            self._temp.fh.close()

        if self._temp.size <= 0:
            self._abort_temp(already_closed=True)
            raise StorageValidationError(StorageRejectCode.EMPTY_FILE.value, "Fichier vide refusé")

        checksum = self._temp.hasher.hexdigest()
        head = self._temp.head
        size = self._temp.size
        validation = validate_upload_head_and_meta(
            filename=filename,
            head=head,
            size_bytes=size,
            declared_mime=declared_mime,
            checksum_sha256=checksum,
        )

        final_ns = self._final_namespace(validation.quarantined)
        final_key = new_object_key(extension=validation.extension)
        # Pour Supabase : clés structurées documents/{org}/yyyy/mm/uuid
        if self._provider.name == "supabase":
            from app.storage.providers.supabase_storage_provider import build_document_object_key

            final_key = build_document_object_key(
                organization_id=organization_id,
                extension=validation.extension,
            )
            # namespace = documents|quarantine|temp — object_key déjà préfixé documents/...
            # On stocke object_key relatif sans doubler le namespace dans le path provider
            if final_key.startswith("documents/"):
                final_key = final_key[len("documents/") :]

        temp_path = self._temp.path
        try:
            if isinstance(self._provider, LocalStorageProvider) and not self._temp.is_os_temp:
                self._promote_local(temp_path, final_ns, final_key)
            else:
                self._promote_remote(temp_path, final_ns, final_key, validation=validation, checksum=checksum)
        except Exception:
            self._abort_temp(already_closed=True)
            raise

        # remote : supprimer temp OS après succès
        if self._temp and self._temp.is_os_temp:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                logger.debug("os_temp_cleanup_failed", exc_info=True)
        self._temp = None
        return StreamedUploadResult(
            namespace=final_ns,
            object_key=final_key,
            size_bytes=validation.size_bytes,
            checksum_sha256=checksum,
            head=head,
            validation=validation,
            provider=self._provider.name,
        )

    def _final_namespace(self, quarantined: bool) -> str:
        if quarantined:
            return (
                getattr(settings, "storage_quarantine_namespace", None)
                or getattr(settings, "supabase_storage_quarantine_namespace", None)
                or "quarantine"
            ).strip() or "quarantine"
        if self._provider.name == "supabase":
            return (
                getattr(settings, "supabase_storage_document_namespace", None) or "documents"
            ).strip() or "documents"
        return "default"

    def _promote_local(self, temp_path: Path, namespace: str, object_key: str) -> None:
        assert isinstance(self._provider, LocalStorageProvider)
        dest = self._provider.resolve_path(namespace, object_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(str(temp_path), str(dest))
            try:
                os.chmod(dest, 0o644)
            except OSError:
                pass
        except Exception as exc:
            raise StorageProviderError("promote_failed", "Promotion fichier échouée") from exc

    def _promote_remote(
        self,
        temp_path: Path,
        namespace: str,
        object_key: str,
        *,
        validation: FileValidationResult,
        checksum: str,
    ) -> None:
        """Upload direct vers clé définitive après validation locale (non atomique distant)."""
        try:
            with temp_path.open("rb") as fh:
                self._provider.put_stream(
                    namespace=namespace,
                    object_key=object_key,
                    stream=fh,
                    size_bytes=validation.size_bytes,
                    content_type=validation.mime_type_detected or validation.mime_type_declared,
                    metadata={"checksum_sha256": checksum},
                    overwrite=False,
                )
        except StorageProviderError:
            raise
        except Exception as exc:
            raise StorageProviderError("remote_put_failed", "Upload distant échoué") from exc
        if not self._provider.object_exists(namespace=namespace, object_key=object_key):
            raise StorageProviderError("remote_verify_failed", "Objet distant non vérifié")

    def _abort_temp(self, *, already_closed: bool = False) -> None:
        if not self._temp:
            return
        try:
            if not already_closed:
                try:
                    self._temp.fh.close()
                except Exception:
                    pass
            if self._temp.path.exists():
                self._temp.path.unlink()
        except OSError:
            logger.debug("temp_cleanup_failed", exc_info=True)
        finally:
            self._temp = None


async def iter_upload_file_chunks(upload_file, *, chunk_size: int | None = None) -> AsyncIterator[bytes]:
    size = int(chunk_size or getattr(settings, "storage_upload_chunk_size_bytes", 65_536) or 65_536)
    while True:
        try:
            chunk = await upload_file.read(size)
        except Exception as exc:
            raise StorageValidationError(
                StorageRejectCode.UPLOAD_INTERRUPTED.value,
                "Upload interrompu",
            ) from exc
        if not chunk:
            break
        yield chunk
