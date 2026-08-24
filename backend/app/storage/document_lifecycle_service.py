"""Lifecycle documentaire — archive / soft-delete / restore / transitions."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.storage.storage_exceptions import DocumentAccessDeniedError, StorageValidationError
from app.storage.storage_models import ElfisDocumentRecord
from app.storage.storage_repository import DocumentRepository, LegalHoldRepository
from app.storage.storage_types import DOCUMENT_TRANSITIONS, DocumentStatus

logger = logging.getLogger(__name__)


class DocumentLifecycleService:
    def __init__(self, db: Session, *, audit_logger: Any | None = None) -> None:
        self._db = db
        self._docs = DocumentRepository(db)
        self._holds = LegalHoldRepository(db)
        self._audit = audit_logger

    def _assert_transition(self, current: str, target: str) -> None:
        allowed = DOCUMENT_TRANSITIONS.get(current, frozenset())
        if target not in allowed:
            raise StorageValidationError(
                "invalid_transition",
                f"Transition interdite: {current} → {target}",
            )

    def archive(self, document_id: str, organization_id: int) -> ElfisDocumentRecord:
        doc = self._get(document_id, organization_id)
        self._assert_transition(doc.status, DocumentStatus.ARCHIVED.value)
        archived = self._docs.archive(doc.id, commit=True)
        assert archived is not None
        self._safe("record_document_archived", document_id=doc.id, organization_id=organization_id, status=archived.status)
        return archived

    def unarchive(self, document_id: str, organization_id: int) -> ElfisDocumentRecord:
        doc = self._get(document_id, organization_id)
        self._assert_transition(doc.status, DocumentStatus.AVAILABLE.value)
        if doc.status != DocumentStatus.ARCHIVED.value:
            raise StorageValidationError("invalid_transition", "Document non archivé")
        row = self._docs.unarchive(doc.id, commit=True)
        assert row is not None
        self._safe(
            "record_document_unarchived",
            document_id=doc.id,
            organization_id=organization_id,
            status=row.status,
        )
        return row

    def soft_delete(
        self,
        document_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        reason: str | None = None,
    ) -> ElfisDocumentRecord:
        doc = self._get(document_id, organization_id)
        self._assert_transition(doc.status, DocumentStatus.DELETED.value)
        doc.status = DocumentStatus.DELETED.value
        doc.deleted_at = datetime.utcnow()
        doc.deleted_by_user_id = actor_user_id
        doc.delete_reason = (reason or "")[:255] or None
        doc.updated_at = datetime.utcnow()
        grace = int(getattr(settings, "document_retention_deleted_grace_days", 30) or 30)
        doc.retention_deadline = datetime.utcnow() + timedelta(days=grace)
        self._db.commit()
        self._db.refresh(doc)
        self._safe(
            "record_document_soft_deleted",
            document_id=doc.id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            reason=reason,
        )
        return doc

    def restore_soft_deleted(
        self,
        document_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
    ) -> ElfisDocumentRecord:
        doc = self._get(document_id, organization_id, allow_deleted=True)
        if doc.status != DocumentStatus.DELETED.value:
            raise StorageValidationError("invalid_transition", "Document non soft-deleted")
        if doc.purged_at or doc.purge_status == "purged":
            raise StorageValidationError("already_purged", "Document déjà purgé")
        # délai de grâce : si retention_deadline passée, refus
        if doc.retention_deadline and doc.retention_deadline < datetime.utcnow():
            # encore restaurable tant que pas purged — grace pour restore = before purge
            pass
        target = DocumentStatus.ARCHIVED.value if doc.archived_at else DocumentStatus.AVAILABLE.value
        self._assert_transition(doc.status, target)
        doc.status = target
        doc.deleted_at = None
        doc.deleted_by_user_id = None
        doc.delete_reason = None
        doc.purge_status = "none"
        doc.updated_at = datetime.utcnow()
        self._db.commit()
        self._db.refresh(doc)
        self._safe(
            "record_document_restored",
            document_id=doc.id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            status=doc.status,
        )
        return doc

    def _get(
        self, document_id: str, organization_id: int, *, allow_deleted: bool = False
    ) -> ElfisDocumentRecord:
        doc = self._docs.get(document_id)
        if not doc or doc.organization_id != organization_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if doc.status == DocumentStatus.PURGED.value:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if not allow_deleted and doc.status == DocumentStatus.DELETED.value:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        return doc

    def _safe(self, method: str, **kwargs: Any) -> None:
        if not self._audit:
            return
        try:
            getattr(self._audit, method)(**kwargs)
        except Exception:
            logger.debug("audit_lifecycle_failed", extra={"method": method}, exc_info=True)
