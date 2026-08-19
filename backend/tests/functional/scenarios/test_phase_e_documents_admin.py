"""Phase E — Documents admin (DOCADMIN-001…002)."""

from __future__ import annotations

from tests.functional.helpers.phase_a import seed_vault_document
from tests.functional.helpers.phase_e import assert_safe_admin_body


def test_docadmin_001_list_filtered(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        seed_vault_document(db, org_id=org_id, marker="PHASEE")
    finally:
        db.close()

    api.login_user("platform_admin")
    r = api.client.get(
        f"/api/platform/vault-documents?organization_id={org_id}&page=1&page_size=20",
        headers=api._headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert_safe_admin_body(body)


def test_docadmin_002_no_pdf_exposed(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        doc = seed_vault_document(db, org_id=org_id, marker="NOPDF")
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("platform_admin")
    r = api.client.get(f"/api/platform/vault-documents/{doc_id}", headers=api._headers())
    assert r.status_code in (200, 404), r.text
    if r.status_code == 200:
        body = r.json()
        assert_safe_admin_body(body)
        blob = str(body).lower()
        assert "pdf_bytes" not in blob
        assert "%pdf" not in blob
        # storage key interne non exposée en clair si scrubbing
        assert "supabase" not in blob
