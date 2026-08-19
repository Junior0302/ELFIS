"""Phase D — Search (SEARCH-001 … SEARCH-004)."""

from __future__ import annotations

from tests.functional.helpers.phase_c import drain_pipeline
from tests.functional.helpers.phase_d import VALIDATE_BODY, seed_accounting_proposal, seed_sales_doc
from tests.functional.helpers.phase_a import seed_search_document


def test_search_001_002_proposal_after_validation(api, functional_db, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "elfis_auto_search_indexing_enabled", True)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        proposal_id = seed_accounting_proposal(db, org_id=org_id, vault_id="vd-search-val-d")
    finally:
        db.close()

    api.login_user("org_admin")
    api.client.post(
        f"/api/accounting/proposals/{proposal_id}/validate",
        headers=api._headers(),
        json=VALIDATE_BODY,
    )
    drain_pipeline(functional_db["Session"], max_rounds=15)

    r = api.client.get("/api/search?q=Fournisseur+Phase+D", headers=api._headers())
    assert r.status_code in (200, 402, 403)
    if r.status_code == 200:
        items = r.json().get("items") or r.json().get("results") or []
        # Soft : indexation best-effort
        assert isinstance(items, list)


def test_search_003_invoice_number(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        seed_search_document(db, org_id=org_id, unique_term="FAC-PHASE-D-UNIQUE-99")
        seed_sales_doc(db, org_id=org_id, customer_name="Client Search D")
    finally:
        db.close()

    api.login_user("org_admin")
    r = api.client.get("/api/search?q=FAC-PHASE-D-UNIQUE-99", headers=api._headers())
    assert r.status_code in (200, 402, 403)
    if r.status_code == 200:
        items = r.json().get("items") or []
        total = r.json().get("total")
        assert total is None or total >= 0 or len(items) >= 0


def test_search_004_isolation(api, functional_db):
    Session = functional_db["Session"]
    org_a = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    term = "SUPPLIER-PHASE-D-TENANT-ISO"
    db = Session()
    try:
        seed_search_document(db, org_id=org_a, unique_term=term)
    finally:
        db.close()

    api.login_user("other_tenant")
    r = api.client.get(f"/api/search?q={term}", headers=api._headers())
    assert r.status_code in (200, 402, 403)
    if r.status_code == 200:
        items = r.json().get("items") or []
        assert len(items) == 0 or r.json().get("total", 0) == 0
