"""DocumentRegistryService — documents logiques + liens métier + upload streaming."""

from __future__ import annotations

import logging
import time
from typing import Any, AsyncIterator
from uuid import uuid4

from sqlalchemy.orm import Session

from app.storage.document_access_policy import DocumentAccessPolicy
from app.storage.document_lifecycle_service import DocumentLifecycleService
from app.storage.document_version_service import DocumentVersionService
from app.storage.storage_context import StorageContext
from app.storage.storage_exceptions import (
    DocumentAccessDeniedError,
    DocumentNotFoundError,
    StorageValidationError,
)
from app.storage.storage_metadata import sanitize_document_metadata
from app.storage.storage_models import ElfisDocumentLink, ElfisDocumentRecord, ElfisStorageObject
from app.storage.storage_repository import DocumentLinkRepository, DocumentRepository
from app.storage.storage_service import StorageService
from app.storage.storage_types import (
    DocumentEntityType,
    DocumentRelationType,
    DocumentSource,
    DocumentStatus,
    StorageObjectStatus,
)

logger = logging.getLogger(__name__)

_VALID_ENTITY = {e.value for e in DocumentEntityType}
_VALID_RELATION = {r.value for r in DocumentRelationType}
_VALID_SOURCE = {s.value for s in DocumentSource}


class DocumentRegistryService:
    def __init__(
        self,
        db: Session,
        *,
        storage: StorageService | None = None,
        context: StorageContext | None = None,
        audit_logger: Any | None = None,
        access_policy: DocumentAccessPolicy | None = None,
    ) -> None:
        self._db = db
        self._docs = DocumentRepository(db)
        self._links = DocumentLinkRepository(db)
        self._audit = audit_logger
        self._storage = storage or StorageService(db, context=context, audit_logger=audit_logger)
        self._access = access_policy or DocumentAccessPolicy()
        self._versions = DocumentVersionService(db, storage=self._storage, audit_logger=audit_logger)
        self._lifecycle = DocumentLifecycleService(db, audit_logger=audit_logger)

    @property
    def access(self) -> DocumentAccessPolicy:
        return self._access

    @property
    def storage(self) -> StorageService:
        return self._storage

    async def create_from_stream(
        self,
        *,
        organization_id: int,
        filename: str,
        chunk_iterator: AsyncIterator[bytes],
        declared_mime: str | None = None,
        title: str | None = None,
        document_type: str = "file",
        product: str | None = None,
        source: str = DocumentSource.UPLOAD.value,
        owner_user_id: int | None = None,
        metadata: dict[str, Any] | None = None,
        links: list[dict[str, str]] | None = None,
    ) -> tuple[ElfisDocumentRecord, bool]:
        """Retourne (document, duplicate_candidate)."""
        started = time.perf_counter()
        self._safe_audit_upload_started(
            organization_id=organization_id,
            actor_user_id=owner_user_id,
            filename=filename,
        )
        if organization_id is None or int(organization_id) <= 0:
            raise StorageValidationError("ORGANIZATION_REQUIRED", "Organisation obligatoire")
        src = (source or DocumentSource.UPLOAD.value).strip().lower()
        if src not in _VALID_SOURCE:
            raise StorageValidationError("SECURITY_POLICY_REJECTED", f"Source invalide: {src}")
        meta = sanitize_document_metadata(metadata)

        try:
            storage_obj = await self._storage.register_from_stream(
                filename=filename,
                chunk_iterator=chunk_iterator,
                declared_mime=declared_mime,
                organization_id=organization_id,
                created_by_user_id=owner_user_id,
                metadata=meta,
                commit=False,
            )
        except Exception as exc:
            self._safe_audit_upload_failed(
                organization_id=organization_id,
                actor_user_id=owner_user_id,
                reason=getattr(exc, "code", type(exc).__name__),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            raise

        duplicate = False
        if storage_obj.checksum_sha256:
            prior = self._storage.find_org_checksum_duplicate(
                organization_id=organization_id,
                checksum_sha256=storage_obj.checksum_sha256,
                exclude_id=storage_obj.id,
            )
            if prior:
                duplicate = True

        doc_status = (
            DocumentStatus.AVAILABLE.value
            if storage_obj.status == StorageObjectStatus.AVAILABLE.value
            else DocumentStatus.DRAFT.value
        )
        if storage_obj.status == StorageObjectStatus.QUARANTINED.value:
            doc_status = DocumentStatus.FAILED.value

        doc = ElfisDocumentRecord(
            id=str(uuid4()),
            document_type=(document_type or "file")[:64],
            title=(title or storage_obj.safe_filename or "document")[:255],
            status=doc_status,
            organization_id=organization_id,
            product=(product or None),
            current_storage_object_id=storage_obj.id,
            owner_user_id=owner_user_id,
            source=src,
            metadata_json={
                **(meta or {}),
                **({"duplicate_candidate": True} if duplicate else {}),
            }
            or None,
        )
        try:
            self._docs.create(doc, commit=False)
            if links:
                for link_spec in links:
                    self._create_link_row(
                        doc,
                        entity_type=link_spec.get("entity_type", ""),
                        entity_id=link_spec.get("entity_id", ""),
                        relation_type=link_spec.get("relation_type", "attachment"),
                        created_by_user_id=owner_user_id,
                        commit=False,
                    )
            self._versions.create_initial_version(
                document=doc,
                storage_obj=storage_obj,
                created_by_user_id=owner_user_id,
                source=src,
                commit=False,
            )
            self._db.commit()
            self._db.refresh(doc)
        except Exception as exc:
            self._db.rollback()
            self._storage._compensate_delete(
                namespace=storage_obj.namespace,
                object_key=storage_obj.object_key,
                storage_object_id=storage_obj.id,
                organization_id=organization_id,
            )
            self._safe_audit_upload_failed(
                organization_id=organization_id,
                actor_user_id=owner_user_id,
                reason=type(exc).__name__,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            raise

        duration = int((time.perf_counter() - started) * 1000)
        self._safe_audit_created(doc, storage_obj)
        self._safe_audit_upload_completed(doc, storage_obj, duration_ms=duration)
        return doc, duplicate

    def create_from_upload(
        self,
        *,
        organization_id: int,
        filename: str,
        content: bytes,
        declared_mime: str | None = None,
        title: str | None = None,
        document_type: str = "file",
        product: str | None = None,
        source: str = DocumentSource.UPLOAD.value,
        owner_user_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ElfisDocumentRecord:
        """Compat sync — utilise le pipeline streaming par chunks."""
        import asyncio

        async def _run():
            chunk = 65_536

            async def gen():
                if not content:
                    return
                for i in range(0, len(content), chunk):
                    yield content[i : i + chunk]

            doc, _ = await self.create_from_stream(
                organization_id=organization_id,
                filename=filename,
                chunk_iterator=gen(),
                declared_mime=declared_mime,
                title=title,
                document_type=document_type,
                product=product,
                source=source,
                owner_user_id=owner_user_id,
                metadata=metadata,
            )
            return doc

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # tests sync: bypass via storage sync path
                return self._create_from_upload_sync(
                    organization_id=organization_id,
                    filename=filename,
                    content=content,
                    declared_mime=declared_mime,
                    title=title,
                    document_type=document_type,
                    product=product,
                    source=source,
                    owner_user_id=owner_user_id,
                    metadata=metadata,
                )
            return loop.run_until_complete(_run())
        except RuntimeError:
            return asyncio.run(_run())

    def _create_from_upload_sync(self, **kwargs) -> ElfisDocumentRecord:
        content = kwargs.pop("content")
        filename = kwargs["filename"]
        chunk = 65_536
        chunks = [content[i : i + chunk] for i in range(0, len(content), chunk)] or [b""]
        organization_id = kwargs["organization_id"]
        owner_user_id = kwargs.get("owner_user_id")
        declared_mime = kwargs.get("declared_mime")
        meta = sanitize_document_metadata(kwargs.get("metadata"))
        started = time.perf_counter()
        self._safe_audit_upload_started(
            organization_id=organization_id,
            actor_user_id=owner_user_id,
            filename=filename,
        )
        try:
            storage_obj = self._storage.register_from_streamed_sync(
                filename=filename,
                chunks=chunks,
                declared_mime=declared_mime,
                organization_id=organization_id,
                created_by_user_id=owner_user_id,
                metadata=meta,
                commit=False,
            )
        except Exception as exc:
            self._safe_audit_upload_failed(
                organization_id=organization_id,
                actor_user_id=owner_user_id,
                reason=getattr(exc, "code", type(exc).__name__),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            raise

        duplicate = False
        if storage_obj.checksum_sha256:
            prior = self._storage.find_org_checksum_duplicate(
                organization_id=organization_id,
                checksum_sha256=storage_obj.checksum_sha256,
                exclude_id=storage_obj.id,
            )
            if prior:
                duplicate = True

        doc_status = (
            DocumentStatus.AVAILABLE.value
            if storage_obj.status == StorageObjectStatus.AVAILABLE.value
            else DocumentStatus.DRAFT.value
        )
        if storage_obj.status == StorageObjectStatus.QUARANTINED.value:
            doc_status = DocumentStatus.FAILED.value

        doc = ElfisDocumentRecord(
            id=str(uuid4()),
            document_type=(kwargs.get("document_type") or "file")[:64],
            title=(kwargs.get("title") or storage_obj.safe_filename or "document")[:255],
            status=doc_status,
            organization_id=organization_id,
            product=kwargs.get("product"),
            current_storage_object_id=storage_obj.id,
            owner_user_id=owner_user_id,
            source=(kwargs.get("source") or DocumentSource.UPLOAD.value).strip().lower(),
            metadata_json={
                **(meta or {}),
                **({"duplicate_candidate": True} if duplicate else {}),
            }
            or None,
        )
        try:
            self._docs.create(doc, commit=False)
            self._versions.create_initial_version(
                document=doc,
                storage_obj=storage_obj,
                created_by_user_id=owner_user_id,
                source=(kwargs.get("source") or DocumentSource.UPLOAD.value).strip().lower(),
                commit=False,
            )
            self._db.commit()
            self._db.refresh(doc)
        except Exception:
            self._db.rollback()
            self._storage._compensate_delete(
                namespace=storage_obj.namespace,
                object_key=storage_obj.object_key,
                storage_object_id=storage_obj.id,
                organization_id=organization_id,
            )
            raise
        self._safe_audit_created(doc, storage_obj)
        self._safe_audit_upload_completed(
            doc, storage_obj, duration_ms=int((time.perf_counter() - started) * 1000)
        )
        return doc

    def get_for_organization(
        self,
        document_id: str,
        organization_id: int,
        *,
        allow_deleted: bool = False,
    ) -> ElfisDocumentRecord:
        doc = self._docs.get(document_id)
        if not doc:
            raise DocumentNotFoundError("document_not_found", "Document introuvable")
        if doc.organization_id != organization_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if doc.status == DocumentStatus.PURGED.value:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if not allow_deleted and doc.status == DocumentStatus.DELETED.value:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        return doc

    def list_for_organization(
        self,
        organization_id: int,
        *,
        include_archived: bool = False,
        document_type: str | None = None,
        source: str | None = None,
        status: str | None = None,
        product: str | None = None,
        filename_contains: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ElfisDocumentRecord], int]:
        return self._docs.list_for_organization(
            organization_id,
            include_archived=include_archived,
            document_type=document_type,
            source=source,
            status=status,
            product=product,
            filename_contains=filename_contains,
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
            offset=offset,
        )

    def _create_link_row(
        self,
        doc: ElfisDocumentRecord,
        *,
        entity_type: str,
        entity_id: str,
        relation_type: str,
        created_by_user_id: int | None,
        commit: bool,
    ) -> ElfisDocumentLink:
        et = (entity_type or "").strip().lower()
        rt = (relation_type or "").strip().lower()
        if et not in _VALID_ENTITY:
            raise StorageValidationError("SECURITY_POLICY_REJECTED", f"entity_type invalide: {et}")
        if rt not in _VALID_RELATION:
            raise StorageValidationError("SECURITY_POLICY_REJECTED", f"relation_type invalide: {rt}")
        eid = str(entity_id or "").strip()[:128]
        if not eid:
            raise StorageValidationError("SECURITY_POLICY_REJECTED", "entity_id requis")
        existing = self._links.find_existing(
            document_id=doc.id,
            entity_type=et,
            entity_id=eid,
            relation_type=rt,
        )
        if existing:
            return existing
        link = ElfisDocumentLink(
            id=str(uuid4()),
            document_id=doc.id,
            entity_type=et,
            entity_id=eid,
            relation_type=rt,
            created_by_user_id=created_by_user_id,
        )
        return self._links.create(link, commit=commit)

    def link_entity(
        self,
        *,
        document_id: str,
        organization_id: int,
        entity_type: str,
        entity_id: str,
        relation_type: str = DocumentRelationType.ATTACHMENT.value,
        created_by_user_id: int | None = None,
    ) -> ElfisDocumentLink:
        doc = self.get_for_organization(document_id, organization_id)
        link = self._create_link_row(
            doc,
            entity_type=entity_type,
            entity_id=entity_id,
            relation_type=relation_type,
            created_by_user_id=created_by_user_id,
            commit=True,
        )
        self._safe_audit_linked(doc, link)
        return link

    def archive(
        self,
        *,
        document_id: str,
        organization_id: int,
    ) -> ElfisDocumentRecord:
        return self._lifecycle.archive(document_id, organization_id)

    def unarchive(
        self,
        *,
        document_id: str,
        organization_id: int,
    ) -> ElfisDocumentRecord:
        return self._lifecycle.unarchive(document_id, organization_id)

    def soft_delete(
        self,
        *,
        document_id: str,
        organization_id: int,
        actor_user_id: int | None = None,
        reason: str | None = None,
    ) -> ElfisDocumentRecord:
        return self._lifecycle.soft_delete(
            document_id,
            organization_id,
            actor_user_id=actor_user_id,
            reason=reason,
        )

    def restore_soft_deleted(
        self,
        *,
        document_id: str,
        organization_id: int,
        actor_user_id: int | None = None,
    ) -> ElfisDocumentRecord:
        return self._lifecycle.restore_soft_deleted(
            document_id,
            organization_id,
            actor_user_id=actor_user_id,
        )

    @property
    def versions(self) -> DocumentVersionService:
        return self._versions

    def get_storage_object(
        self,
        document: ElfisDocumentRecord,
    ) -> ElfisStorageObject | None:
        if not document.current_storage_object_id:
            return None
        return self._storage.get_object_row(document.current_storage_object_id)

    def open_download(self, document: ElfisDocumentRecord, *, allow_quarantine: bool = False):
        if not document.current_storage_object_id:
            raise DocumentNotFoundError("no_storage_object", "Aucun fichier associé")
        return self._storage.open_stream(
            document.current_storage_object_id, allow_quarantine=allow_quarantine
        )

    def _safe_audit_created(self, doc: ElfisDocumentRecord, obj: ElfisStorageObject) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_document_created(
                document_id=doc.id,
                storage_object_id=obj.id,
                organization_id=doc.organization_id,
                actor_user_id=doc.owner_user_id,
                source=doc.source,
                status=doc.status,
                mime=obj.mime_type_detected or obj.mime_type_declared,
                size_bytes=obj.size_bytes,
            )
        except Exception:
            logger.debug("audit_document_created_failed", exc_info=True)

    def _safe_audit_upload_started(self, **kwargs: Any) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_document_upload_started(**kwargs)
        except Exception:
            logger.debug("audit_upload_started_failed", exc_info=True)

    def _safe_audit_upload_completed(
        self, doc: ElfisDocumentRecord, obj: ElfisStorageObject, *, duration_ms: int
    ) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_document_upload_completed(
                document_id=doc.id,
                storage_object_id=obj.id,
                organization_id=doc.organization_id,
                actor_user_id=doc.owner_user_id,
                size_bytes=obj.size_bytes,
                mime=obj.mime_type_detected or obj.mime_type_declared,
                status=obj.status,
                duration_ms=duration_ms,
                checksum_prefix=(obj.checksum_sha256 or "")[:12] or None,
            )
        except Exception:
            logger.debug("audit_upload_completed_failed", exc_info=True)

    def _safe_audit_upload_failed(self, **kwargs: Any) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_document_upload_failed(**kwargs)
        except Exception:
            logger.debug("audit_upload_failed_event", exc_info=True)

    def _safe_audit_linked(self, doc: ElfisDocumentRecord, link: ElfisDocumentLink) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_document_linked(
                document_id=doc.id,
                organization_id=doc.organization_id,
                actor_user_id=link.created_by_user_id,
                entity_type=link.entity_type,
                entity_id=link.entity_id,
                relation_type=link.relation_type,
            )
        except Exception:
            logger.debug("audit_document_linked_failed", exc_info=True)

    def _safe_audit_archived(self, doc: ElfisDocumentRecord) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_document_archived(
                document_id=doc.id,
                organization_id=doc.organization_id,
                actor_user_id=doc.owner_user_id,
                status=doc.status,
            )
        except Exception:
            logger.debug("audit_document_archived_failed", exc_info=True)
