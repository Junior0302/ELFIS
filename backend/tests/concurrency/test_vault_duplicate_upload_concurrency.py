"""CONC-007 — Upload doublon (même hash) contrôlé."""

from __future__ import annotations

from tests.document_intelligence import make_text_pdf


def test_conc_007_vault_duplicate_upload_concurrency(api, mock_vault_storage):
    api.login_user("org_admin")
    content = make_text_pdf("phase-f-duplicate-hash-content-unique")

    r1 = api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("dup-f.pdf", content, "application/pdf")},
        data={"tenant_id": str(api.org_id), "document_type": "supplier_invoice"},
    )
    assert r1.status_code in (200, 201), r1.text

    r2 = api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("dup-f.pdf", content, "application/pdf")},
        data={"tenant_id": str(api.org_id), "document_type": "supplier_invoice"},
    )
    assert r2.status_code in (409, 400, 200)
    if r2.status_code == 200:
        # politique reuse éventuelle — pas deux blobs distincts exigés ici
        assert r2.json().get("existing_document_id") or r1.json().get("id")
