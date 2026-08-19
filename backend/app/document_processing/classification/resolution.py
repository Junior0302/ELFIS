"""Résolution du type effectif + sync DocumentRecord."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.document_processing.classification.models import ElfisDocumentClassification
from app.document_processing.classification.scoring import ClassificationScoringPolicy
from app.document_processing.classification.taxonomy import get_document_type_registry
from app.document_processing.classification.types import ClassificationStatus, TYPE_INVOICE
from app.storage.storage_models import ElfisDocumentRecord

logger = logging.getLogger(__name__)


class DocumentTypeResolutionService:
    def __init__(self, db: Session, *, audit_logger: Any | None = None) -> None:
        self._db = db
        self._audit = audit_logger
        self._scoring = ClassificationScoringPolicy.from_settings()
        self._registry = get_document_type_registry()

    def effective_type(self, row: ElfisDocumentClassification) -> str | None:
        if row.confirmed_type:
            return row.confirmed_type
        if row.status == ClassificationStatus.REJECTED.value:
            return None
        if row.status in (
            ClassificationStatus.PROPOSED.value,
            ClassificationStatus.CONFIRMED.value,
        ):
            # predicted autorisé seulement si politique / score
            if row.requires_review and not row.confirmed_type:
                # tant que revue requise, effective = confirmed only
                if not getattr(settings, "document_classification_auto_confirm", False):
                    return row.confirmed_type
            return row.predicted_type
        return None

    def maybe_sync_document_type(
        self,
        row: ElfisDocumentClassification,
        *,
        force: bool = False,
    ) -> bool:
        """Met à jour DocumentRecord.document_type si règle autorisée."""
        doc = self._db.get(ElfisDocumentRecord, row.document_id)
        if not doc or doc.organization_id != row.organization_id:
            return False

        target: str | None = None
        if row.confirmed_type and self._registry.is_known(row.confirmed_type):
            target = row.confirmed_type
        elif force:
            return False
        elif (
            not row.requires_review
            and row.predicted_type
            and row.predicted_type not in ("unknown", TYPE_INVOICE)
            and float(row.confidence_score or 0) >= self._scoring.confirm_threshold
            and self._registry.is_known(row.predicted_type)
            and getattr(settings, "document_classification_auto_confirm", False)
        ):
            target = row.predicted_type

        if not target or doc.document_type == target:
            return False

        previous = doc.document_type
        doc.document_type = target
        self._db.commit()
        if self._audit:
            try:
                self._audit.record_document_type_effective_updated(
                    classification_id=row.id,
                    document_id=row.document_id,
                    version_id=row.document_version_id,
                    organization_id=row.organization_id,
                    predicted_type=row.predicted_type,
                    confirmed_type=row.confirmed_type or target,
                )
            except Exception:
                logger.debug("type_effective_audit_failed", exc_info=True)
        logger.info(
            "document_type_effective_updated",
            extra={"document_id": doc.id, "from": previous, "to": target},
        )
        return True
