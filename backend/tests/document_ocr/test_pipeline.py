"""Tests pipeline OCR noop + artefact + version pin."""

from __future__ import annotations

import asyncio
import json

from app.document_processing.ocr.service import DocumentOCRService
from app.document_processing.orchestrator import DocumentProcessingOrchestrator
from app.document_processing.repository import DocumentProcessingRepository
from app.document_processing.service import DocumentProcessingService
from app.document_processing.types import PIPELINE_BASIC_V1, PIPELINE_CLASSIFICATION_V1, PIPELINE_OCR_V1
from tests.document_ocr.conftest_helpers import make_ocr_db, seed_document, seed_org_user


def _run(c):
    return asyncio.run(c)


def test_ocr_noop_pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.document_ocr_enabled", True)
    monkeypatch.setattr("app.config.settings.document_ocr_provider", "noop")
    monkeypatch.setattr("app.config.settings.storage_local_root", str(tmp_path / "artifacts"))
    Session, _ = make_ocr_db()
    db = Session()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user)
    job = DocumentProcessingService(db).create_job(
        organization_id=org.id,
        document_id=doc.id,
        pipeline_key=PIPELINE_OCR_V1,
        metadata={"noop_mode": "ok", "noop_pages": 2},
    )
    assert len(DocumentProcessingService(db).list_steps(job.id)) == 8
    DocumentProcessingRepository(db).claim_jobs(worker_id="w", batch_size=1, lease_seconds=60)
    _run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="w"))
    db.refresh(job)
    assert job.status == "completed"
    items, total = DocumentOCRService(db).list_results(organization_id=org.id, document_id=doc.id)
    assert total == 1
    row = items[0]
    assert row.document_version_id == doc.current_version_id
    assert row.provider_key == "noop"
    assert row.page_count == 2
    assert row.text_artifact_storage_object_id
    pages = DocumentOCRService(db).list_pages(row.id)
    assert len(pages) == 2
    # texte uniquement via open_text
    data, _ = DocumentOCRService(db).open_text(row.id, org.id)
    payload = json.loads(data.decode("utf-8"))
    assert payload["schema_version"] == "ocr_text_v1"
    assert len(payload["pages"]) == 2
    # metadata job sans texte
    meta = job.metadata_json or {}
    raw = str(meta.get("_ocr_provider_result") or {})
    assert "[noop page" not in raw


def test_ocr_retryable_then_basic_unaffected(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.document_ocr_enabled", True)
    monkeypatch.setattr("app.config.settings.document_ocr_provider", "noop")
    monkeypatch.setattr("app.config.settings.storage_local_root", str(tmp_path / "artifacts"))
    Session, _ = make_ocr_db()
    db = Session()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user)
    job = DocumentProcessingService(db).create_job(
        organization_id=org.id,
        document_id=doc.id,
        pipeline_key=PIPELINE_OCR_V1,
        metadata={"noop_mode": "permanent"},
    )
    DocumentProcessingRepository(db).claim_jobs(worker_id="w", batch_size=1, lease_seconds=60)
    _run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="w"))
    db.refresh(job)
    assert job.status == "failed"

    # non-régression pipelines
    j2 = DocumentProcessingService(db).create_job(
        organization_id=org.id, document_id=doc.id, pipeline_key=PIPELINE_BASIC_V1
    )
    DocumentProcessingRepository(db).claim_jobs(worker_id="w2", batch_size=1, lease_seconds=60)
    _run(DocumentProcessingOrchestrator(db).run_job(j2.id, worker_id="w2"))
    db.refresh(j2)
    assert j2.status == "completed"

    j3 = DocumentProcessingService(db).create_job(
        organization_id=org.id, document_id=doc.id, pipeline_key=PIPELINE_CLASSIFICATION_V1
    )
    DocumentProcessingRepository(db).claim_jobs(worker_id="w3", batch_size=1, lease_seconds=60)
    _run(DocumentProcessingOrchestrator(db).run_job(j3.id, worker_id="w3"))
    db.refresh(j3)
    assert j3.status == "completed"


def test_quarantine_blocks(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.document_ocr_enabled", True)
    monkeypatch.setattr("app.config.settings.document_ocr_provider", "noop")
    Session, _ = make_ocr_db()
    db = Session()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user)
    from app.storage.storage_models import ElfisDocumentVersion, ElfisStorageObject

    ver = db.get(ElfisDocumentVersion, doc.current_version_id)
    obj = db.get(ElfisStorageObject, ver.storage_object_id)
    obj.status = "quarantined"
    db.commit()
    job = DocumentProcessingService(db).create_job(
        organization_id=org.id, document_id=doc.id, pipeline_key=PIPELINE_OCR_V1
    )
    DocumentProcessingRepository(db).claim_jobs(worker_id="w", batch_size=1, lease_seconds=60)
    _run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="w"))
    db.refresh(job)
    assert job.status == "blocked"
