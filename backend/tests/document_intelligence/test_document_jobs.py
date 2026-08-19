"""Tests jobs Document Intelligence."""

from __future__ import annotations

import base64

from app.document_intelligence.document_models import ElfisDocumentTextExtraction
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.jobs.job_models import ElfisJob
from app.jobs.job_schemas import JobRequest
from app.jobs.job_service import JobService
from app.jobs.job_types import JobNames, JobStatus
from app.jobs.job_worker import JobWorker
from tests.document_intelligence import make_text_pdf, setup_di_db


def test_extract_text_job_completed_without_full_text_in_result():
    db, Session, _ = setup_di_db()
    pdf = make_text_pdf("Facture Total TVA 20 montant 100 date")
    JobService(db).enqueue(
        JobRequest(
            job_name=JobNames.VAULT_DOCUMENT_EXTRACT_TEXT,
            organization_id=1,
            user_id=1,
            payload={
                "vault_document_id": "vd-1",
                "document_version": 1,
                "_test_content_b64": base64.b64encode(pdf).decode("ascii"),
            },
            idempotency_key="di-job-1",
        )
    )
    worker = JobWorker(db, worker_id="w-di", session_factory=lambda: Session())
    assert worker.process_next_batch() >= 1
    job = db.query(ElfisJob).filter_by(idempotency_key="di-job-1").one()
    assert job.status == JobStatus.COMPLETED
    result = job.result or {}
    assert "extraction_id" in result
    assert "text_content" not in result
    assert "extracted_text" not in result
    assert result.get("text_length") is not None


def test_ocr_job_permanent_when_disabled():
    db, Session, _ = setup_di_db()
    JobService(db).enqueue(
        JobRequest(
            job_name=JobNames.VAULT_DOCUMENT_OCR,
            organization_id=1,
            payload={"vault_document_id": "vd-1"},
            idempotency_key="di-ocr-1",
        )
    )
    worker = JobWorker(db, worker_id="w-ocr", session_factory=lambda: Session())
    worker.process_next_batch()
    job = db.query(ElfisJob).filter_by(idempotency_key="di-ocr-1").one()
    assert job.status in (JobStatus.DEAD_LETTER, JobStatus.FAILED)


def test_failed_event_on_bad_mime():
    db, Session, _ = setup_di_db()
    from app.models_vault import VaultDocument

    doc = db.query(VaultDocument).filter_by(id="vd-1").one()
    doc.mime_type = "application/zip"
    doc.original_filename = "x.zip"
    db.commit()

    JobService(db).enqueue(
        JobRequest(
            job_name=JobNames.VAULT_DOCUMENT_EXTRACT_TEXT,
            organization_id=1,
            payload={
                "vault_document_id": "vd-1",
                "_test_content_b64": base64.b64encode(b"PK").decode("ascii"),
            },
            idempotency_key="di-fail-1",
        )
    )
    worker = JobWorker(db, worker_id="w-f", session_factory=lambda: Session())
    worker.process_next_batch()
    job = db.query(ElfisJob).filter_by(idempotency_key="di-fail-1").one()
    # MIME invalide → PermanentJobError avant persistance extraction
    assert job.status in (JobStatus.DEAD_LETTER, JobStatus.FAILED)
    assert job.last_error
