"""StorageService — enregistrement objets + flux (sans SQL dans les routes)."""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Iterator
from uuid import uuid4

from sqlalchemy.orm import Session

from app.storage.storage_context import StorageContext, default_storage_context
from app.storage.storage_exceptions import (
    StorageDisabledError,
    StorageError,
    StorageNotFoundError,
    StorageValidationError,
)
from app.storage.storage_metadata import sanitize_document_metadata
from app.storage.storage_models import ElfisStorageObject
from app.storage.storage_provider import StorageProvider
from app.storage.storage_repository import StorageObjectRepository
from app.storage.storage_types import EncryptionStatus, StorageObjectStatus
from app.storage.storage_upload import StreamingUploadPipeline, StreamedUploadResult

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(
        self,
        db: Session,
        *,
        context: StorageContext | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._db = db
        self._ctx = context or default_storage_context()
        self._repo = StorageObjectRepository(db)
        self._audit = audit_logger

    @property
    def provider(self) -> StorageProvider:
        return self._ctx.provider

    async def register_from_stream(
        self,
        *,
        filename: str,
        chunk_iterator: AsyncIterator[bytes],
        declared_mime: str | None = None,
        organization_id: int | None = None,
        created_by_user_id: int | None = None,
        metadata: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> ElfisStorageObject:
        """Upload streaming → objet physique puis métadonnées DB."""
        if self.provider.name == "disabled":
            raise StorageDisabledError("storage_disabled", "Stockage désactivé")
        pipeline = StreamingUploadPipeline(self.provider)
        try:
            streamed = await pipeline.consume_upload_file(
                filename=filename,
                declared_mime=declared_mime,
                chunk_iterator=chunk_iterator,
                organization_id=organization_id,
            )
        except StorageValidationError as exc:
            self._safe_audit_reject(
                reason=exc.code,
                filename=filename,
                size=0,
                mime=declared_mime,
                organization_id=organization_id,
                actor_user_id=created_by_user_id,
            )
            raise
        except StorageDisabledError:
            raise
        except Exception as exc:
            self._safe_audit_failed(
                reason=type(exc).__name__,
                organization_id=organization_id,
                actor_user_id=created_by_user_id,
                size=None,
                mime=declared_mime,
            )
            if isinstance(exc, StorageError):
                raise
            raise StorageError("storage_failed", "Échec upload streaming") from exc

        return self._persist_streamed(
            streamed,
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
            metadata=metadata,
            commit=commit,
        )

    def register_from_streamed_sync(
        self,
        *,
        filename: str,
        chunks: list[bytes],
        declared_mime: str | None = None,
        organization_id: int | None = None,
        created_by_user_id: int | None = None,
        metadata: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> ElfisStorageObject:
        if self.provider.name == "disabled":
            raise StorageDisabledError("storage_disabled", "Stockage désactivé")
        pipeline = StreamingUploadPipeline(self.provider)
        try:
            streamed = pipeline.consume_sync_chunks(
                filename=filename,
                declared_mime=declared_mime,
                chunks=chunks,
                organization_id=organization_id,
            )
        except StorageValidationError as exc:
            self._safe_audit_reject(
                reason=exc.code,
                filename=filename,
                size=sum(len(c) for c in chunks),
                mime=declared_mime,
                organization_id=organization_id,
                actor_user_id=created_by_user_id,
            )
            raise
        return self._persist_streamed(
            streamed,
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
            metadata=metadata,
            commit=commit,
        )

    def _persist_streamed(
        self,
        streamed: StreamedUploadResult,
        *,
        organization_id: int | None,
        created_by_user_id: int | None,
        metadata: dict[str, Any] | None,
        commit: bool,
    ) -> ElfisStorageObject:
        v = streamed.validation
        status = (
            StorageObjectStatus.QUARANTINED.value
            if v.quarantined
            else StorageObjectStatus.AVAILABLE.value
        )
        row = ElfisStorageObject(
            id=str(uuid4()),
            provider=self.provider.name,
            namespace=streamed.namespace,
            object_key=streamed.object_key,
            original_filename=v.original_filename,
            safe_filename=v.safe_filename,
            mime_type_declared=v.mime_type_declared,
            mime_type_detected=v.mime_type_detected,
            extension=v.extension,
            size_bytes=streamed.size_bytes,
            checksum_sha256=streamed.checksum_sha256,
            status=status,
            encryption_status=EncryptionStatus.NONE.value,
            created_by_user_id=created_by_user_id,
            organization_id=organization_id,
            metadata_json=sanitize_document_metadata(metadata),
        )
        try:
            self._repo.create(row, commit=False)
            if commit:
                self._db.commit()
                self._db.refresh(row)
            else:
                self._db.flush()
            if v.quarantined:
                self._safe_audit_quarantined(row)
            return row
        except Exception as exc:
            self._db.rollback()
            compensated = self._compensate_delete(
                namespace=streamed.namespace,
                object_key=streamed.object_key,
                storage_object_id=row.id,
                organization_id=organization_id,
            )
            if not compensated:
                self._safe_audit_orphan(
                    namespace=streamed.namespace,
                    object_key=streamed.object_key,
                    organization_id=organization_id,
                )
            if isinstance(exc, StorageError):
                raise
            raise StorageError("db_failed", "Échec enregistrement métadonnées") from exc

    def register_bytes(
        self,
        *,
        filename: str,
        content: bytes,
        declared_mime: str | None = None,
        organization_id: int | None = None,
        created_by_user_id: int | None = None,
        metadata: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> ElfisStorageObject:
        """Compat — découpe en chunks pour le même pipeline streaming."""
        chunk = 65_536
        chunks = [content[i : i + chunk] for i in range(0, len(content), chunk)] or [b""]
        return self.register_from_streamed_sync(
            filename=filename,
            chunks=chunks,
            declared_mime=declared_mime,
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
            metadata=metadata,
            commit=commit,
        )

    def _compensate_delete(
        self,
        *,
        namespace: str,
        object_key: str,
        storage_object_id: str | None,
        organization_id: int | None,
    ) -> bool:
        try:
            ok = self.provider.delete_object(namespace=namespace, object_key=object_key)
            self._safe_audit_compensated(
                storage_object_id=storage_object_id,
                organization_id=organization_id,
                success=ok,
            )
            return ok
        except Exception:
            logger.debug("compensation_delete_failed", exc_info=True)
            self._safe_audit_compensated(
                storage_object_id=storage_object_id,
                organization_id=organization_id,
                success=False,
            )
            return False

    def get_object_row(self, object_id: str) -> ElfisStorageObject | None:
        return self._repo.get(object_id)

    def open_stream(self, object_id: str, *, allow_quarantine: bool = False):
        row = self._repo.get(object_id)
        if not row or row.status == StorageObjectStatus.DELETED.value:
            raise StorageNotFoundError("object_not_found", "Objet introuvable")
        if row.status == StorageObjectStatus.QUARANTINED.value and not allow_quarantine:
            raise StorageValidationError("object_quarantined", "Objet en quarantaine")
        if row.status not in (
            StorageObjectStatus.AVAILABLE.value,
            StorageObjectStatus.QUARANTINED.value,
        ):
            raise StorageNotFoundError("object_unavailable", "Objet indisponible")
        if not self.provider.object_exists(namespace=row.namespace, object_key=row.object_key):
            raise StorageNotFoundError("object_missing", "Fichier physique manquant")
        return self.provider.open_stream(namespace=row.namespace, object_key=row.object_key)

    def iter_chunks(self, object_id: str, *, chunk_size: int = 65536) -> Iterator[bytes]:
        row = self._repo.get(object_id)
        if not row or row.status == StorageObjectStatus.DELETED.value:
            raise StorageNotFoundError("object_not_found", "Objet introuvable")
        yield from self.provider.iter_chunks(
            namespace=row.namespace,
            object_key=row.object_key,
            chunk_size=chunk_size,
        )

    def mark_deleted(self, object_id: str, *, commit: bool = True) -> bool:
        return self._repo.mark_deleted(object_id, commit=commit)

    def find_org_checksum_duplicate(
        self,
        *,
        organization_id: int,
        checksum_sha256: str,
        exclude_id: str | None = None,
    ) -> ElfisStorageObject | None:
        """Doublon candidate même org uniquement — jamais cross-tenant."""
        return self._repo.find_by_org_checksum(
            organization_id, checksum_sha256, exclude_id=exclude_id
        )

    def _safe_audit_reject(self, **kwargs: Any) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_storage_object_rejected(**kwargs)
        except Exception:
            logger.debug("audit_storage_reject_failed", exc_info=True)

    def _safe_audit_failed(self, **kwargs: Any) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_storage_object_failed(**kwargs)
        except Exception:
            logger.debug("audit_storage_failed_event", exc_info=True)

    def _safe_audit_quarantined(self, row: ElfisStorageObject) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_storage_object_quarantined(
                storage_object_id=row.id,
                organization_id=row.organization_id,
                size_bytes=row.size_bytes,
                mime=row.mime_type_detected or row.mime_type_declared,
                reason=row.metadata_json.get("reject_reason") if isinstance(row.metadata_json, dict) else None,
            )
        except Exception:
            logger.debug("audit_quarantine_failed", exc_info=True)

    def _safe_audit_compensated(
        self,
        *,
        storage_object_id: str | None,
        organization_id: int | None,
        success: bool,
    ) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_storage_object_compensated(
                storage_object_id=storage_object_id,
                organization_id=organization_id,
                success=success,
            )
        except Exception:
            logger.debug("audit_compensate_failed", exc_info=True)

    def _safe_audit_orphan(
        self,
        *,
        namespace: str,
        object_key: str,
        organization_id: int | None,
    ) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_storage_object_orphan_detected(
                organization_id=organization_id,
                metadata={"namespace": namespace, "object_key_prefix": (object_key or "")[:8]},
            )
        except Exception:
            logger.debug("audit_orphan_failed", exc_info=True)
