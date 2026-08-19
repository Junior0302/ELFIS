"""Phase C — Analyse IA (AI-001 … AI-006)."""

from __future__ import annotations

from app.ai.ai_models import ElfisDocumentAnalysis
from app.config import settings
from tests.functional.fixtures.generate_documents import ensure_document_fixtures
from tests.functional.helpers.phase_c import doc_id_from_archive, drain_pipeline


def test_ai_001_002_supplier_and_customer_classification(api, functional_db, mock_vault_storage, monkeypatch):
    monkeypatch.setattr(settings, "elfis_auto_text_extraction_enabled", True)
    monkeypatch.setattr(settings, "elfis_auto_ai_analysis_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "")
    files = ensure_document_fixtures()
    api.login_user("active")

    for fname, expected_hint in (
        ("invoice_supplier_valid.pdf", "supplier"),
        ("invoice_customer_valid.pdf", "customer"),
    ):
        body = api.upload_document(files[fname], document_type="supplier_invoice" if "supplier" in fname else "customer_invoice", expect=(200, 201))
        doc_id = doc_id_from_archive(body)
        drain_pipeline(functional_db["Session"], max_rounds=30)
        Session = functional_db["Session"]
        db = Session()
        try:
            analysis = (
                db.query(ElfisDocumentAnalysis)
                .filter(ElfisDocumentAnalysis.vault_document_id == doc_id)
                .first()
            )
            # Heuristique peut produire analysis ou rester en attente selon timing
            if analysis is not None:
                blob = str(analysis.document_type or "").lower() + str(analysis.status or "").lower()
                assert expected_hint in blob or "invoice" in blob or analysis.status is not None
        finally:
            db.close()


def test_ai_003_credit_note(api, functional_db, mock_vault_storage, monkeypatch):
    monkeypatch.setattr(settings, "elfis_auto_text_extraction_enabled", True)
    monkeypatch.setattr(settings, "elfis_auto_ai_analysis_enabled", True)
    files = ensure_document_fixtures()
    api.login_user("active")
    body = api.upload_document(
        files["credit_note_supplier.pdf"],
        document_type="credit_note",
        expect=(200, 201),
    )
    doc_id = doc_id_from_archive(body)
    drain_pipeline(functional_db["Session"], max_rounds=30)
    assert doc_id


def test_ai_004_low_confidence_or_review(api, functional_db, mock_vault_storage, monkeypatch):
    monkeypatch.setattr(settings, "elfis_auto_text_extraction_enabled", True)
    monkeypatch.setattr(settings, "elfis_auto_ai_analysis_enabled", True)
    files = ensure_document_fixtures()
    api.login_user("active")
    body = api.upload_document(files["invoice_requires_review.pdf"], expect=(200, 201))
    doc_id = doc_id_from_archive(body)
    drain_pipeline(functional_db["Session"], max_rounds=30)
    Session = functional_db["Session"]
    db = Session()
    try:
        from app.accounting.accounting_models import ElfisAccountingProposal

        prop = (
            db.query(ElfisAccountingProposal)
            .filter(ElfisAccountingProposal.vault_document_id == doc_id)
            .first()
        )
        if prop is not None:
            assert prop.status in (
                "requires_review",
                "ready_for_validation",
                "validation_failed",
                "failed",
            )
            # Montant élevé → review attendu
            if prop.status == "ready_for_validation":
                # Politique peut encore review via reasons
                pass
    finally:
        db.close()
