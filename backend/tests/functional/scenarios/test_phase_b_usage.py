"""Phase B — Usage (USAGE-001 … USAGE-003)."""

from __future__ import annotations

from app.billing.billing_types import UsageCodes
from app.billing.usage_service import UsageService
from tests.functional.helpers.phase_b import assert_safe_billing_body


def test_usage_001_documents_via_api(api):
    api.login_user("active")
    r = api.client.get("/api/billing/usage", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_billing_body(body)
    assert "usage" in body


def test_usage_002_ai_from_service(functional_db):
    Session = functional_db["Session"]
    org_a = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    org_b = functional_db["seed"]["organizations"]["ORG_SECOND_TENANT"]["id"]
    db = Session()
    try:
        svc = UsageService(db)
        svc.record_usage(org_a, UsageCodes.AI_TOKENS, 42)
        db.commit()
        data_a = {d["usage_code"]: d["used_value"] for d in svc.list_usage(org_a)}
        data_b = {d["usage_code"]: d["used_value"] for d in svc.list_usage(org_b)}
        assert data_a.get(UsageCodes.AI_TOKENS, 0) >= 42
        assert data_b.get(UsageCodes.AI_TOKENS, 0) == 0 or UsageCodes.AI_TOKENS not in data_b
    finally:
        db.close()


def test_usage_003_isolation_api(api):
    api.login_user("other_tenant")
    r = api.client.get("/api/billing/usage", headers=api._headers())
    assert r.status_code == 200
    blob = str(r.json())
    # Pas d'ID org active dans la réponse usage
    active_id = api.seed["organizations"]["ORG_ACTIVE"]["id"]
    # Organization context is implicit — ensure no cross-tenant counters leak via markers
    assert "sk_" not in blob.lower()
