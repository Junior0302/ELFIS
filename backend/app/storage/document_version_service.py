"""Service versions documentaires — immutabilité + concurrence."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.storage.storage_exceptions import (
    DocumentAccessDeniedError,
    DocumentNotFoundError,
    StorageError,
    StorageValidationError,
)
from app.storage.storage_metadata import sanitize_document_metadata
from app.storage.storage_models import ElfisDocumentRecord, ElfisDocumentVersion, ElfisStorageObject
from app.storage.storage_repository import DocumentRepository, DocumentVersionRepository, StorageObjectRepository
from app.storage.storage_service import StorageService
from app.storage.storage_types import DocumentStatus, DocumentVersionStatus

logger = logging.getLogger(__name__)

_IMMUTABLE_FIELDS = frozenset(
    {
        "storage_object_id",
        "checksum_sha256",
        "size_bytes",
        "mime_type",
        "version_number",
        "document_id",
        "original_filename",
    }
)


class DocumentVersionService:
    """
    Stratégie restore (B) : créer une nouvelle version pointant vers le même
    StorageObject historique (pas de copie physique ; purge vérifie les refs).
    """

    def __init__(
        self,
        db: Session,
        *,
        storage: StorageService | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._db = db
        self._docs = DocumentRepository(db)
        self._versions = DocumentVersionRepository(db)
        self._objects = StorageObjectRepository(db)
        self._storage = storage or StorageService(db, audit_logger=audit_logger)
        self._audit = audit_logger

    def assert_version_immutable(self, version: ElfisDocumentVersion, updates: dict[str, Any]) -> None:
        for key in updates:
            if key in _IMMUTABLE_FIELDS:
                raise StorageValidationError(
                    "version_immutable",
                    f"Champ version immuable: {key}",
                )

    def create_initial_version(
        self,
        *,
        document: ElfisDocumentRecord,
        storage_obj: ElfisStorageObject,
        created_by_user_id: int | None = None,
        source: str | None = None,
        commit: bool = False,
    ) -> ElfisDocumentVersion:
        """Crée version 1 (upload initial ou backfill) — pas de copie physique."""
        existing = self._versions.get_by_document_and_number(document.id, 1)
        if existing:
            return existing
        ver = ElfisDocumentVersion(
            id=str(uuid4()),
            document_id=document.id,
            version_number=1,
            storage_object_id=storage_obj.id,
            status=DocumentVersionStatus.CURRENT.value,
            created_by_user_id=created_by_user_id,
            source=(source or document.source or "upload")[:32],
            original_filename=storage_obj.original_filename or storage_obj.safe_filename,
            size_bytes=int(storage_obj.size_bytes or 0),
            checksum_sha256=storage_obj.checksum_sha256,
            mime_type=storage_obj.mime_type_detected or storage_obj.mime_type_declared,
        )
        self._versions.create(ver, commit=False)
        document.current_version_id = ver.id
        document.current_storage_object_id = storage_obj.id
        document.updated_at = datetime.utcnow()
        if commit:
            self._db.commit()
            self._db.refresh(ver)
        else:
            self._db.flush()
        self._safe_audit_version_created(document, ver)
        return ver

    async def add_version_from_stream(
        self,
        *,
        document_id: str,
        organization_id: int,
        filename: str,
        chunk_iterator,
        declared_mime: str | None = None,
        change_reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        created_by_user_id: int | None = None,
        source: str = "upload",
    ) -> ElfisDocumentVersion:
        doc = self._require_mutable_document(document_id, organization_id)
        meta = sanitize_document_metadata(metadata)
        storage_obj = await self._storage.register_from_stream(
            filename=filename,
            chunk_iterator=chunk_iterator,
            declared_mime=declared_mime,
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
            metadata=meta,
            commit=False,
        )
        return self._attach_new_version(
            doc,
            storage_obj,
            change_reason=change_reason,
            created_by_user_id=created_by_user_id,
            source=source,
            metadata=meta,
        )

    def add_version_from_chunks_sync(
        self,
        *,
        document_id: str,
        organization_id: int,
        filename: str,
        chunks: list[bytes],
        declared_mime: str | None = None,
        change_reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        created_by_user_id: int | None = None,
        source: str = "upload",
    ) -> ElfisDocumentVersion:
        doc = self._require_mutable_document(document_id, organization_id)
        meta = sanitize_document_metadata(metadata)
        storage_obj = self._storage.register_from_streamed_sync(
            filename=filename,
            chunks=chunks,
            declared_mime=declared_mime,
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
            metadata=meta,
            commit=False,
        )
        return self._attach_new_version(
            doc,
            storage_obj,
            change_reason=change_reason,
            created_by_user_id=created_by_user_id,
            source=source,
            metadata=meta,
        )

    def restore_as_new_version(
        self,
        *,
        document_id: str,
        organization_id: int,
        version_id: str,
        created_by_user_id: int | None = None,
        change_reason: str | None = None,
    ) -> ElfisDocumentVersion:
        """Stratégie B : nouvelle version référençant l'objet historique."""
        doc = self._require_mutable_document(document_id, organization_id)
        hist = self._versions.get(version_id)
        if not hist or hist.document_id != doc.id:
            raise DocumentNotFoundError("version_not_found", "Version introuvable")
        if hist.status in (DocumentVersionStatus.DELETED.value, DocumentVersionStatus.PURGED.value):
            raise StorageValidationError("version_unavailable", "Version non restaurable")
        obj = self._objects.get(hist.storage_object_id)
        if not obj or obj.status not in ("available", "quarantined"):
            raise StorageValidationError("object_unavailable", "Objet historique indisponible")
        return self._attach_new_version(
            doc,
            obj,
            change_reason=change_reason or f"restore_from_v{hist.version_number}",
            created_by_user_id=created_by_user_id,
            source="restore",
            metadata={"restored_from_version_id": hist.id},
            reuse_object=True,
        )

    def _attach_new_version(
        self,
        doc: ElfisDocumentRecord,
        storage_obj: ElfisStorageObject,
        *,
        change_reason: str | None,
        created_by_user_id: int | None,
        source: str,
        metadata: dict[str, Any] | None,
        reuse_object: bool = False,
    ) -> ElfisDocumentVersion:
        max_attempts = 5
        last_exc: Exception | None = None
        for attempt in range(max_attempts):
            locked = self._docs.lock_for_update(doc.id) or doc
            if locked.status in (DocumentStatus.DELETED.value, DocumentStatus.PURGED.value):
                raise StorageValidationError("document_not_mutable", "Document non modifiable")
            next_num = self._versions.max_version_number(locked.id) + 1
            if locked.current_version_id:
                cur = self._versions.get(locked.current_version_id)
                if cur and cur.status == DocumentVersionStatus.CURRENT.value:
                    cur.status = DocumentVersionStatus.SUPERSEDED.value
                    cur.superseded_at = datetime.utcnow()
                    self._safe_audit_superseded(locked, cur)

            ver = ElfisDocumentVersion(
                id=str(uuid4()),
                document_id=locked.id,
                version_number=next_num,
                storage_object_id=storage_obj.id,
                status=DocumentVersionStatus.CURRENT.value,
                created_by_user_id=created_by_user_id,
                source=(source or "upload")[:32],
                change_reason=(change_reason or "")[:255] or None,
                original_filename=storage_obj.original_filename or storage_obj.safe_filename,
                size_bytes=int(storage_obj.size_bytes or 0),
                checksum_sha256=storage_obj.checksum_sha256,
                mime_type=storage_obj.mime_type_detected or storage_obj.mime_type_declared,
                metadata_json=metadata,
            )
            try:
                self._versions.create(ver, commit=False)
                locked.current_version_id = ver.id
                locked.current_storage_object_id = storage_obj.id
                locked.updated_at = datetime.utcnow()
                if locked.status == DocumentStatus.DRAFT.value:
                    locked.status = DocumentStatus.AVAILABLE.value
                self._db.commit()
                self._db.refresh(ver)
                self._safe_audit_version_created(locked, ver)
                if source == "restore":
                    self._safe_audit_version_restored(locked, ver)
                return ver
            except IntegrityError as exc:
                self._db.rollback()
                last_exc = exc
                continue

        if not reuse_object:
            try:
                self._storage._compensate_delete(
                    namespace=storage_obj.namespace,
                    object_key=storage_obj.object_key,
                    storage_object_id=storage_obj.id,
                    organization_id=doc.organization_id,
                )
            except Exception:
                pass
        raise StorageError("version_conflict", "Conflit de version après retries") from last_exc

    def list_versions(self, document_id: str, organization_id: int) -> list[ElfisDocumentVersion]:
        doc = self._docs.get(document_id)
        if not doc or doc.organization_id != organization_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        return [
            v
            for v in self._versions.list_for_document(document_id)
            if v.status not in (DocumentVersionStatus.DELETED.value, DocumentVersionStatus.PURGED.value)
        ]

    def get_version(
        self, document_id: str, version_id: str, organization_id: int
    ) -> ElfisDocumentVersion:
        doc = self._docs.get(document_id)
        if not doc or doc.organization_id != organization_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        ver = self._versions.get(version_id)
        if not ver or ver.document_id != document_id:
            raise DocumentNotFoundError("version_not_found", "Version introuvable")
        if ver.status in (DocumentVersionStatus.DELETED.value, DocumentVersionStatus.PURGED.value):
            raise DocumentAccessDeniedError("version_access_denied", "Version introuvable")
        return ver

    def _require_mutable_document(self, document_id: str, organization_id: int) -> ElfisDocumentRecord:
        doc = self._docs.get(document_id)
        if not doc or doc.organization_id != organization_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if doc.status in (DocumentStatus.DELETED.value, DocumentStatus.PURGED.value):
            raise StorageValidationError("document_not_mutable", "Document non modifiable")
        # Archive : pas de nouvelle version (politique stricte)
        if doc.status == DocumentStatus.ARCHIVED.value:
            raise StorageValidationError("document_archived", "Document archivé — nouvelle version interdite")
        return doc

    def _safe_audit_version_created(self, doc: ElfisDocumentRecord, ver: ElfisDocumentVersion) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_document_version_created(
                document_id=doc.id,
                version_id=ver.id,
                version_number=ver.version_number,
                organization_id=doc.organization_id,
                actor_user_id=ver.created_by_user_id,
            )
        except Exception:
            logger.debug("audit_version_created_failed", exc_info=True)

    def _safe_audit_superseded(self, doc: ElfisDocumentRecord, ver: ElfisDocumentVersion) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_document_version_superseded(
                document_id=doc.id,
                version_id=ver.id,
                version_number=ver.version_number,
                organization_id=doc.organization_id,
            )
        except Exception:
            logger.debug("audit_version_superseded_failed", exc_info=True)

    def _safe_audit_version_restored(self, doc: ElfisDocumentRecord, ver: ElfisDocumentVersion) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_document_version_restored(
                document_id=doc.id,
                version_id=ver.id,
                version_number=ver.version_number,
                organization_id=doc.organization_id,
                actor_user_id=ver.created_by_user_id,
            )
        except Exception:
            logger.debug("audit_version_restored_failed", exc_info=True)
