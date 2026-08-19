"""Tests pipeline archive → extract → AI."""

from __future__ import annotations

from app.config import settings
from app.document_intelligence.event_handlers import (
    DocumentArchivedTextExtractionHandler,
    DocumentExtractionCompletedAIHandler,
)
from app.events.event_context import EventContext
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.jobs.job_models import ElfisJob
from app.jobs.job_types import JobNames
from app.document_intelligence.document_models import ElfisDocumentTextExtraction
from app.document_intelligence.document_types import ExtractionStatus
from datetime import datetime
import uuid

from tests.document_intelligence import setup_di_db


def test_archive_enqueues_extract_text(monkeypatch):
    db, _, _ = setup_di_db()
    monkeypatch.setattr(settings, "elfis_auto_text_extraction_enabled", True)
    handler = DocumentArchivedTextExtractionHandler()
    event = DomainEvent(
        event_name=EventNames.VAULT_DOCUMENT_ARCHIVED,
        organization_id=1,
        aggregate_type="vault_document",
        aggregate_id="vd-1",
        payload={"vault_document_id": "vd-1", "version": 1},
        metadata={},
    )
    handler.handle(event, EventContext(db=db, worker_id="test"))
    jobs = db.query(ElfisJob).filter(ElfisJob.job_name == JobNames.VAULT_DOCUMENT_EXTRACT_TEXT).all()
    assert len(jobs) == 1
    assert jobs[0].idempotency_key == "document-text:1:vd-1:1"

    # idempotent
    handler.handle(event, EventContext(db=db, worker_id="test"))
    jobs2 = db.query(ElfisJob).filter(ElfisJob.job_name == JobNames.VAULT_DOCUMENT_EXTRACT_TEXT).all()
    assert len(jobs2) == 1


def test_extraction_completed_enqueues_classification(monkeypatch):
    db, _, _ = setup_di_db()
    monkeypatch.setattr(settings, "elfis_auto_ai_analysis_enabled", True)
    row = ElfisDocumentTextExtraction(
        id=str(uuid.uuid4()),
        extraction_id=str(uuid.uuid4()),
        organization_id=1,
        vault_document_id="vd-1",
        document_version=1,
        extractor_name="pdf_text",
        status=ExtractionStatus.COMPLETED,
        text_content="Facture Total TVA 20 montant 100",
        text_length=32,
        requires_ocr=False,
        metadata_json={},
        warnings=[],
        errors=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()

    handler = DocumentExtractionCompletedAIHandler()
    event = DomainEvent(
        event_name=EventNames.DOCUMENT_EXTRACTION_COMPLETED,
        organization_id=1,
        aggregate_type="document_text_extraction",
        aggregate_id=row.extraction_id,
        payload={
            "extraction_id": row.extraction_id,
            "vault_document_id": "vd-1",
            "organization_id": 1,
            "status": "completed",
            "text_length": 32,
            "requires_ocr": False,
        },
        metadata={},
    )
    handler.handle(event, EventContext(db=db, worker_id="test"))
    jobs = (
        db.query(ElfisJob)
        .filter(ElfisJob.job_name == JobNames.VAULT_DOCUMENT_AI_CLASSIFICATION)
        .all()
    )
    assert len(jobs) == 1
    assert jobs[0].payload.get("extraction_id") == row.extraction_id
    assert "extracted_text" not in (jobs[0].payload or {})
