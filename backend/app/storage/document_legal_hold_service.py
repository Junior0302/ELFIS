"""Legal hold — gel anti-purge."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.storage.storage_exceptions import DocumentAccessDeniedError, StorageValidationError
from app.storage.storage_metadata import sanitize_document_metadata
from app.storage.storage_models import ElfisDocumentLegalHold
from app.storage.storage_repository import DocumentRepository, LegalHoldRepository

logger = logging.getLogger(__name__)


class DocumentLegalHoldService:
    def __init__(self, db: Session, *, audit_logger: Any | None = None) -> None:
        self._db = db
        self._docs = DocumentRepository(db)
        self._holds = LegalHoldRepository(db)
        self._audit = audit_logger

    def place(
        self,
        *,
        document_id: str,
        organization_id: int,
        reason: str,
        reference: str | None = None,
        placed_by_user_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ElfisDocumentLegalHold:
        doc = self._docs.get(document_id)
        if not doc or doc.organization_id != organization_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        cleaned = (reason or "").strip()
        if len(cleaned) < 3:
            raise StorageValidationError("reason_required", "Raison de legal hold obligatoire")
        hold = ElfisDocumentLegalHold(
            id=str(uuid4()),
            document_id=document_id,
            reason=cleaned[:500],
            reference=(reference or "")[:255] or None,
            active=True,
            placed_by_user_id=placed_by_user_id,
            metadata_json=sanitize_document_metadata(metadata),
        )
        self._holds.create(hold, commit=True)
        self._safe_placed(hold, organization_id)
        return hold

    def release(
        self,
        *,
        document_id: str,
        hold_id: str,
        organization_id: int,
        released_by_user_id: int | None = None,
    ) -> ElfisDocumentLegalHold:
        doc = self._docs.get(document_id)
        if not doc or doc.organization_id != organization_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        hold = self._holds.get(hold_id)
        if not hold or hold.document_id != document_id:
            raise DocumentAccessDeniedError("hold_not_found", "Legal hold introuvable")
        if not hold.active:
            return hold  # idempotent
        hold.active = False
        hold.released_at = datetime.utcnow()
        hold.released_by_user_id = released_by_user_id
        self._db.commit()
        self._db.refresh(hold)
        self._safe_released(hold, organization_id)
        return hold

    def list_holds(
        self, document_id: str, organization_id: int, *, active_only: bool = False
    ) -> list[ElfisDocumentLegalHold]:
        doc = self._docs.get(document_id)
        if not doc or doc.organization_id != organization_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        return self._holds.list_for_document(document_id, active_only=active_only)

    def _safe_placed(self, hold: ElfisDocumentLegalHold, organization_id: int) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_document_legal_hold_placed(
                document_id=hold.document_id,
                legal_hold_id=hold.id,
                organization_id=organization_id,
                actor_user_id=hold.placed_by_user_id,
                reason=hold.reason[:120],
            )
        except Exception:
            logger.debug("audit_hold_placed_failed", exc_info=True)

    def _safe_released(self, hold: ElfisDocumentLegalHold, organization_id: int) -> None:
        if not self._audit:
            return
        try:
            self._audit.record_document_legal_hold_released(
                document_id=hold.document_id,
                legal_hold_id=hold.id,
                organization_id=organization_id,
                actor_user_id=hold.released_by_user_id,
            )
        except Exception:
            logger.debug("audit_hold_released_failed", exc_info=True)
