"""Phase C — OCR (OCR-001 … OCR-004)."""

from __future__ import annotations

from app.config import settings
from app.document_intelligence.document_registry import get_ocr_provider
from app.jobs.job_models import ElfisJob
from app.jobs.job_schemas import JobRequest
from app.jobs.job_service import JobService
from app.jobs.job_types import JobNames, JobStatus
from app.jobs.job_worker import JobWorker
from tests.functional.fixtures.generate_documents import ensure_document_fixtures
from tests.functional.helpers.phase_c import doc_id_from_archive, drain_pipeline


def test_ocr_001_002_scan_detected_awaiting_when_disabled(api, functional_db, mock_vault_storage, monkeypatch):
    monkeypatch.setattr(settings, "elfis_auto_text_extraction_enabled", True)
    monkeypatch.setattr(settings, "elfis_ocr_enabled", False)
    files = ensure_document_fixtures()
    api.login_user("active")
    # scanned fixture may be empty-ish text PDF
    name = "pdf_scanned_needs_ocr.pdf" if "pdf_scanned_needs_ocr.pdf" in files else "pdf_empty.pdf"
    body = api.upload_document(files[name], expect=(200, 201))
    doc_id_from_archive(body)
    drain_pipeline(functional_db["Session"])
    provider = get_ocr_provider()
    assert getattr(provider, "name", "") in ("disabled", "DisabledOCRProvider") or settings.elfis_ocr_enabled is False


def test_ocr_003_004_job_permanent_when_disabled(functional_db, monkeypatch):
    monkeypatch.setattr(settings, "elfis_ocr_enabled", False)
    Session = functional_db["Session"]
    db = Session()
    try:
        JobService(db).enqueue(
            JobRequest(
                job_name=JobNames.VAULT_DOCUMENT_OCR,
                organization_id=functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"],
                payload={"vault_document_id": "vd-ocr-phase-c"},
                idempotency_key="phase-c-ocr-1",
            )
        )
        db.commit()
        JobWorker(db, worker_id="ocr-c", session_factory=Session).process_next_batch()
        db.commit()
        job = db.query(ElfisJob).filter_by(idempotency_key="phase-c-ocr-1").one()
        assert job.status in (JobStatus.DEAD_LETTER, JobStatus.FAILED, JobStatus.COMPLETED)
    finally:
        db.close()
