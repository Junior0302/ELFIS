"""Tests Document Intake Engine V1."""

from __future__ import annotations

import pytest

from app.document_intake.enums import IntakeItemStatus
from app.document_intake.exceptions import DocumentIntakeQuotaError, DocumentIntakeValidationError
from app.document_intake.format_registry import list_formats
from app.document_intake.service import DocumentIntakeService
from app.document_intake.validators import detect_mime, validate_content
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.migration_center.enums import MigrationMode
from app.migration_center.service import MigrationCenterService
from tests.document_intake.conftest_helpers import (
    PDF_MINIMAL,
    PNG_MINIMAL,
    ZIP_MINIMAL,
    make_intake_db,
    seed_org_user,
)


def test_format_registry_contains_required_types():
    ids = {f["id"] for f in list_formats()}
    for required in ("pdf", "csv", "xls", "xlsx", "ods", "xml", "json", "zip", "jpeg", "png", "tiff", "txt"):
        assert required in ids


def test_validate_pdf_and_reject_empty_double_ext():
    ok = validate_content(filename="doc.pdf", content=PDF_MINIMAL, declared_mime="application/pdf")
    assert ok.format_id == "pdf"
    assert detect_mime(PDF_MINIMAL) == "application/pdf"
    with pytest.raises(DocumentIntakeValidationError) as e1:
        validate_content(filename="a.pdf", content=b"", declared_mime="application/pdf")
    assert e1.value.code == "empty_file"
    with pytest.raises(DocumentIntakeValidationError) as e2:
        validate_content(filename="evil.php.pdf", content=PDF_MINIMAL)
    assert e2.value.code == "double_extension"
    with pytest.raises(DocumentIntakeValidationError) as e3:
        validate_content(filename="nope.exe", content=b"MZ" + b"\x00" * 20)
    assert e3.value.code == "extension_not_allowed"


def test_ingest_hash_status_events_and_duplicate():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = DocumentIntakeService(db)
    a = svc.ingest_bytes(
        organization_id=org.id,
        filename="invoice.pdf",
        content=PDF_MINIMAL,
        actor_user_id=user.id,
        declared_mime="application/pdf",
    )
    assert a.checksum_sha256
    assert a.status == IntakeItemStatus.READY_FOR_ANALYSIS.value
    assert a.intake_token.startswith("din_")
    b = svc.ingest_bytes(
        organization_id=org.id,
        filename="invoice_copy.pdf",
        content=PDF_MINIMAL,
        actor_user_id=user.id,
    )
    assert b.is_duplicate is True
    assert b.status == IntakeItemStatus.DUPLICATE.value
    assert b.duplicate_of_id == a.id
    names = {e.event_name for e in db.query(ElfisEvent).all()}
    assert EventNames.DOCUMENT_UPLOADED in names
    assert EventNames.DOCUMENT_VALIDATED in names
    assert EventNames.DOCUMENT_READY_FOR_ANALYSIS in names
    assert EventNames.DOCUMENT_DUPLICATE_DETECTED in names
    db.close()


def test_zip_inventoried_not_extracted():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    row = DocumentIntakeService(db).ingest_bytes(
        organization_id=org.id,
        filename="pack.zip",
        content=ZIP_MINIMAL,
        actor_user_id=user.id,
        declared_mime="application/zip",
    )
    assert row.format_id == "zip"
    assert row.extract_later is True
    assert row.status == IntakeItemStatus.VALIDATED.value
    assert row.analysis_allowed is False
    db.close()


def test_folder_relative_path_preserved():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    batch_id, items, stats = DocumentIntakeService(db).ingest_batch(
        organization_id=org.id,
        files=[
            {
                "filename": "a.pdf",
                "content": PDF_MINIMAL,
                "relative_path": "exports/2024/a.pdf",
            },
            {
                "filename": "b.png",
                "content": PNG_MINIMAL,
                "relative_path": "exports/2024/images/b.png",
            },
        ],
        actor_user_id=user.id,
    )
    assert batch_id
    assert stats["accepted"] == 2
    paths = {i.relative_path for i in items}
    assert "exports/2024/a.pdf" in paths
    assert "exports/2024/images/b.png" in paths
    db.close()


def test_mime_mismatch_quarantine():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    # PDF extension but PNG content
    row = DocumentIntakeService(db).ingest_bytes(
        organization_id=org.id,
        filename="fake.pdf",
        content=PNG_MINIMAL,
        actor_user_id=user.id,
        declared_mime="application/pdf",
    )
    assert row.status == IntakeItemStatus.QUARANTINED.value
    assert row.quarantine_reason == "mime_mismatch"
    db.close()


def test_quota_batch_limit():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = DocumentIntakeService(db)
    files = [{"filename": f"f{i}.pdf", "content": PDF_MINIMAL} for i in range(101)]
    with pytest.raises(DocumentIntakeQuotaError) as exc:
        svc.ingest_batch(organization_id=org.id, files=files, actor_user_id=user.id)
    assert exc.value.code == "batch_file_limit"
    db.close()


def test_migration_session_isolation():
    factory, _ = make_intake_db()
    db = factory()
    org_a, user_a = seed_org_user(db, email="ia@t.local", name="A")
    org_b, _ = seed_org_user(db, email="ib@t.local", name="B")
    mig = MigrationCenterService(db).create_session(
        organization_id=org_a.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user_a.id,
    )
    svc = DocumentIntakeService(db)
    row = svc.ingest_bytes(
        organization_id=org_a.id,
        filename="x.pdf",
        content=PDF_MINIMAL,
        actor_user_id=user_a.id,
        migration_session_id=mig.id,
    )
    assert row.migration_session_id == mig.id
    items_b, total_b, _ = svc.list_items(organization_id=org_b.id)
    assert total_b == 0
    with pytest.raises(Exception):
        svc.get_for_org(row.id, org_b.id)
    db.close()


def test_cancel_and_inventory_states():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = DocumentIntakeService(db)
    row = svc.ingest_bytes(
        organization_id=org.id,
        filename="c.pdf",
        content=PDF_MINIMAL,
        actor_user_id=user.id,
    )
    cancelled = svc.cancel_item(row.id, org.id, actor_user_id=user.id)
    assert cancelled.status == IntakeItemStatus.CANCELLED.value
    _, _, summary = svc.list_items(organization_id=org.id)
    assert summary["count"] >= 1
    db.close()


def test_event_payload_no_file_content():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    DocumentIntakeService(db).ingest_bytes(
        organization_id=org.id,
        filename="safe.pdf",
        content=PDF_MINIMAL,
        actor_user_id=user.id,
    )
    for e in db.query(ElfisEvent).all():
        payload = e.payload or {}
        assert "content" not in payload
        assert "file_content" not in payload
        assert "checksum_sha256" in payload
        assert payload.get("schema_version") == 1
    db.close()
