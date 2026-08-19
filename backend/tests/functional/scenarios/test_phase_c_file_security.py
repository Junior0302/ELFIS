"""Phase C — Sécurité fichiers (SEC upload)."""

from __future__ import annotations

from tests.document_intelligence import make_text_pdf
from tests.functional.helpers.phase_c import assert_safe_document_body


def test_sec_001_unauthenticated_upload(api):
    content = make_text_pdf("x")
    r = api.client.post(
        "/api/vault/documents/archive",
        files={"file": ("x.pdf", content, "application/pdf")},
        data={"tenant_id": "1", "document_type": "supplier_invoice"},
    )
    assert r.status_code in (401, 403)
    assert_safe_document_body(r.json())


def test_file_corrupt_rejected(api):
    api.login_user("active")
    r = api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("bad.pdf", b"NOT_A_PDF_CONTENT", "application/pdf")},
        data={"tenant_id": str(api.org_id), "document_type": "supplier_invoice"},
    )
    assert r.status_code in (400, 415, 422)
    assert_safe_document_body(r.json())


def test_file_null_byte_name(api):
    api.login_user("active")
    content = make_text_pdf("x")
    r = api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("inv\x00oice.pdf", content, "application/pdf")},
        data={"tenant_id": str(api.org_id), "document_type": "supplier_invoice"},
    )
    assert r.status_code in (200, 201, 400, 422)


def test_wrong_magic_zip_as_pdf(api):
    api.login_user("active")
    r = api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("fake.pdf", b"PK\x03\x04zipcontent", "application/pdf")},
        data={"tenant_id": str(api.org_id), "document_type": "supplier_invoice"},
    )
    assert r.status_code in (400, 415, 422)
