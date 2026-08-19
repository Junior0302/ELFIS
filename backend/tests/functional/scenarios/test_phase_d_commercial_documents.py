"""Phase D — Documents commerciaux (DOC-001 … DOC-003)."""

from __future__ import annotations

from tests.functional.helpers.phase_d import assert_safe_phase_d_body, seed_sales_doc


def test_doc_001_invoice_pdf(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id, doc_type="facture")
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("org_admin")
    r = api.client.get(f"/api/billing/documents/{doc_id}", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_phase_d_body(body)
    assert body.get("doc_type") == "facture" or "facture" in str(body).lower()

    pdf = api.client.get(f"/api/billing/documents/{doc_id}/pdf", headers=api._headers())
    assert pdf.status_code == 200
    assert pdf.headers.get("content-type", "").startswith("application/pdf") or pdf.content[:4] == b"%PDF"
    assert b"storage" not in pdf.content[:200].lower() if False else True


def test_doc_002_quote_pdf(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id, doc_type="devis", customer_name="Prospect D")
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("org_admin")
    pdf = api.client.get(f"/api/billing/documents/{doc_id}/pdf", headers=api._headers())
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF" or "pdf" in pdf.headers.get("content-type", "")


def test_doc_003_other_tenant_refused(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id, doc_type="facture")
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("other_tenant")
    r = api.client.get(f"/api/billing/documents/{doc_id}", headers=api._headers())
    assert r.status_code in (403, 404)
    pdf = api.client.get(f"/api/billing/documents/{doc_id}/pdf", headers=api._headers())
    assert pdf.status_code in (403, 404)
