"""DocumentLifecycleService — machine à états centralisée."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.audit.audit_logger import AuditLogger
from app.audit.audit_types import AuditCategory, AuditStatus, Severity
from app.document_intake.enums import (
    LIFECYCLE_TRANSITIONS,
    DocumentLifecycleStatus,
    LifecycleActorType,
)
from app.document_intake.events import publish_intake_event
from app.document_intake.exceptions import DocumentIntakeConflictError, DocumentIntakeNotFoundError
from app.document_intake.models import ElfisDocumentIntakeItem, ElfisDocumentLifecycleEntry

logger = logging.getLogger(__name__)

_SENSITIVE_TO = frozenset(
    {
        DocumentLifecycleStatus.QUARANTINED.value,
        DocumentLifecycleStatus.REJECTED.value,
        DocumentLifecycleStatus.FAILED.value,
        DocumentLifecycleStatus.CANCELLED.value,
    }
)


class DocumentLifecycleService:
    def __init__(self, db: Session, *, audit: AuditLogger | None = None) -> None:
        self._db = db
        self._audit = audit or AuditLogger(db)

    def can_transition(self, from_status: str, to_status: str) -> bool:
        allowed = LIFECYCLE_TRANSITIONS.get(from_status, frozenset())
        return to_status in allowed

    def get_allowed_transitions(self, from_status: str) -> list[str]:
        return sorted(LIFECYCLE_TRANSITIONS.get(from_status, frozenset()))

    def transition(
        self,
        item: ElfisDocumentIntakeItem,
        to_status: str,
        *,
        organization_id: int,
        reason_code: str | None = None,
        actor_type: str = LifecycleActorType.SYSTEM.value,
        actor_user_id: int | None = None,
        metadata: dict[str, Any] | None = None,
        commit: bool = False,
        expected_version: int | None = None,
    ) -> ElfisDocumentIntakeItem:
        if item.organization_id != organization_id:
            raise DocumentIntakeNotFoundError("not_found", "Fichier introuvable")

        current = item.lifecycle_status or item.status
        # Idempotence : déjà dans l'état cible
        if current == to_status:
            return item

        if not self.can_transition(current, to_status):
            raise DocumentIntakeConflictError(
                "invalid_lifecycle_transition",
                f"Transition interdite: {current} -> {to_status}",
            )

        if expected_version is not None and int(item.version or 1) != expected_version:
            raise DocumentIntakeConflictError(
                "version_conflict",
                "Conflit de version optimiste",
            )

        from_status = current
        now = datetime.utcnow()
        item.status = to_status
        item.lifecycle_status = to_status
        item.last_activity_at = now
        item.version = int(item.version or 1) + 1
        item.updated_at = now
        if to_status in (
            DocumentLifecycleStatus.VALIDATED.value,
            DocumentLifecycleStatus.READY_FOR_ANALYSIS.value,
            DocumentLifecycleStatus.DUPLICATE.value,
        ):
            item.validated_at = item.validated_at or now
        if to_status == DocumentLifecycleStatus.QUARANTINED.value:
            item.analysis_allowed = False
        if to_status == DocumentLifecycleStatus.READY_FOR_ANALYSIS.value:
            # Préparation uniquement — pas d'OCR/IA
            item.analysis_allowed = False

        entry = ElfisDocumentLifecycleEntry(
            id=str(uuid4()),
            organization_id=organization_id,
            document_intake_item_id=item.id,
            from_status=from_status,
            to_status=to_status,
            reason_code=(reason_code or "")[:64] or None,
            actor_type=actor_type,
            actor_user_id=actor_user_id,
            metadata_json=dict(metadata or {}),
            occurred_at=now,
            created_at=now,
        )
        self._db.add(entry)
        self._db.flush()

        publish_intake_event(
            self._db,
            event_type="document.lifecycle.changed",
            item=item,
            actor_user_id=actor_user_id,
            metadata={
                "from_status": from_status,
                "to_status": to_status,
                "reason_code": reason_code,
                **(metadata or {}),
            },
            idempotency_key=f"document:lifecycle:{item.id}:{from_status}:{to_status}:{item.version}",
            commit=False,
        )

        if to_status in _SENSITIVE_TO:
            try:
                self._audit.service.record(
                    f"document_intake.lifecycle.{to_status}",
                    severity=Severity.WARNING if to_status != DocumentLifecycleStatus.CANCELLED.value else Severity.INFO,
                    category=AuditCategory.DOCUMENT,
                    status=AuditStatus.SUCCESS,
                    success=True,
                    message=f"Lifecycle {from_status} → {to_status}",
                    actor_user_id=actor_user_id,
                    organization_id=organization_id,
                    service="document_intake",
                    product="elfis-core",
                    target_type="document_intake_item",
                    target_id=item.id,
                    metadata={
                        "universal_document_id": item.universal_document_id,
                        "from_status": from_status,
                        "to_status": to_status,
                        "reason_code": reason_code,
                    },
                )
            except Exception:
                logger.exception("lifecycle_audit_failed")

        logger.info(
            "document_lifecycle_transition",
            extra={
                "organization_id": organization_id,
                "document_intake_item_id": item.id,
                "universal_document_id": item.universal_document_id,
                "from_status": from_status,
                "to_status": to_status,
                "operation": "lifecycle_transition",
                "result": "ok",
            },
        )

        if commit:
            self._db.commit()
            self._db.refresh(item)
        return item

    def mark_validating(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.VALIDATING.value, **kw)

    def mark_validated(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.VALIDATED.value, **kw)

    def mark_duplicate(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.DUPLICATE.value, **kw)

    def mark_quarantined(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.QUARANTINED.value, **kw)

    def mark_ready_for_analysis(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.READY_FOR_ANALYSIS.value, **kw)

    def mark_analysis_pending(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.ANALYSIS_PENDING.value, **kw)

    def mark_analyzing(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.ANALYZING.value, **kw)

    def mark_classified(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.CLASSIFIED.value, **kw)

    def mark_ready_for_ai(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.READY_FOR_AI.value, **kw)

    def mark_ocr_pending(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.OCR_PENDING.value, **kw)

    def mark_extraction_pending(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.EXTRACTION_PENDING.value, **kw)

    def mark_extracting(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.EXTRACTING.value, **kw)

    def mark_extracted(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.EXTRACTED.value, **kw)

    def mark_awaiting_validation(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.AWAITING_VALIDATION.value, **kw)

    def mark_human_validating(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.HUMAN_VALIDATING.value, **kw)

    def mark_validated_by_user(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.VALIDATED_BY_USER.value, **kw)

    def mark_ready_for_import(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.READY_FOR_IMPORT.value, **kw)

    def mark_import_pending(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.IMPORT_PENDING.value, **kw)

    def mark_importing(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.IMPORTING.value, **kw)

    def mark_import_completed(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.IMPORT_COMPLETED.value, **kw)

    def mark_imported(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        """Alias historique — délègue à import_completed."""
        return self.mark_import_completed(item, **kw)

    def mark_import_failed(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.IMPORT_FAILED.value, **kw)

    def mark_rollback_completed(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.ROLLBACK_COMPLETED.value, **kw)

    def mark_import_cancelled(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.IMPORT_CANCELLED.value, **kw)

    def mark_rejected(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.REJECTED.value, **kw)

    def mark_failed(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.FAILED.value, **kw)

    def cancel(self, item: ElfisDocumentIntakeItem, **kw: Any) -> ElfisDocumentIntakeItem:
        return self.transition(item, DocumentLifecycleStatus.CANCELLED.value, **kw)

    def list_entries(
        self, *, organization_id: int, document_intake_item_id: str
    ) -> list[ElfisDocumentLifecycleEntry]:
        return (
            self._db.query(ElfisDocumentLifecycleEntry)
            .filter(ElfisDocumentLifecycleEntry.organization_id == organization_id)
            .filter(ElfisDocumentLifecycleEntry.document_intake_item_id == document_intake_item_id)
            .order_by(ElfisDocumentLifecycleEntry.occurred_at.asc())
            .all()
        )
