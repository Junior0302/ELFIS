"""Tests pipeline extraction + revue."""

from __future__ import annotations

import asyncio

import pytest

from app.config import settings
from app.document_processing.extraction.service import DocumentExtractionService
from app.document_processing.extraction.types import PIPELINE_EXTRACTION_V1
from app.document_processing.orchestrator import DocumentProcessingOrchestrator
from app.document_processing.repository import DocumentProcessingRepository
from app.document_processing.service import DocumentProcessingService
from tests.document_extraction.conftest_helpers import (
    make_extraction_db,
    run_ocr_noop,
    seed_document,
    seed_org_user,
)


@pytest.fixture()
def db_env(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_local_root", str(tmp_path / "store"))
    monkeypatch.setattr(settings, "document_ocr_enabled", True)
    monkeypatch.setattr(settings, "document_ocr_provider", "noop")
    monkeypatch.setattr(settings, "document_extraction_enabled", True)
    monkeypatch.setattr(settings, "document_extraction_provider", "noop")
    Session, _engine = make_extraction_db()
    db = Session()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path / "obj", org, user)
    yield db, org, user, doc, tmp_path
    db.close()


def test_extraction_noop_pipeline(db_env, monkeypatch):
    db, org, user, doc, _ = db_env
    ocr_job = run_ocr_noop(db, doc, monkeypatch=monkeypatch)
    assert ocr_job.status == "completed"

    job = DocumentProcessingService(db).create_job(
        organization_id=org.id,
        document_id=doc.id,
        document_version_id=doc.current_version_id,
        pipeline_key=PIPELINE_EXTRACTION_V1,
        idempotency_key=f"extr-{doc.id}",
        metadata={"force_extraction_enabled": True, "noop_mode": "ok"},
    )
    DocumentProcessingRepository(db).claim_jobs(worker_id="t", batch_size=1, lease_seconds=60)
    asyncio.run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="t"))
    db.refresh(job)
    assert job.status == "completed", (job.status, job.error_code, job.error_message_sanitized)

    svc = DocumentExtractionService(db)
    items, total = svc.list_results(organization_id=org.id, document_id=doc.id)
    assert total >= 1
    row = items[0]
    assert row.document_version_id == doc.current_version_id
    assert row.ocr_result_id
    assert row.schema_key in ("generic_document_v1", "invoice_basic_v1")
    assert row.result_artifact_storage_object_id
    fields = svc.list_fields(row.id)
    assert fields
    data, _ = svc.open_content(row.id, org.id)
    assert b"structured_extraction_v1" in data or b"schema" in data
    # pas de object_key dans le contenu API — on vérifie artefact JSON
    assert b"object_key" not in data


def test_extraction_confirm_reject(db_env, monkeypatch):
    db, org, user, doc, _ = db_env
    run_ocr_noop(db, doc, monkeypatch=monkeypatch)
    job = DocumentProcessingService(db).create_job(
        organization_id=org.id,
        document_id=doc.id,
        document_version_id=doc.current_version_id,
        pipeline_key=PIPELINE_EXTRACTION_V1,
        idempotency_key=f"extr2-{doc.id}",
        metadata={"force_extraction_enabled": True, "noop_mode": "ok"},
    )
    DocumentProcessingRepository(db).claim_jobs(worker_id="t", batch_size=1, lease_seconds=60)
    asyncio.run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="t"))
    svc = DocumentExtractionService(db)
    items, _ = svc.list_results(organization_id=org.id, document_id=doc.id)
    row = items[0]
    confirmed = svc.confirm(row.id, org.id, actor_user_id=user.id)
    assert confirmed.status == "confirmed"
    # reextract crée un job
    new_job = svc.request_reextract(row.id, org.id, actor_user_id=user.id, force=True)
    assert new_job.pipeline_key == PIPELINE_EXTRACTION_V1


def test_extraction_source_missing_blocks(db_env):
    db, org, user, doc, _ = db_env
    # pas d'OCR
    job = DocumentProcessingService(db).create_job(
        organization_id=org.id,
        document_id=doc.id,
        document_version_id=doc.current_version_id,
        pipeline_key=PIPELINE_EXTRACTION_V1,
        idempotency_key=f"extr-miss-{doc.id}",
        metadata={"force_extraction_enabled": True, "noop_mode": "ok"},
    )
    DocumentProcessingRepository(db).claim_jobs(worker_id="t", batch_size=1, lease_seconds=60)
    asyncio.run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="t"))
    db.refresh(job)
    assert job.status in ("failed", "blocked")
