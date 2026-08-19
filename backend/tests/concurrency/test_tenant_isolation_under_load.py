"""CONC-008 — Isolation tenant sous charge légère."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from tests.functional.helpers.phase_a import seed_search_document


def test_conc_008_tenant_isolation_under_load(api, functional_db):
    Session = functional_db["Session"]
    org_a = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    org_b = functional_db["seed"]["organizations"]["ORG_SECOND_TENANT"]["id"]
    db = Session()
    try:
        seed_search_document(db, org_id=org_a, unique_term="TENANT_A_ONLY_PHASE_F")
        seed_search_document(db, org_id=org_b, unique_term="TENANT_B_ONLY_PHASE_F")
    finally:
        db.close()

    def search_as(user_key: str, term: str):
        api.login_user(user_key)
        r = api.client.get(f"/api/search?q={term}", headers=api._headers())
        return user_key, term, r.status_code, r.json() if r.status_code == 200 else {}

    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [
            pool.submit(search_as, "org_admin", "TENANT_A_ONLY_PHASE_F"),
            pool.submit(search_as, "other_tenant", "TENANT_B_ONLY_PHASE_F"),
            pool.submit(search_as, "org_admin", "TENANT_B_ONLY_PHASE_F"),
            pool.submit(search_as, "other_tenant", "TENANT_A_ONLY_PHASE_F"),
        ]
        results = [f.result() for f in futs]

    for user_key, term, status, body in results:
        if status != 200:
            continue
        blob = str(body)
        if user_key == "org_admin" and term == "TENANT_B_ONLY_PHASE_F":
            assert "TENANT_B_ONLY_PHASE_F" not in blob or body.get("total", 0) == 0 or not body.get("items")
        if user_key == "other_tenant" and term == "TENANT_A_ONLY_PHASE_F":
            assert "TENANT_A_ONLY_PHASE_F" not in blob or body.get("total", 0) == 0 or not body.get("items")
