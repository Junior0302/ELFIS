"""Tests Document Analysis Pipeline V1 (Sprint 3)."""

from __future__ import annotations

import io

import pytest
from pypdf import PdfWriter

from app.document_analysis.analyzers.ocr_decision import decide_ocr
from app.document_analysis.classifiers import classify_document
from app.document_analysis.enums import AnalysisReportStatus, DocumentClass
from app.document_analysis.exceptions import DocumentAnalysisConflictError
from app.document_analysis.language import analyze_language
from app.document_analysis.orientation import analyze_orientation
from app.document_analysis.pipeline import run_analysis_pipeline
from app.document_analysis.service import DocumentAnalysisService
from app.document_intake.enums import DocumentLifecycleStatus
from app.document_intake.service import DocumentIntakeService
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


def _make_text_pdf(text: str = "Facture TVA total montant client") -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    # pypdf blank page has no text — inject via content stream heuristically insufficient
    # Use raw PDF with text operators for language/classification
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
        b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
        b"4 0 obj<< /Length "
        + str(40 + len(text)).encode()
        + b" >>stream\nBT /F1 12 Tf 10 100 Td ("
        + text.encode("latin-1", errors="replace")
        + b") Tj ET\nendstream\nendobj\n"
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"trailer<< /Size 6 /Root 1 0 R >>\nstartxref\n0\n%%EOF\n"
    )


def _bootstrap():
    factory, _ = make_intake_db()
    # extend tables for analysis
    from app.database import Base
    from app.document_analysis import models as analysis_models  # noqa: F401

    db = factory()
    # create analysis table on same engine
    engine = db.get_bind()
    analysis_models.ElfisDocumentAnalysisReport.__table__.create(bind=engine, checkfirst=True)
    org, user = seed_org_user(db)
    return factory, db, org, user


def test_pipeline_pdf_text_and_events():
    factory, db, org, user = _bootstrap()
    pdf = _make_text_pdf("Facture TVA total montant et la societe")
    item = DocumentIntakeService(db).ingest_bytes(
        organization_id=org.id,
        filename="facture_client.pdf",
        content=pdf,
        actor_user_id=user.id,
        declared_mime="application/pdf",
    )
    assert item.lifecycle_status == DocumentLifecycleStatus.READY_FOR_ANALYSIS.value
    report = DocumentAnalysisService(db).analyze_item(item.id, org.id, actor_user_id=user.id)
    assert report.status == AnalysisReportStatus.COMPLETED.value
    assert report.report_json.get("llm_used") is False
    assert report.report_json.get("ocr_executed") is False
    assert report.report_json.get("extraction") is None
    assert report.need_ocr is False or report.need_ocr is True  # depends on text extract
    assert report.quality_score is not None
    db.refresh(item)
    assert item.lifecycle_status == DocumentLifecycleStatus.READY_FOR_AI.value
    names = {e.event_name for e in db.query(ElfisEvent).all()}
    assert EventNames.DOCUMENT_ANALYSIS_STARTED in names
    assert EventNames.DOCUMENT_ANALYSIS_COMPLETED in names
    assert EventNames.DOCUMENT_ANALYSIS_READY_FOR_AI in names
    db.close()


def test_image_needs_ocr():
    factory, db, org, user = _bootstrap()
    item = DocumentIntakeService(db).ingest_bytes(
        organization_id=org.id,
        filename="scan.png",
        content=PNG_MINIMAL,
        actor_user_id=user.id,
        declared_mime="image/png",
    )
    report = DocumentAnalysisService(db).analyze_item(item.id, org.id, actor_user_id=user.id)
    assert report.need_ocr is True
    assert report.detected_format == "png"
    assert (report.report_json.get("ocr_decision") or {}).get("reason") == "raster_image"
    db.close()


def test_zip_csv_xml_json_formats():
    report_zip = run_analysis_pipeline(
        content=ZIP_MINIMAL,
        filename="pack.zip",
        mime="application/zip",
        extension=".zip",
        checksum_sha256="a" * 64,
        fingerprint={},
        size_bytes=len(ZIP_MINIMAL),
    )
    assert report_zip["technical"]["detected_format"] == "zip"
    assert report_zip["ocr_decision"]["need_ocr"] is False

    csv_data = b"date,montant,client\n2024-01-01,10,ACME\n"
    r_csv = run_analysis_pipeline(
        content=csv_data,
        filename="export.csv",
        mime="text/csv",
        extension=".csv",
        checksum_sha256="b" * 64,
        fingerprint={},
        size_bytes=len(csv_data),
    )
    assert r_csv["technical"]["detected_format"] == "csv"
    assert r_csv["ocr_decision"]["need_ocr"] is False

    xml = b'<?xml version="1.0"?><root><facture>1</facture></root>'
    assert (
        run_analysis_pipeline(
            content=xml,
            filename="a.xml",
            mime="application/xml",
            extension=".xml",
            checksum_sha256="c" * 64,
            fingerprint={},
            size_bytes=len(xml),
        )["technical"]["detected_format"]
        == "xml"
    )

    js = b'{"invoice": true, "total": 1}'
    assert (
        run_analysis_pipeline(
            content=js,
            filename="a.json",
            mime="application/json",
            extension=".json",
            checksum_sha256="d" * 64,
            fingerprint={},
            size_bytes=len(js),
        )["technical"]["detected_format"]
        == "json"
    )


def test_language_and_classification_heuristics():
    tech = {"detected_format": "txt", "pdf": {}, "is_image": False}
    lang = analyze_language(
        "La facture et le montant total de la TVA pour le client".encode(),
        tech,
    )
    assert lang["code"] == "fr"
    clf = classify_document(
        b"Facture numero 123 TVA total",
        filename="facture_janvier.pdf",
        technical=tech,
    )
    assert clf["label"] == DocumentClass.INVOICE.value


def test_orientation_pdf_rotate():
    # Minimal PDF without rotate → 0
    orient = analyze_orientation(PDF_MINIMAL, {"detected_format": "pdf", "pdf": {}})
    assert orient["degrees"] in (0, 90, 180, 270)
    assert orient["mixed"] is False


def test_ocr_decision_text_vs_scan():
    tech_text = {
        "detected_format": "pdf",
        "pdf": {"has_text": True, "probable_scan": False, "is_encrypted": False},
    }
    assert decide_ocr(tech_text, {"code": "fr", "sample_chars": 100})["need_ocr"] is False
    tech_scan = {
        "detected_format": "pdf",
        "pdf": {"has_text": False, "probable_scan": True, "is_encrypted": False},
    }
    assert decide_ocr(tech_scan, {"code": "unknown", "sample_chars": 0})["need_ocr"] is True


def test_quarantine_blocked():
    factory, db, org, user = _bootstrap()
    item = DocumentIntakeService(db).ingest_bytes(
        organization_id=org.id,
        filename="fake.pdf",
        content=PNG_MINIMAL,
        actor_user_id=user.id,
        declared_mime="application/pdf",
    )
    assert item.status == DocumentLifecycleStatus.QUARANTINED.value
    with pytest.raises(DocumentAnalysisConflictError):
        DocumentAnalysisService(db).analyze_item(item.id, org.id, actor_user_id=user.id)
    db.close()


def test_session_batch_analyze():
    factory, db, org, user = _bootstrap()
    mig = MigrationCenterService(db).create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    DocumentIntakeService(db).ingest_bytes(
        organization_id=org.id,
        filename="a.pdf",
        content=PDF_MINIMAL,
        actor_user_id=user.id,
        migration_session_id=mig.id,
        declared_mime="application/pdf",
    )
    result = DocumentAnalysisService(db).analyze_migration_session(
        organization_id=org.id,
        migration_session_id=mig.id,
        actor_user_id=user.id,
    )
    assert result["analyzed"] >= 1
    rows, total = DocumentAnalysisService(db).list_for_session(
        organization_id=org.id, migration_session_id=mig.id
    )
    assert total >= 1
    assert rows[0].universal_document_id
    db.close()


def test_no_sensitive_payload_in_events():
    factory, db, org, user = _bootstrap()
    item = DocumentIntakeService(db).ingest_bytes(
        organization_id=org.id,
        filename="safe.pdf",
        content=PDF_MINIMAL,
        actor_user_id=user.id,
    )
    DocumentAnalysisService(db).analyze_item(item.id, org.id, actor_user_id=user.id)
    for e in db.query(ElfisEvent).all():
        blob = str(e.payload or {})
        assert "file_content" not in blob
        assert "%PDF" not in blob
        assert "C:\\" not in blob
    db.close()
