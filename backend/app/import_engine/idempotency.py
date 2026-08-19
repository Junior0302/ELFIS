"""Idempotence Import Engine."""

from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from app.import_engine.exceptions import ImportIdempotencyError
from app.import_engine.models import ElfisImportFingerprint, ElfisImportRun


def build_fingerprint(
    *,
    organization_id: int,
    document_intake_item_id: str,
    validation_session_id: str,
    validation_version: int,
) -> str:
    raw = (
        f"{organization_id}|{document_intake_item_id}|"
        f"{validation_session_id}|{int(validation_version)}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_idempotency_key(fingerprint: str) -> str:
    return f"import:{fingerprint}"


def find_active_fingerprint(
    db: Session, *, organization_id: int, fingerprint: str
) -> ElfisImportFingerprint | None:
    return (
        db.query(ElfisImportFingerprint)
        .filter(ElfisImportFingerprint.organization_id == organization_id)
        .filter(ElfisImportFingerprint.fingerprint == fingerprint)
        .filter(ElfisImportFingerprint.is_active.is_(True))
        .first()
    )


def assert_not_already_imported(
    db: Session, *, organization_id: int, fingerprint: str
) -> None:
    existing = find_active_fingerprint(
        db, organization_id=organization_id, fingerprint=fingerprint
    )
    if existing:
        raise ImportIdempotencyError(
            f"Import déjà effectué (run={existing.import_run_id})"
        )


def register_fingerprint(
    db: Session,
    *,
    organization_id: int,
    fingerprint: str,
    document_intake_item_id: str,
    validation_session_id: str,
    validation_version: int,
    import_run_id: str,
) -> ElfisImportFingerprint:
    existing = (
        db.query(ElfisImportFingerprint)
        .filter(ElfisImportFingerprint.organization_id == organization_id)
        .filter(ElfisImportFingerprint.fingerprint == fingerprint)
        .first()
    )
    if existing:
        if existing.is_active:
            raise ImportIdempotencyError(
                f"Import déjà effectué (run={existing.import_run_id})"
            )
        # Rejeu après rollback — réactive la même empreinte
        existing.is_active = True
        existing.deactivated_at = None
        existing.import_run_id = import_run_id
        existing.document_intake_item_id = document_intake_item_id
        existing.validation_session_id = validation_session_id
        existing.validation_version = int(validation_version)
        db.add(existing)
        db.flush()
        return existing

    row = ElfisImportFingerprint(
        organization_id=organization_id,
        fingerprint=fingerprint,
        document_intake_item_id=document_intake_item_id,
        validation_session_id=validation_session_id,
        validation_version=int(validation_version),
        import_run_id=import_run_id,
        is_active=True,
    )
    db.add(row)
    db.flush()
    return row


def deactivate_fingerprint_for_run(db: Session, *, import_run_id: str) -> None:
    from datetime import datetime

    rows = (
        db.query(ElfisImportFingerprint)
        .filter(ElfisImportFingerprint.import_run_id == import_run_id)
        .filter(ElfisImportFingerprint.is_active.is_(True))
        .all()
    )
    now = datetime.utcnow()
    for row in rows:
        row.is_active = False
        row.deactivated_at = now
        db.add(row)


def get_completed_run_by_fingerprint(
    db: Session, *, organization_id: int, fingerprint: str
) -> ElfisImportRun | None:
    fp = find_active_fingerprint(
        db, organization_id=organization_id, fingerprint=fingerprint
    )
    if not fp:
        return None
    return (
        db.query(ElfisImportRun)
        .filter(ElfisImportRun.id == fp.import_run_id)
        .filter(ElfisImportRun.organization_id == organization_id)
        .first()
    )
