"""Tests Sprint 6 — Import Engine V1."""

from __future__ import annotations

from app.document_analysis.service import DocumentAnalysisService
from app.document_extraction.enums import ExtractionStatus
from app.document_extraction.service import DocumentExtractionService
from app.document_intake.enums import DocumentLifecycleStatus
from app.document_intake.service import DocumentIntakeService
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.import_engine.enums import ImportRunStatus
from app.import_engine.exceptions import (
    ImportIdempotencyError,
    ImportNotFoundError,
    ImportValidationError,
)
from app.import_engine.mapping import MappingEngine
from app.import_engine.models import ElfisImportAuditLog, ElfisImportFingerprint
from app.import_engine.service import ImportEngineService
from app.models import Invoice
from app.models_saas import Contact
from app.validation_mapping.enums import MatchResolution, ValidationSessionStatus
from app.validation_mapping.service import ValidationMappingService
from tests.document_intake.conftest_helpers import make_intake_db, seed_org_user


def _bootstrap():
    factory, _ = make_intake_db()
    from app.document_analysis import models as analysis_models  # noqa: F401
    from app.document_extraction import models as extr_models  # noqa: F401
    from app.validation_mapping import models as val_models  # noqa: F401
    from app.import_engine import models as imp_models  # noqa: F401
    from app.models import Invoice as Inv  # noqa: F401
    from app.models import BankAccount, BankTransaction  # noqa: F401
    from app.models_saas import Contact as C  # noqa: F401

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
        imp_models.ElfisImportRun.__table__,
        imp_models.ElfisImportFingerprint.__table__,
        imp_models.ElfisImportArtifact.__table__,
        imp_models.ElfisImportReport.__table__,
        imp_models.ElfisImportAuditLog.__table__,
        Inv.__table__,
        C.__table__,
        BankAccount.__table__,
        BankTransaction.__table__,
    ):
        tbl.create(bind=engine, checkfirst=True)
    org, user = seed_org_user(db)
    return db, org, user


def _invoice_bytes() -> bytes:
    return (
        b"Facture FA-2024-777 du 15/01/2024\n"
        b"Fournisseur ACME SARL SIRET 12345678900012\n"
        b"Total HT 100,00 TVA 20,00 Total TTC 120,00 EUR\n"
    )


def _ready_for_import(db, org, user, *, resolve_create=True):
    item = DocumentIntakeService(db).ingest_bytes(
        organization_id=org.id,
        filename="facture_imp.txt",
        content=_invoice_bytes(),
        actor_user_id=user.id,
        declared_mime="text/plain",
    )
    DocumentAnalysisService(db).analyze_item(item.id, org.id, actor_user_id=user.id)
    extr = DocumentExtractionService(db).start_extraction(
        item.id, org.id, actor_user_id=user.id
    )
    assert extr.status == ExtractionStatus.AWAITING_HUMAN_VALIDATION.value

    vsvc = ValidationMappingService(db)
    session = vsvc.start_or_get(item.id, org.id, actor_user_id=user.id)
    # Corriger les montants pour passer les contrôles Validation & Mapping
    for path, value in (
        ("amounts.subtotal_excluding_tax", "100.00"),
        ("amounts.total_tax", "20.00"),
        ("amounts.total_including_tax", "120.00"),
    ):
        try:
            vsvc.edit_field(
                session.id,
                org.id,
                field_path=path,
                new_value=value,
                actor_user_id=user.id,
                action="edit",
            )
        except Exception:
            pass
    for m in vsvc.get_matches(session.id, org.id):
        if m.resolution == MatchResolution.UNRESOLVED.value:
            resolution = (
                MatchResolution.CREATE_LATER.value
                if resolve_create
                else MatchResolution.IGNORE.value
            )
            vsvc.resolve_match(
                m.id,
                org.id,
                resolution=resolution,
                actor_user_id=user.id,
            )
    done = vsvc.validate_document(
        session.id, org.id, actor_user_id=user.id, mark_ready=True
    )
    assert done.status == ValidationSessionStatus.READY_FOR_IMPORT.value
    db.refresh(item)
    assert item.lifecycle_status == DocumentLifecycleStatus.READY_FOR_IMPORT.value
    return item, done


def test_mapping_invoice_schema():
    mapped = MappingEngine().map(
        schema_name="invoice.v1",
        validated_data={
            "document_number": "FA-1",
            "document_date": "2024-01-15",
            "supplier": {"name": "ACME", "siret": "12345678900012"},
            "amounts": {
                "subtotal_excluding_tax": "100",
                "total_tax": "20",
                "total_including_tax": "120",
            },
            "currency": "EUR",
        },
        filename="f.pdf",
    )
    assert mapped.kind == "invoice"
    assert mapped.invoice_fields["invoice_number"] == "FA-1"
    assert mapped.invoice_fields["amount_ttc"] == 120.0
    assert mapped.accounting_entry is not None
    assert "supplier" in mapped.contact_candidates


def test_import_transaction_complete_and_idempotent():
    db, org, user = _bootstrap()
    item, _ = _ready_for_import(db, org, user, resolve_create=True)
    svc = ImportEngineService(db)

    run = svc.import_document(
        organization_id=org.id, document_id=item.id, actor_user_id=user.id
    )
    assert run.status == ImportRunStatus.COMPLETED.value
    assert run.created_objects_json
    assert any(o.get("kind") == "invoice" for o in run.created_objects_json)
    assert any(o.get("kind") == "contact" for o in run.created_objects_json)

    db.refresh(item)
    assert item.lifecycle_status == DocumentLifecycleStatus.IMPORT_COMPLETED.value

    invs = db.query(Invoice).filter(Invoice.organization_id == org.id).all()
    assert len(invs) == 1
    contacts = db.query(Contact).filter(Contact.organization_id == org.id).all()
    assert len(contacts) >= 1

    try:
        svc.import_document(
            organization_id=org.id, document_id=item.id, actor_user_id=user.id
        )
        assert False, "doit lever ImportIdempotencyError"
    except ImportIdempotencyError:
        pass

    names = {e.event_name for e in db.query(ElfisEvent).all()}
    assert EventNames.IMPORT_STARTED in names
    assert EventNames.IMPORT_MAPPING_COMPLETED in names
    assert EventNames.IMPORT_TRANSACTION_STARTED in names
    assert EventNames.IMPORT_TRANSACTION_COMMITTED in names
    assert EventNames.IMPORT_COMPLETED in names

    audits = (
        db.query(ElfisImportAuditLog)
        .filter(ElfisImportAuditLog.import_run_id == run.id)
        .all()
    )
    assert any(a.action == "import_completed" for a in audits)
    assert any(a.action == "entity_created" for a in audits)

    report = svc.get_report(organization_id=org.id, import_id=run.id)
    assert report.version == 1
    assert report.duration_ms is not None
    db.close()


def test_rollback_and_reimport():
    db, org, user = _bootstrap()
    item, _ = _ready_for_import(db, org, user, resolve_create=True)
    svc = ImportEngineService(db)
    run = svc.import_document(
        organization_id=org.id, document_id=item.id, actor_user_id=user.id
    )
    assert db.query(Invoice).count() == 1

    rolled = svc.rollback_import(
        organization_id=org.id,
        import_id=run.id,
        actor_user_id=user.id,
        reason="manual",
    )
    assert rolled.status == ImportRunStatus.ROLLBACK_COMPLETED.value
    assert db.query(Invoice).count() == 0
    fp = (
        db.query(ElfisImportFingerprint)
        .filter(ElfisImportFingerprint.import_run_id == run.id)
        .first()
    )
    assert fp is not None and fp.is_active is False

    db.refresh(item)
    assert item.lifecycle_status == DocumentLifecycleStatus.ROLLBACK_COMPLETED.value

    names = {e.event_name for e in db.query(ElfisEvent).all()}
    assert EventNames.IMPORT_ROLLBACK_STARTED in names
    assert EventNames.IMPORT_ROLLBACK_COMPLETED in names

    run2 = svc.import_document(
        organization_id=org.id, document_id=item.id, actor_user_id=user.id
    )
    assert run2.status == ImportRunStatus.COMPLETED.value
    assert db.query(Invoice).count() == 1
    db.close()


def test_link_existing_contact():
    db, org, user = _bootstrap()
    contact = Contact(
        organization_id=org.id,
        contact_type="supplier",
        company_name="ACME SARL",
        siret="12345678900012",
        siren="123456789",
        source="manual",
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)

    item = DocumentIntakeService(db).ingest_bytes(
        organization_id=org.id,
        filename="facture_link.txt",
        content=_invoice_bytes(),
        actor_user_id=user.id,
        declared_mime="text/plain",
    )
    DocumentAnalysisService(db).analyze_item(item.id, org.id, actor_user_id=user.id)
    DocumentExtractionService(db).start_extraction(item.id, org.id, actor_user_id=user.id)
    vsvc = ValidationMappingService(db)
    session = vsvc.start_or_get(item.id, org.id, actor_user_id=user.id)
    for path, value in (
        ("amounts.subtotal_excluding_tax", "100.00"),
        ("amounts.total_tax", "20.00"),
        ("amounts.total_including_tax", "120.00"),
    ):
        try:
            vsvc.edit_field(
                session.id,
                org.id,
                field_path=path,
                new_value=value,
                actor_user_id=user.id,
                action="edit",
            )
        except Exception:
            pass
    for m in vsvc.get_matches(session.id, org.id):
        if m.resolution == MatchResolution.UNRESOLVED.value:
            m.contact_id = contact.id
            db.add(m)
            db.commit()
            vsvc.resolve_match(
                m.id,
                org.id,
                resolution=MatchResolution.USE_EXISTING.value,
                actor_user_id=user.id,
            )
    vsvc.validate_document(session.id, org.id, actor_user_id=user.id, mark_ready=True)

    run = ImportEngineService(db).import_document(
        organization_id=org.id, document_id=item.id, actor_user_id=user.id
    )
    assert run.status == ImportRunStatus.COMPLETED.value
    assert any(o.get("resolution") == "use_existing" for o in (run.linked_objects_json or []))
    inv = db.query(Invoice).filter(Invoice.organization_id == org.id).one()
    assert inv.supplier_contact_id == contact.id
    assert db.query(Contact).filter(Contact.organization_id == org.id).count() == 1
    db.close()


def test_reject_non_validated_and_cross_tenant():
    db, org, user = _bootstrap()
    org2, _ = seed_org_user(db, email="imp2@test.local", name="OtherOrg")
    item = DocumentIntakeService(db).ingest_bytes(
        organization_id=org.id,
        filename="raw.txt",
        content=_invoice_bytes(),
        actor_user_id=user.id,
        declared_mime="text/plain",
    )
    svc = ImportEngineService(db)
    try:
        svc.import_document(
            organization_id=org.id, document_id=item.id, actor_user_id=user.id
        )
        assert False
    except ImportValidationError:
        pass

    item2, _ = _ready_for_import(db, org, user, resolve_create=False)
    run = svc.import_document(
        organization_id=org.id, document_id=item2.id, actor_user_id=user.id
    )
    try:
        svc.get_import(organization_id=org2.id, import_id=run.id)
        assert False
    except ImportNotFoundError:
        pass
    db.close()


def test_permissions_catalog():
    from app.import_engine.permissions import IMPORT_PERMISSIONS
    from app.iam.permission_catalog import Permission

    for p in IMPORT_PERMISSIONS:
        assert Permission(p).value == p
