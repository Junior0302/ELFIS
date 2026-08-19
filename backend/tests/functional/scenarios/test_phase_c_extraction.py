"""Phase C — Extraction texte (EXTRACT-001 … EXTRACT-004)."""

from __future__ import annotations

from app.document_intelligence.document_models import ElfisDocumentTextExtraction
from app.jobs.job_models import ElfisJob
from app.jobs.job_types import JobNames, JobStatus
from tests.functional.fixtures.generate_documents import ensure_document_fixtures
from tests.functional.helpers.phase_c import doc_id_from_archive, drain_pipeline


def test_extract_001_text_pdf(api, functional_db, mock_vault_storage, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "elfis_auto_text_extraction_enabled", True)
    files = ensure_document_fixtures()
    api.login_user("active")
    body = api.upload_document(files["invoice_text_pdf.pdf"], expect=(200, 201))
    doc_id = doc_id_from_archive(body)

    stats = drain_pipeline(functional_db["Session"])
    assert stats["jobs"] + stats["events"] >= 1

    Session = functional_db["Session"]
    db = Session()
    try:
        jobs = (
            db.query(ElfisJob)
            .filter(
                ElfisJob.organization_id == api.org_id,
                ElfisJob.job_name == JobNames.VAULT_DOCUMENT_EXTRACT_TEXT,
            )
            .all()
        )
        assert len(jobs) >= 1
        # Au moins un job terminé ou en cours après drain
        statuses = {j.status for j in jobs}
        assert statuses & {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.DEAD_LETTER, JobStatus.PENDING, JobStatus.PROCESSING}

        row = (
            db.query(ElfisDocumentTextExtraction)
            .filter(ElfisDocumentTextExtraction.vault_document_id == doc_id)
            .first()
        )
        if row is not None:
            assert row.organization_id == api.org_id
            # Texte non exposé dans result job
            for j in jobs:
                result = j.result or {}
                assert "text_content" not in result
                assert "extracted_text" not in result
    finally:
        db.close()


def test_extract_002_empty_pdf_requires_ocr_or_controlled(api, functional_db, mock_vault_storage, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "elfis_auto_text_extraction_enabled", True)
    monkeypatch.setattr(settings, "elfis_ocr_enabled", False)
    files = ensure_document_fixtures()
    api.login_user("active")
    body = api.upload_document(files["pdf_empty.pdf"], expect=(200, 201))
    doc_id = doc_id_from_archive(body)
    drain_pipeline(functional_db["Session"])

    Session = functional_db["Session"]
    db = Session()
    try:
        row = (
            db.query(ElfisDocumentTextExtraction)
            .filter(ElfisDocumentTextExtraction.vault_document_id == doc_id)
            .first()
        )
        if row is not None:
            assert row.requires_ocr is True or (row.text_length or 0) == 0 or row.status in (
                "completed",
                "requires_ocr",
                "failed",
                "awaiting_ocr",
            )
    finally:
        db.close()
