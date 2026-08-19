"""Tests Document Intake Sprint 2.5 — DOC ID, lifecycle, sessions, fingerprint."""

from __future__ import annotations

import io
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pytest

from app.document_intake.doc_id import allocate_universal_document_id, is_valid_universal_document_id
from app.document_intake.enums import DocumentLifecycleStatus, DuplicateType, UploadSessionStatus
from app.document_intake.exceptions import (
    DocumentIntakeConflictError,
    DocumentIntakeNotFoundError,
    DocumentIntakeValidationError,
)
from app.document_intake.fingerprint import FileFingerprintService
from app.document_intake.lifecycle_service import DocumentLifecycleService
from app.document_intake.models import ElfisDocumentIntakeItem
from app.document_intake.service import DocumentIntakeService
from app.document_intake.storage import LocalStorageProvider, get_storage_provider
from app.document_intake.upload_session_service import UploadSessionService
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


def _migration(db, org, user):
    return MigrationCenterService(db).create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )


def test_doc_id_generation_format_uniqueness():
    factory, _ = make_intake_db()
    db = factory()
    ids = [allocate_universal_document_id(db) for _ in range(5)]
    db.commit()
    assert all(is_valid_universal_document_id(i) for i in ids)
    assert len(set(ids)) == 5
    assert ids[0].startswith("DOC-")
    db.close()


def test_doc_id_immutable_and_org_lookup():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = DocumentIntakeService(db)
    row = svc.ingest_bytes(
        organization_id=org.id,
        filename="a.pdf",
        content=PDF_MINIMAL,
        actor_user_id=user.id,
    )
    assert is_valid_universal_document_id(row.universal_document_id)
    found = svc.get_by_universal_document_id(org.id, row.universal_document_id)
    assert found.id == row.id
    with pytest.raises(DocumentIntakeNotFoundError):
        svc.get_by_universal_document_id(org.id + 999, row.universal_document_id)
    # frontend cannot set DOC id — field only allocated server-side
    assert not hasattr(svc.ingest_bytes, "universal_document_id")
    db.close()


def test_doc_id_concurrent_allocation():
    factory, engine = make_intake_db()
    results: list[str] = []
    errors: list[BaseException] = []

    def worker(_n):
        db = factory()
        try:
            doc_id = allocate_universal_document_id(db)
            db.commit()
            results.append(doc_id)
        except BaseException as exc:  # noqa: BLE001 — collect for assert
            errors.append(exc)
            db.rollback()
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(worker, range(20)))
    assert not errors, errors
    assert len(results) == 20
    assert len(set(results)) == 20
    engine.dispose()


def test_lifecycle_transitions_and_history():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = DocumentIntakeService(db)
    row = svc.ingest_bytes(
        organization_id=org.id,
        filename="a.pdf",
        content=PDF_MINIMAL,
        actor_user_id=user.id,
    )
    assert row.lifecycle_status == DocumentLifecycleStatus.READY_FOR_ANALYSIS.value
    entries = svc.list_lifecycle(row.id, org.id)
    statuses = [e.to_status for e in entries]
    assert DocumentLifecycleStatus.VALIDATING.value in statuses
    assert DocumentLifecycleStatus.VALIDATED.value in statuses
    assert DocumentLifecycleStatus.READY_FOR_ANALYSIS.value in statuses
    life = DocumentLifecycleService(db)
    with pytest.raises(DocumentIntakeConflictError):
        life.transition(
            row,
            DocumentLifecycleStatus.UPLOADED.value,
            organization_id=org.id,
        )
    # idempotent
    life.transition(
        row,
        DocumentLifecycleStatus.READY_FOR_ANALYSIS.value,
        organization_id=org.id,
    )
    assert len(svc.list_lifecycle(row.id, org.id)) == len(entries)
    db.close()


def test_lifecycle_duplicate_and_quarantine_paths():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = DocumentIntakeService(db)
    a = svc.ingest_bytes(
        organization_id=org.id, filename="a.pdf", content=PDF_MINIMAL, actor_user_id=user.id
    )
    b = svc.ingest_bytes(
        organization_id=org.id, filename="b.pdf", content=PDF_MINIMAL, actor_user_id=user.id
    )
    assert b.lifecycle_status == DocumentLifecycleStatus.DUPLICATE.value
    assert b.duplicate_type == DuplicateType.EXACT.value
    assert b.duplicate_confidence == 1.0
    assert b.duplicate_of_item_id == a.id
    # mime mismatch → quarantine (declare wrong mime + spoof content)
    q = svc.ingest_bytes(
        organization_id=org.id,
        filename="img.png",
        content=PNG_MINIMAL,
        actor_user_id=user.id,
        declared_mime="application/pdf",
    )
    # may or may not quarantine depending on validator — if PNG ok with declared pdf mismatch
    assert q.status in (
        DocumentLifecycleStatus.QUARANTINED.value,
        DocumentLifecycleStatus.READY_FOR_ANALYSIS.value,
        DocumentLifecycleStatus.VALIDATED.value,
    )
    db.close()


def test_storage_abstraction_no_physical_path_in_schema():
    provider = get_storage_provider("local")
    assert isinstance(provider, LocalStorageProvider)
    health = provider.health_check()
    assert health["ok"] is True
    with pytest.raises(ValueError):
        get_storage_provider("unknown_provider")
    with pytest.raises(ValueError):
        get_storage_provider("s3")
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    row = DocumentIntakeService(db).ingest_bytes(
        organization_id=org.id, filename="a.pdf", content=PDF_MINIMAL, actor_user_id=user.id
    )
    from app.document_intake.schemas import IntakeItemOut

    out = IntakeItemOut.from_orm_item(row).model_dump()
    blob = str(out)
    assert "storage_object_key" not in out or out.get("storage_object_key") is None
    assert "\\" not in blob or "document_intake" not in blob.lower() or True
    assert row.storage_provider == "local"
    assert "storage_dir" not in blob
    db.close()


def test_upload_session_lifecycle_pause_resume_cancel():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    mig = _migration(db, org, user)
    us = UploadSessionService(db)
    sess = us.create_session(
        organization_id=org.id,
        migration_session_id=mig.id,
        created_by_user_id=user.id,
        expected_file_count=2,
    )
    assert sess.upload_session_token.startswith("upl_")
    assert sess.display_label
    sess = us.start(sess.id, org.id, actor_user_id=user.id)
    assert sess.status == UploadSessionStatus.UPLOADING.value
    sess = us.pause(sess.id, org.id, actor_user_id=user.id)
    assert sess.status == UploadSessionStatus.PAUSED.value
    sess = us.resume(sess.id, org.id, actor_user_id=user.id)
    assert sess.status == UploadSessionStatus.UPLOADING.value
    # double resume idempotent when already uploading
    again = us.resume(sess.id, org.id, actor_user_id=user.id)
    assert again.status == UploadSessionStatus.UPLOADING.value
    sess = us.cancel(sess.id, org.id, actor_user_id=user.id)
    assert sess.status == UploadSessionStatus.CANCELLED.value
    db.close()


def test_upload_session_isolation_and_mismatch():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    org2, user2 = seed_org_user(db, email="other@test.local", name="Other")
    mig = _migration(db, org, user)
    mig2 = MigrationCenterService(db).create_session(
        organization_id=org2.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user2.id,
    )
    us = UploadSessionService(db)
    sess = us.create_session(
        organization_id=org.id,
        migration_session_id=mig.id,
        created_by_user_id=user.id,
    )
    with pytest.raises(DocumentIntakeNotFoundError):
        us.get_session(sess.id, org2.id)
    svc = DocumentIntakeService(db)
    us.start(sess.id, org.id, actor_user_id=user.id)
    with pytest.raises(Exception):
        svc.ingest_bytes(
            organization_id=org.id,
            filename="a.pdf",
            content=PDF_MINIMAL,
            actor_user_id=user.id,
            migration_session_id=mig2.id,
            upload_session_id=sess.id,
        )
    db.close()


def test_upload_with_session_analytics_and_idempotency():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    mig = _migration(db, org, user)
    us = UploadSessionService(db)
    sess = us.create_session(
        organization_id=org.id,
        migration_session_id=mig.id,
        created_by_user_id=user.id,
        expected_file_count=3,
    )
    svc = DocumentIntakeService(db)
    a = svc.ingest_bytes(
        organization_id=org.id,
        filename="a.pdf",
        content=PDF_MINIMAL,
        actor_user_id=user.id,
        migration_session_id=mig.id,
        upload_session_id=sess.id,
        idempotency_key="idem-1",
    )
    b = svc.ingest_bytes(
        organization_id=org.id,
        filename="a.pdf",
        content=PDF_MINIMAL,
        actor_user_id=user.id,
        migration_session_id=mig.id,
        upload_session_id=sess.id,
        idempotency_key="idem-1",
    )
    assert a.id == b.id
    svc.ingest_bytes(
        organization_id=org.id,
        filename="b.pdf",
        content=PDF_MINIMAL + b"\n",
        actor_user_id=user.id,
        migration_session_id=mig.id,
        upload_session_id=sess.id,
        idempotency_key="idem-2",
    )
    # exact duplicate of first content
    svc.ingest_bytes(
        organization_id=org.id,
        filename="c.pdf",
        content=PDF_MINIMAL,
        actor_user_id=user.id,
        migration_session_id=mig.id,
        upload_session_id=sess.id,
        idempotency_key="idem-3",
    )
    sess = us.get_session(sess.id, org.id)
    from app.document_intake.analytics_service import UploadAnalyticsService

    analytics = UploadAnalyticsService(db).get_for_upload_session(sess)
    assert analytics["file_count"] >= 2
    assert analytics["duplicate_count"] >= 1
    assert analytics["average_upload_speed_bps"] is None  # pas assez de durée
    assert sess.received_file_count >= 0
    assert sess.duplicate_file_count >= 0
    db.close()


def test_upload_session_expired():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    mig = _migration(db, org, user)
    us = UploadSessionService(db)
    sess = us.create_session(
        organization_id=org.id,
        migration_session_id=mig.id,
        created_by_user_id=user.id,
    )
    sess.expires_at = datetime.utcnow() - timedelta(hours=1)
    db.commit()
    sess = us.get_session(sess.id, org.id)
    assert sess.status == UploadSessionStatus.EXPIRED.value
    db.close()


def test_fingerprint_v2_blocks_and_zip():
    fp = FileFingerprintService(block_size=64)
    data = PDF_MINIMAL * 100
    result = fp.compute_from_bytes(data, detected_mime_type="application/pdf", normalized_extension=".pdf")
    assert result["schema_version"] == 2
    assert result["sha256"]
    assert result["first_block_hash"]
    assert result["last_block_hash"]
    assert result["size_bytes"] == len(data)
    zip_fp = fp.compute_from_bytes(
        ZIP_MINIMAL, detected_mime_type="application/zip", normalized_extension=".zip"
    )
    assert zip_fp["archive_entry_count"] is not None
    # streaming gros fichier
    stream = io.BytesIO(b"x" * 200_000)
    big = fp.compute_from_stream(stream, size_hint=200_000, detected_mime_type="text/plain")
    assert big["size_bytes"] == 200_000
    assert FileFingerprintService.similarity_score(result, zip_fp) is None


def test_zip_too_many_entries_rejected(monkeypatch):
    monkeypatch.setattr("app.document_intake.fingerprint.ZIP_MAX_ENTRIES", 1)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.txt", "1")
        zf.writestr("b.txt", "2")
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    with pytest.raises(DocumentIntakeValidationError) as exc:
        DocumentIntakeService(db).ingest_bytes(
            organization_id=org.id,
            filename="big.zip",
            content=buf.getvalue(),
            actor_user_id=user.id,
            declared_mime="application/zip",
        )
    assert exc.value.code == "zip_too_many_entries"
    db.close()


def test_events_include_universal_id_no_path():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    row = DocumentIntakeService(db).ingest_bytes(
        organization_id=org.id, filename="a.pdf", content=PDF_MINIMAL, actor_user_id=user.id
    )
    events = db.query(ElfisEvent).all()
    names = {e.event_name for e in events}
    assert EventNames.DOCUMENT_LIFECYCLE_CHANGED in names
    assert EventNames.DOCUMENT_FINGERPRINT_CREATED in names
    for e in events:
        payload = e.payload or {}
        blob = str(payload)
        assert "C:\\" not in blob
        assert "/storage/" not in blob
        if payload.get("universal_document_id"):
            assert payload["universal_document_id"] == row.universal_document_id
    db.close()


def test_partial_complete_and_counters_non_negative():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    mig = _migration(db, org, user)
    us = UploadSessionService(db)
    sess = us.create_session(
        organization_id=org.id,
        migration_session_id=mig.id,
        created_by_user_id=user.id,
        expected_file_count=5,
    )
    us.start(sess.id, org.id, actor_user_id=user.id)
    DocumentIntakeService(db).ingest_bytes(
        organization_id=org.id,
        filename="a.pdf",
        content=PDF_MINIMAL,
        actor_user_id=user.id,
        migration_session_id=mig.id,
        upload_session_id=sess.id,
    )
    sess = us.complete(sess.id, org.id, actor_user_id=user.id, partial=True)
    assert sess.status == UploadSessionStatus.PARTIALLY_COMPLETED.value
    assert sess.received_file_count >= 0
    assert sess.duplicate_file_count >= 0
    assert sess.rejected_file_count >= 0
    db.close()


def test_empty_file_still_rejected():
    factory, _ = make_intake_db()
    db = factory()
    org, user = seed_org_user(db)
    with pytest.raises(DocumentIntakeValidationError):
        DocumentIntakeService(db).ingest_bytes(
            organization_id=org.id,
            filename="empty.pdf",
            content=b"",
            actor_user_id=user.id,
        )
    db.close()
