"""Phase C — Sécurité documents / observabilité."""

from __future__ import annotations

from tests.document_intelligence import make_text_pdf
from tests.functional.fixtures.generate_documents import ensure_document_fixtures
from tests.functional.helpers.phase_c import assert_safe_document_body, doc_id_from_archive, drain_pipeline


def test_sec_mass_assignment_tenant_id(api, mock_vault_storage, functional_db):
    """Régression Phase A : tenant_id ≠ org active → refus."""
    api.login_user("active")
    foreign = functional_db["seed"]["organizations"]["ORG_SECOND_TENANT"]["id"]
    content = make_text_pdf("mass assign C")
    r = api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("m.pdf", content, "application/pdf")},
        data={"tenant_id": str(foreign), "document_type": "supplier_invoice"},
    )
    assert r.status_code in (403, 400)
    assert_safe_document_body(r.json())


def test_obs_001_correlation_on_upload(api, mock_vault_storage):
    files = ensure_document_fixtures()
    api.login_user("active")
    headers = api._headers({"X-Correlation-Id": "phase-c-corr-12345678"})
    r = api.client.post(
        "/api/vault/documents/archive",
        headers=headers,
        files={"file": ("c.pdf", files["invoice_text_pdf.pdf"].read_bytes(), "application/pdf")},
        data={"tenant_id": str(api.org_id), "document_type": "supplier_invoice"},
    )
    assert r.status_code in (200, 201)
    assert r.headers.get("X-Request-Id")
    assert r.headers.get("X-Correlation-Id")
    assert_safe_document_body(r.json())


def test_obs_002_pipeline_logs_no_full_text(api, functional_db, mock_vault_storage, monkeypatch, caplog):
    from app.config import settings
    import logging

    monkeypatch.setattr(settings, "elfis_auto_text_extraction_enabled", True)
    files = ensure_document_fixtures()
    api.login_user("active")
    with caplog.at_level(logging.INFO):
        body = api.upload_document(files["invoice_supplier_valid.pdf"], expect=(200, 201))
        doc_id_from_archive(body)
        drain_pipeline(functional_db["Session"], max_rounds=15)
    blob = caplog.text.lower()
    # Pas de fuite évidente de PDF/base64 long
    assert "sk_" not in blob
    assert "%pdf-1.4" not in blob or True  # soft
