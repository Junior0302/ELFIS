"""Validateurs pré-import — Validation & Mapping obligatoire."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.document_intake.enums import DocumentLifecycleStatus
from app.document_intake.models import ElfisDocumentIntakeItem
from app.import_engine.exceptions import ImportNotFoundError, ImportValidationError
from app.validation_mapping.enums import MatchResolution, ValidationSessionStatus
from app.validation_mapping.models import ElfisValidationMatch, ElfisValidationSession


ALLOWED_PRE_IMPORT_STATUSES = frozenset(
    {
        DocumentLifecycleStatus.READY_FOR_IMPORT.value,
        DocumentLifecycleStatus.IMPORT_PENDING.value,
        DocumentLifecycleStatus.IMPORT_FAILED.value,
        DocumentLifecycleStatus.ROLLBACK_COMPLETED.value,
    }
)


def get_intake_item(
    db: Session, *, organization_id: int, document_id: str
) -> ElfisDocumentIntakeItem:
    item = (
        db.query(ElfisDocumentIntakeItem)
        .filter(ElfisDocumentIntakeItem.id == document_id)
        .filter(ElfisDocumentIntakeItem.organization_id == organization_id)
        .first()
    )
    if not item:
        raise ImportNotFoundError("Document introuvable")
    return item


def get_ready_validation_session(
    db: Session, *, organization_id: int, document_id: str
) -> ElfisValidationSession:
    session = (
        db.query(ElfisValidationSession)
        .filter(ElfisValidationSession.organization_id == organization_id)
        .filter(ElfisValidationSession.document_intake_item_id == document_id)
        .filter(
            ElfisValidationSession.status
            == ValidationSessionStatus.READY_FOR_IMPORT.value
        )
        .order_by(ElfisValidationSession.updated_at.desc())
        .first()
    )
    if not session:
        raise ImportValidationError(
            "Aucune session Validation & Mapping en ready_for_import"
        )
    return session


def assert_document_importable(
    db: Session, *, organization_id: int, document_id: str
) -> tuple[ElfisDocumentIntakeItem, ElfisValidationSession]:
    item = get_intake_item(db, organization_id=organization_id, document_id=document_id)
    if item.lifecycle_status not in ALLOWED_PRE_IMPORT_STATUSES:
        raise ImportValidationError(
            f"Document non prêt à l'import (status={item.lifecycle_status})"
        )
    session = get_ready_validation_session(
        db, organization_id=organization_id, document_id=document_id
    )
    if not session.validated_data:
        raise ImportValidationError("Données validées absentes")
    # Matches non résolus bloquants (sauf ignore)
    matches = (
        db.query(ElfisValidationMatch)
        .filter(ElfisValidationMatch.validation_session_id == session.id)
        .all()
    )
    for m in matches:
        if m.resolution == MatchResolution.UNRESOLVED.value:
            raise ImportValidationError(
                f"Matching non résolu pour le rôle {m.party_role}"
            )
        if m.resolution == MatchResolution.USE_EXISTING.value and not m.contact_id:
            raise ImportValidationError(
                f"USE_EXISTING sans contact_id pour {m.party_role}"
            )
    return item, session
