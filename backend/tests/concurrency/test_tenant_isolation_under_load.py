"""CONC-008 — Isolation tenant sous charge légère."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import uuid4

from app.services.auth import create_access_token
from tests.functional.helpers.phase_a import seed_search_document


def _auth_headers(seed: dict[str, Any], user_key: str) -> dict[str, str]:
    info = seed["users"][user_key]
    org_id = info.get("org_id")
    token = create_access_token({"sub": str(info["id"]), "org_id": org_id})
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": str(org_id),
        "X-Request-Id": f"conc-008-{user_key}-{uuid4()}",
    }


def test_conc_008_tenant_isolation_under_load(concurrency_db):
    Session = concurrency_db["Session"]
    seed = concurrency_db["seed"]
    client = concurrency_db["client"]
    org_a = seed["organizations"]["ORG_ACTIVE"]["id"]
    org_b = seed["organizations"]["ORG_SECOND_TENANT"]["id"]
    db = Session()
    try:
        seed_search_document(db, org_id=org_a, unique_term="TENANT_A_ONLY_PHASE_F")
        seed_search_document(db, org_id=org_b, unique_term="TENANT_B_ONLY_PHASE_F")
    finally:
        db.close()

    def search_as(user_key: str, term: str):
        headers = _auth_headers(seed, user_key)
        r = client.get(f"/api/search?q={term}", headers=headers)
        body: Any
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:1000]}
        return user_key, term, r.status_code, body

    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [
            pool.submit(search_as, "org_admin", "TENANT_A_ONLY_PHASE_F"),
            pool.submit(search_as, "other_tenant", "TENANT_B_ONLY_PHASE_F"),
            pool.submit(search_as, "org_admin", "TENANT_B_ONLY_PHASE_F"),
            pool.submit(search_as, "other_tenant", "TENANT_A_ONLY_PHASE_F"),
        ]
        results = [f.result() for f in futs]

    for user_key, term, status, body in results:
        assert status == 200, f"search infra failure for {user_key}/{term}: HTTP {status} body={body}"
        blob = str(body)
        if user_key == "org_admin" and term == "TENANT_B_ONLY_PHASE_F":
            assert "TENANT_B_ONLY_PHASE_F" not in blob or body.get("total", 0) == 0 or not body.get("items")
        if user_key == "other_tenant" and term == "TENANT_A_ONLY_PHASE_F":
            assert "TENANT_A_ONLY_PHASE_F" not in blob or body.get("total", 0) == 0 or not body.get("items")
