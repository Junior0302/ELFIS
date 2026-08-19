"""Tests DocumentIntelligenceService."""

from __future__ import annotations

from app.document_intelligence.document_models import ElfisDocumentTextExtraction
from app.document_intelligence.document_quality import text_sha256
from app.document_intelligence.document_schemas import DocumentExtractionRequest
from app.document_intelligence.document_service import DocumentIntelligenceService
from app.document_intelligence.document_types import ExtractionStatus
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from tests.document_intelligence import make_empty_pdf, make_text_pdf, setup_di_db


def test_extraction_persisted_no_pdf_in_db():
    db, _, _ = setup_di_db()
    pdf = make_text_pdf("Facture Total TVA 20 TTC 120 date numéro")
    svc = DocumentIntelligenceService(db, download_fn=lambda p: pdf)
    result = svc.extract_document_text(
        DocumentExtractionRequest(
            organization_id=1,
            vault_document_id="vd-1",
            content_bytes=pdf,
        )
    )
    row = db.query(ElfisDocumentTextExtraction).filter_by(extraction_id=result.extraction_id).one()
    assert row.text_content is None or not row.text_content.startswith("%PDF")
    assert row.mime_type == "application/pdf"
    # colonnes JSON ne contiennent pas le PDF
    assert "%PDF" not in str(row.metadata_json)
    assert "%PDF" not in str(row.warnings)


def test_idempotency_prevents_duplicate():
    db, _, _ = setup_di_db()
    pdf = make_text_pdf("Facture Total TVA montant 100")
    svc = DocumentIntelligenceService(db)
    r1 = svc.extract_document_text(
        DocumentExtractionRequest(
            organization_id=1,
            vault_document_id="vd-1",
            idempotency_key="document-text:1:vd-1:1",
            content_bytes=pdf,
        )
    )
    r2 = svc.extract_document_text(
        DocumentExtractionRequest(
            organization_id=1,
            vault_document_id="vd-1",
            idempotency_key="document-text:1:vd-1:1",
            content_bytes=pdf,
        )
    )
    assert r1.extraction_id == r2.extraction_id
    assert r2.idempotent_reuse is True
    assert db.query(ElfisDocumentTextExtraction).count() == 1


def test_tenant_isolation():
    db, _, _ = setup_di_db()
    pdf = make_text_pdf("Facture Total")
    svc = DocumentIntelligenceService(db)
    from app.document_intelligence.document_exceptions import DocumentNotFoundError
    import pytest

    with pytest.raises(DocumentNotFoundError):
        svc.extract_document_text(
            DocumentExtractionRequest(
                organization_id=2,
                vault_document_id="vd-1",
                content_bytes=pdf,
            )
        )


def test_temp_file_deleted():
    db, _, _ = setup_di_db()
    pdf = make_text_pdf("Facture Total TVA 20")
    svc = DocumentIntelligenceService(db)
    from app.document_intelligence import document_security as sec
    created = []
    orig = sec.create_temp_file

    def tracking(**kwargs):
        p = orig(**kwargs)
        created.append(p)
        return p

    sec.create_temp_file = tracking  # type: ignore
    try:
        svc.extract_document_text(
            DocumentExtractionRequest(
                organization_id=1,
                vault_document_id="vd-1",
                content_bytes=pdf,
            )
        )
        for p in created:
            assert not p.exists()
    finally:
        sec.create_temp_file = orig  # type: ignore


def test_txt_via_service_and_hash():
    db, _, _ = setup_di_db()
    content = (
        b"Facture numero FAC-100 Societe Demo Total TVA 20 montant HT 100 TTC 120 "
        b"date 01/01/2024 reference commande"
    )
    svc = DocumentIntelligenceService(db)
    result = svc.extract_document_text(
        DocumentExtractionRequest(
            organization_id=1,
            vault_document_id="vd-txt",
            content_bytes=content,
        )
    )
    assert result.status == ExtractionStatus.COMPLETED
    row = db.query(ElfisDocumentTextExtraction).filter_by(extraction_id=result.extraction_id).one()
    assert row.text_hash == text_sha256(row.text_content or "")
    assert row.text_length > 0


def test_empty_pdf_publishes_requires_ocr():
    db, _, _ = setup_di_db()
    pdf = make_empty_pdf()
    svc = DocumentIntelligenceService(db)
    result = svc.extract_document_text(
        DocumentExtractionRequest(
            organization_id=1,
            vault_document_id="vd-1",
            content_bytes=pdf,
        )
    )
    assert result.requires_ocr is True
    assert result.status == ExtractionStatus.REQUIRES_OCR
    events = db.query(ElfisEvent).filter(ElfisEvent.event_name == EventNames.DOCUMENT_EXTRACTION_REQUIRES_OCR).all()
    assert events
    for ev in events:
        assert "text_content" not in (ev.payload or {})
        assert "pdf" not in (ev.payload or {})


def test_completed_event_without_text():
    db, _, _ = setup_di_db()
    content = b"Facture fournisseur Total TVA montant date numero 12345"
    svc = DocumentIntelligenceService(db)
    result = svc.extract_document_text(
        DocumentExtractionRequest(
            organization_id=1,
            vault_document_id="vd-txt",
            content_bytes=content,
        )
    )
    assert result.status == ExtractionStatus.COMPLETED
    events = (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.DOCUMENT_EXTRACTION_COMPLETED)
        .all()
    )
    assert events
    payload = events[0].payload or {}
    assert "text_content" not in payload
    assert payload.get("text_length", 0) > 0
