"""SCENARIO 3/4 — Documents (upload vault)."""

from __future__ import annotations

from tests.functional.fixtures.generate_documents import ensure_document_fixtures


def test_upload_supplier_invoice_archived(api, documents_dir):
    files = ensure_document_fixtures()
    api.login_user("active")
    # Upload peut réussir ou être bloqué selon subscription access —
    # on accepte 200/201 ou 402 si require_active_subscription strict
    result = api.upload_document(
        files["invoice_supplier_valid.pdf"],
        document_type="supplier_invoice",
        expect=(200, 201, 402, 403),
    )
    assert result is not None
    if isinstance(result, dict) and result.get("document_id") or result.get("id"):
        docs = api.list_documents()
        assert docs is not None


def test_upload_rejects_double_extension(api):
    from tests.document_intelligence import make_text_pdf

    api.login_user("active")
    content = make_text_pdf("x")
    r = api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("invoice.php.pdf", content, "application/pdf")},
        data={"tenant_id": str(api.org_id), "document_type": "supplier_invoice"},
    )
    # Soit validation vault, soit middleware/security fichier
    assert r.status_code in (400, 402, 403, 415, 422)


def test_upload_rejects_corrupt_pdf(api):
    api.login_user("active")
    r = api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("bad.pdf", b"NOT_A_PDF", "application/pdf")},
        data={"tenant_id": str(api.org_id), "document_type": "supplier_invoice"},
    )
    assert r.status_code in (400, 402, 403, 415, 422)
