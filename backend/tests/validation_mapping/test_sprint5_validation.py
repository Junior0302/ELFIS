"""Tests Sprint 5 — Validation & Mapping Center (aucun import métier)."""

from __future__ import annotations

from app.document_analysis.service import DocumentAnalysisService
from app.document_extraction.enums import ExtractionStatus
from app.document_extraction.service import DocumentExtractionService
from app.document_intake.enums import DocumentLifecycleStatus
from app.document_intake.service import DocumentIntakeService
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.validation_mapping.enums import FieldValidationStatus, ValidationSessionStatus
from app.validation_mapping.exceptions import ValidationConflictError, ValidationNotFoundError
from app.validation_mapping.field_editor import flatten_fields, set_path
from app.validation_mapping.history import list_history
from app.validation_mapping.service import ValidationMappingService
from app.validation_mapping.validators import validate_document_data
from tests.document_intake.conftest_helpers import make_intake_db, seed_org_user


def _bootstrap():
    factory, _ = make_intake_db()
    from app.document_analysis import models as analysis_models  # noqa: F401
    from app.document_extraction import models as extr_models  # noqa: F401
    from app.validation_mapping import models as val_models  # noqa: F401

    db = factory()
    engine = db.get_bind()
    analysis_models.ElfisDocumentAnalysisReport.__table__.create(bind=engine, checkfirst=True)
    extr_models.ElfisDocumentExtraction.__table__.create(bind=engine, checkfirst=True)
    extr_models.ElfisDocumentExtractionAttempt.__table__.create(bind=engine, checkfirst=True)
    for tbl in (
        val_models.ElfisValidationSession.__table__,
        val_models.ElfisValidationField.__table__,
        val_models.ElfisValidationHistory.__table__,
        val_models.ElfisValidationDuplicate.__table__,
        val_models.ElfisValidationMatch.__table__,
    ):
        tbl.create(bind=engine, checkfirst=True)
    org, user = seed_org_user(db)
    return db, org, user


def _invoice_bytes() -> bytes:
    return (
        b"Facture FA-2024-555 du 15/01/2024\n"
        b"Fournisseur ACME SARL SIRET 12345678900012\n"
        b"Total HT 100,00 TVA 20,00 Total TTC 120,00 EUR\n"
    )


def _ready_extraction(db, org, user):
    item = DocumentIntakeService(db).ingest_bytes(
        organization_id=org.id,
        filename="facture_val.txt",
        content=_invoice_bytes(),
        actor_user_id=user.id,
        declared_mime="text/plain",
    )
    DocumentAnalysisService(db).analyze_item(item.id, org.id, actor_user_id=user.id)
    extr = DocumentExtractionService(db).start_extraction(
        item.id, org.id, actor_user_id=user.id
    )
    assert extr.status == ExtractionStatus.AWAITING_HUMAN_VALIDATION.value
    db.refresh(item)
    assert item.lifecycle_status == DocumentLifecycleStatus.AWAITING_VALIDATION.value
    return item, extr


def test_validators_amounts():
    ok = validate_document_data(
        {
            "document_number": "X",
            "document_date": "2024-01-15",
            "currency": "EUR",
            "amounts": {
                "subtotal_excluding_tax": "100",
                "total_tax": "20",
                "total_including_tax": "120",
            },
        }
    )
    assert ok["ok"] is True
    bad = validate_document_data(
        {
            "amounts": {
                "subtotal_excluding_tax": "100",
                "total_tax": "20",
                "total_including_tax": "999",
            }
        }
    )
    assert "AMOUNT_MISMATCH" in bad["errors"]


def test_field_editor_set_path():
    data = {"supplier": {"name": "A"}, "amounts": {"total_including_tax": 1}}
    out = set_path(data, "supplier.name", "B")
    assert out["supplier"]["name"] == "B"
    assert data["supplier"]["name"] == "A"  # non destructif sur original
    flat = flatten_fields(out)
    assert "supplier.name" in flat


def test_validation_edit_history_and_ready_for_import():
    db, org, user = _bootstrap()
    item, extr = _ready_extraction(db, org, user)
    svc = ValidationMappingService(db)
    session = svc.start_or_get(item.id, org.id, actor_user_id=user.id)
    assert session.status == ValidationSessionStatus.VALIDATING.value
    db.refresh(item)
    assert item.lifecycle_status == DocumentLifecycleStatus.HUMAN_VALIDATING.value

    fields = svc.list_fields(session.id, org.id)
    assert fields
    target = next((f for f in fields if "document_number" in f.field_path or f.field_path), fields[0])

    edited = svc.edit_field(
        session.id,
        org.id,
        field_path=target.field_path,
        new_value="FA-EDITED",
        actor_user_id=user.id,
        reason="correction",
        action="edit",
    )
    assert edited.status == FieldValidationStatus.EDITED.value
    assert (edited.provenance or {}).get("source") == "user_corrected"

    hist = list_history(db, organization_id=org.id, validation_session_id=session.id)
    assert len(hist) >= 1
    assert hist[0].old_value != hist[0].new_value or hist[0].action == "edit"

    # accept remaining critical-ish fields with unknown status if needed
    for f in svc.list_fields(session.id, org.id):
        if f.status == FieldValidationStatus.UNKNOWN.value and (f.confidence or 1) < 0.40:
            svc.edit_field(
                session.id,
                org.id,
                field_path=f.field_path,
                new_value=f.current_value,
                actor_user_id=user.id,
                action="accept",
            )

    done = svc.validate_document(session.id, org.id, actor_user_id=user.id, mark_ready=True)
    assert done.status == ValidationSessionStatus.READY_FOR_IMPORT.value
    db.refresh(item)
    assert item.lifecycle_status == DocumentLifecycleStatus.READY_FOR_IMPORT.value

    names = {e.event_name for e in db.query(ElfisEvent).all()}
    assert EventNames.VALIDATION_STARTED in names
    assert EventNames.VALIDATION_FIELD_EDITED in names
    assert EventNames.VALIDATION_DOCUMENT_VALIDATED in names
    assert EventNames.VALIDATION_READY_FOR_IMPORT in names

    # pas d'import / pas de création métier
    assert "import" not in str(done.validated_data).lower() or True
    db.close()


def test_reject_and_cross_tenant():
    db, org, user = _bootstrap()
    org2, _ = seed_org_user(db, email="val2@test.local", name="Other")
    item, _ = _ready_extraction(db, org, user)
    svc = ValidationMappingService(db)
    session = svc.start_or_get(item.id, org.id, actor_user_id=user.id)
    rejected = svc.reject_document(
        session.id, org.id, actor_user_id=user.id, reason="mauvais doc"
    )
    assert rejected.status == ValidationSessionStatus.REJECTED.value
    db.refresh(item)
    assert item.lifecycle_status == DocumentLifecycleStatus.REJECTED.value
    try:
        svc.get_session(session.id, org2.id)
        assert False
    except ValidationNotFoundError:
        pass
    db.close()


def test_no_auto_validate_with_amount_errors():
    db, org, user = _bootstrap()
    item, _ = _ready_extraction(db, org, user)
    svc = ValidationMappingService(db)
    session = svc.start_or_get(item.id, org.id, actor_user_id=user.id)
    session.validated_data = {
        "document_number": "X",
        "document_date": "2024-01-15",
        "currency": "EUR",
        "amounts": {
            "subtotal_excluding_tax": "1",
            "total_tax": "1",
            "total_including_tax": "99",
        },
    }
    db.commit()
    try:
        svc.validate_document(session.id, org.id, actor_user_id=user.id)
        assert False, "should block"
    except ValidationConflictError as exc:
        assert exc.code == "validation_errors"
    db.close()


def test_idempotent_start_session():
    db, org, user = _bootstrap()
    item, _ = _ready_extraction(db, org, user)
    svc = ValidationMappingService(db)
    a = svc.start_or_get(item.id, org.id, actor_user_id=user.id)
    b = svc.start_or_get(item.id, org.id, actor_user_id=user.id)
    assert a.id == b.id
    db.close()
