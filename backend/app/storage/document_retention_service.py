"""Rétention & purge contrôlée — preview / batch / tombstones."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.storage.storage_exceptions import StorageValidationError
from app.storage.storage_models import (
    ElfisDocumentRecord,
    ElfisDocumentTombstone,
    ElfisDocumentVersion,
    ElfisStorageObject,
)
from app.storage.storage_provider import StorageProvider
from app.storage.storage_registry import get_default_storage_provider
from app.storage.storage_repository import (
    DocumentRepository,
    DocumentVersionRepository,
    LegalHoldRepository,
    StorageObjectRepository,
    TombstoneRepository,
)
from app.storage.storage_types import (
    PURGE_BLOCKING_RELATIONS,
    DocumentPurgeStatus,
    DocumentStatus,
    DocumentVersionStatus,
    StorageObjectStatus,
)
from app.storage.storage_repository import DocumentLinkRepository

logger = logging.getLogger(__name__)


@dataclass
class RetentionDecision:
    document_id: str
    eligible: bool
    rule: str
    deadline: datetime | None = None
    blocked_reason: str | None = None
    legal_hold: bool = False
    status: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class DocumentRetentionService:
    def __init__(
        self,
        db: Session,
        *,
        provider: StorageProvider | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._db = db
        self._docs = DocumentRepository(db)
        self._versions = DocumentVersionRepository(db)
        self._objects = StorageObjectRepository(db)
        self._holds = LegalHoldRepository(db)
        self._links = DocumentLinkRepository(db)
        self._tombstones = TombstoneRepository(db)
        self._provider = provider or get_default_storage_provider()
        self._audit = audit_logger

    def calculate_retention_deadline(self, doc: ElfisDocumentRecord) -> tuple[datetime, str]:
        default_days = int(getattr(settings, "document_retention_default_days", 365) or 365)
        archived_days = int(getattr(settings, "document_retention_archived_days", 730) or 730)
        deleted_grace = int(getattr(settings, "document_retention_deleted_grace_days", 30) or 30)
        security_min = int(getattr(settings, "document_retention_security_min_days", 90) or 90)

        base = doc.created_at or datetime.utcnow()
        days = max(default_days, security_min)
        rule = "default"

        if doc.document_type in {"invoice", "quote", "export"}:
            days = max(days, 2555)
            rule = f"type:{doc.document_type}"
        if doc.status == DocumentStatus.ARCHIVED.value:
            days = max(archived_days, security_min)
            rule = "archived"
            base = doc.archived_at or base
        if doc.status == DocumentStatus.DELETED.value:
            days = deleted_grace
            rule = "deleted_grace"
            base = doc.deleted_at or base

        return base + timedelta(days=days), rule

    def explain_retention_decision(self, doc: ElfisDocumentRecord) -> RetentionDecision:
        deadline, rule = self.calculate_retention_deadline(doc)

        hold = self._holds.has_active(doc.id)
        if hold:
            return RetentionDecision(
                document_id=doc.id,
                eligible=False,
                rule=rule,
                deadline=deadline,
                blocked_reason="legal_hold",
                legal_hold=True,
                status=doc.status,
            )
        if doc.status == DocumentStatus.PURGED.value:
            return RetentionDecision(
                document_id=doc.id,
                eligible=False,
                rule=rule,
                deadline=deadline,
                blocked_reason="already_purged",
                status=doc.status,
            )
        if doc.status != DocumentStatus.DELETED.value:
            return RetentionDecision(
                document_id=doc.id,
                eligible=False,
                rule=rule,
                deadline=deadline,
                blocked_reason="status_not_deleted",
                status=doc.status,
            )

        blocking = [
            l
            for l in self._links.list_for_document(doc.id)
            if l.relation_type in PURGE_BLOCKING_RELATIONS
        ]
        if blocking:
            return RetentionDecision(
                document_id=doc.id,
                eligible=False,
                rule=rule,
                deadline=deadline,
                blocked_reason="active_business_link",
                status=doc.status,
                details={"link_count": len(blocking)},
            )

        now = datetime.utcnow()
        effective = doc.retention_deadline or deadline
        if effective and effective > now:
            return RetentionDecision(
                document_id=doc.id,
                eligible=False,
                rule=rule,
                deadline=effective,
                blocked_reason="retention_not_expired",
                status=doc.status,
            )
        return RetentionDecision(
            document_id=doc.id,
            eligible=True,
            rule=rule,
            deadline=effective,
            status=doc.status,
        )

    def preview_expired_documents(self, *, limit: int = 100) -> list[RetentionDecision]:
        rows = (
            self._db.query(ElfisDocumentRecord)
            .filter(ElfisDocumentRecord.status == DocumentStatus.DELETED.value)
            .order_by(ElfisDocumentRecord.deleted_at.asc())
            .limit(max(1, min(limit, 500)))
            .all()
        )
        return [self.explain_retention_decision(r) for r in rows]

    def list_purge_candidates(self, *, before: datetime | None = None, limit: int = 100) -> list[ElfisDocumentRecord]:
        q = self._db.query(ElfisDocumentRecord).filter(
            ElfisDocumentRecord.status == DocumentStatus.DELETED.value,
            ElfisDocumentRecord.purge_status != DocumentPurgeStatus.PURGED.value,
        )
        if before:
            q = q.filter(
                (ElfisDocumentRecord.retention_deadline.is_(None))
                | (ElfisDocumentRecord.retention_deadline <= before)
            )
        out: list[ElfisDocumentRecord] = []
        for row in q.order_by(ElfisDocumentRecord.deleted_at.asc()).limit(limit * 2).all():
            decision = self.explain_retention_decision(row)
            if decision.eligible:
                out.append(row)
            if len(out) >= limit:
                break
        return out

    def soft_delete(self, *args, **kwargs):
        from app.storage.document_lifecycle_service import DocumentLifecycleService

        return DocumentLifecycleService(self._db, audit_logger=self._audit).soft_delete(*args, **kwargs)

    def restore_soft_deleted(self, *args, **kwargs):
        from app.storage.document_lifecycle_service import DocumentLifecycleService

        return DocumentLifecycleService(self._db, audit_logger=self._audit).restore_soft_deleted(
            *args, **kwargs
        )

    def calculate_purge_eligibility(self, doc: ElfisDocumentRecord) -> RetentionDecision:
        return self.explain_retention_decision(doc)

    def purge_candidates(
        self,
        *,
        before: datetime | None = None,
        batch_size: int | None = None,
        actor_user_id: int | None = None,
        reason: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        size = batch_size or int(getattr(settings, "document_purge_batch_size", 100) or 100)
        size = max(1, min(size, 200))
        candidates = self.list_purge_candidates(before=before or datetime.utcnow(), limit=size)
        report: dict[str, Any] = {
            "preview": dry_run,
            "candidates": len(candidates),
            "purged": 0,
            "blocked": 0,
            "failed": 0,
            "ids": [c.id for c in candidates],
        }
        if dry_run:
            return report

        for doc in candidates:
            try:
                # re-check hold just before
                decision = self.explain_retention_decision(doc)
                if not decision.eligible:
                    report["blocked"] += 1
                    self._safe_audit_blocked(doc, decision.blocked_reason)
                    continue
                self._purge_one(doc, actor_user_id=actor_user_id, reason=reason)
                report["purged"] += 1
            except Exception as exc:
                logger.warning("purge_failed", extra={"document_id": doc.id, "error": type(exc).__name__})
                report["failed"] += 1
                self._safe_audit_purge_failed(doc, str(type(exc).__name__))
                self._db.rollback()
        return report

    def _purge_one(
        self,
        doc: ElfisDocumentRecord,
        *,
        actor_user_id: int | None,
        reason: str | None,
    ) -> None:
        """
        Ordre sûr : mark purge_pending → delete physical → mark DB purged → tombstone.
        Préférer tombstone + reprise si DB échoue après delete physique.
        """
        if self._holds.has_active(doc.id):
            raise StorageValidationError("legal_hold", "Legal hold actif")

        doc.purge_status = DocumentPurgeStatus.PENDING.value
        self._db.flush()

        # Artefacts extraction puis OCR (ordre : extraction → OCR → document storage)
        try:
            from app.document_processing.extraction.service import DocumentExtractionService

            DocumentExtractionService(self._db, audit_logger=self._audit).purge_artifacts_for_document(
                doc.id,
                organization_id=doc.organization_id,
                legal_hold_active=False,
            )
        except Exception:
            logger.warning("extraction_purge_hook_failed", extra={"document_id": doc.id})

        try:
            from app.document_processing.ocr.service import DocumentOCRService

            DocumentOCRService(self._db, audit_logger=self._audit).purge_artifacts_for_document(
                doc.id,
                organization_id=doc.organization_id,
                legal_hold_active=False,  # déjà vérifié ci-dessus
            )
        except Exception:
            logger.warning("ocr_purge_hook_failed", extra={"document_id": doc.id})

        versions = self._versions.list_for_document(doc.id)
        storage_ids = {v.storage_object_id for v in versions}
        if doc.current_storage_object_id:
            storage_ids.add(doc.current_storage_object_id)

        # 1) supprimer physiques seulement si aucune autre version active ailleurs
        for oid in storage_ids:
            refs = self._objects.count_version_refs(oid)
            obj = self._objects.get(oid)
            if not obj:
                continue
            # refs includes current versions of this doc — after we mark purged we'll clear
            # For shared across docs: count versions not in this document
            other_refs = (
                self._db.query(ElfisDocumentVersion)
                .filter(
                    ElfisDocumentVersion.storage_object_id == oid,
                    ElfisDocumentVersion.document_id != doc.id,
                    ElfisDocumentVersion.status != DocumentVersionStatus.PURGED.value,
                )
                .count()
            )
            if other_refs > 0:
                continue
            try:
                self._provider.delete_object(namespace=obj.namespace, object_key=obj.object_key)
            except Exception:
                # marque failed pour reprise — ne pas mentir sur purge
                obj.status = StorageObjectStatus.FAILED.value
                self._db.flush()
                raise
            self._objects.mark_purged(oid, commit=False)

        for ver in versions:
            ver.status = DocumentVersionStatus.PURGED.value
            ver.deleted_at = ver.deleted_at or datetime.utcnow()

        checksum = None
        if doc.current_storage_object_id:
            cur = self._objects.get(doc.current_storage_object_id)
            if cur and cur.checksum_sha256:
                checksum = cur.checksum_sha256[:12]

        tomb = ElfisDocumentTombstone(
            id=str(uuid4()),
            document_id=doc.id,
            organization_id=doc.organization_id,
            document_type=doc.document_type,
            title_redacted=(doc.title or "")[:1] + "***" if doc.title else None,
            source=doc.source,
            created_at_original=doc.created_at,
            deleted_at=doc.deleted_at,
            purged_at=datetime.utcnow(),
            purged_by_user_id=actor_user_id,
            purge_reason=(reason or "retention_purge")[:255],
            checksum_prefix=checksum,
            version_count=len(versions),
        )
        if not self._tombstones.get_by_document(doc.id):
            self._tombstones.create(tomb, commit=False)

        doc.status = DocumentStatus.PURGED.value
        doc.purged_at = datetime.utcnow()
        doc.purge_status = DocumentPurgeStatus.PURGED.value
        doc.current_storage_object_id = None
        doc.updated_at = datetime.utcnow()
        self._db.commit()
        self._safe_audit_purged(doc, len(versions))

    def _safe_audit_blocked(self, doc: ElfisDocumentRecord, reason: str | None) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_document_purge_blocked(
                document_id=doc.id,
                organization_id=doc.organization_id,
                blocked_reason=reason,
            )
        except Exception:
            logger.debug("audit_purge_blocked_failed", exc_info=True)

    def _safe_audit_purged(self, doc: ElfisDocumentRecord, version_count: int) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_document_purged(
                document_id=doc.id,
                organization_id=doc.organization_id,
                document_type=doc.document_type,
                storage_object_count=version_count,
            )
        except Exception:
            logger.debug("audit_purged_failed", exc_info=True)

    def _safe_audit_purge_failed(self, doc: ElfisDocumentRecord, reason: str) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_document_purge_failed(
                document_id=doc.id,
                organization_id=doc.organization_id,
                reason=reason,
            )
        except Exception:
            logger.debug("audit_purge_failed_event", exc_info=True)
