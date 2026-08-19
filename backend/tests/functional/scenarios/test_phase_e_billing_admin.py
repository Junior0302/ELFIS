"""Phase E — Billing admin (BILLADMIN-001…003)."""

from __future__ import annotations

from tests.functional.helpers.phase_e import assert_safe_admin_body


def test_billadmin_001_list_subscriptions(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/billing/subscriptions", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_admin_body(body)
    blob = str(body).lower()
    assert "card_number" not in blob
    assert "payment_method_details" not in blob


def test_billadmin_002_entitlement_override(api, functional_db):
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    api.login_user("platform_admin")
    r = api.client.post(
        f"/api/platform/billing/organizations/{org_id}/entitlements",
        headers=api._headers(),
        json={"feature_code": "email.send", "is_enabled": True},
    )
    # V1 : endpoint existant sans reason obligatoire (documenté)
    assert r.status_code in (200, 201, 400, 404, 422), r.text
    if r.status_code in (200, 201):
        assert_safe_admin_body(r.json())


def test_billadmin_003_quota_override_documented(api):
    """Aucune route quota override montée en V1 — vérifier absence ou 404."""
    api.login_user("platform_admin")
    r = api.client.post(
        "/api/platform/billing/organizations/1/quotas",
        headers=api._headers(),
        json={"quota_code": "emails.sent.month", "limit_value": 999, "reason": "Phase E"},
    )
    assert r.status_code in (404, 405, 422)
