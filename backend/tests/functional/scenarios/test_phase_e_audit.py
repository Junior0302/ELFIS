"""Phase E — Audit (AUDIT-001…003)."""

from __future__ import annotations

from tests.functional.helpers.phase_e import REASON, assert_safe_admin_body


def test_audit_001_sensitive_action_logged(api, functional_db):
    orgs = functional_db["seed"]["organizations"]
    org_id = orgs.get("ORG_QUOTA_FULL", orgs.get("ORG_TRIAL", orgs["ORG_ACTIVE"]))["id"]
    api.login_user("platform_admin")
    api.client.post(
        f"/api/platform/organizations/{org_id}/suspend",
        headers=api._headers(),
        json={"reason": REASON},
    )
    r = api.client.get("/api/platform/audit?page=1&page_size=50", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_admin_body(body)
    audits = body.get("audits") or body.get("items") or body.get("results") or []
    actions = {a.get("action") for a in audits if isinstance(a, dict)}
    assert "organization.suspend" in actions or any("suspend" in str(a) for a in audits)
    # restore
    api.client.post(
        f"/api/platform/organizations/{org_id}/restore",
        headers=api._headers(),
        json={"reason": REASON},
    )


def test_audit_002_immutable_via_api(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/audit?page=1&page_size=5", headers=api._headers())
    assert r.status_code == 200
    audits = r.json().get("audits") or r.json().get("items") or []
    if not audits:
        return
    aid = audits[0].get("audit_id") or audits[0].get("id")
    for method, path in (
        ("patch", f"/api/platform/audit/{aid}"),
        ("put", f"/api/platform/audit/{aid}"),
        ("delete", f"/api/platform/audit/{aid}"),
    ):
        resp = getattr(api.client, method)(
            path,
            headers=api._headers(),
            json={"reason": "tamper", "actor_id": 1},
        )
        assert resp.status_code in (404, 405, 401, 403)


def test_audit_003_payload_filtered(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/audit?page=1&page_size=20", headers=api._headers())
    assert r.status_code == 200
    assert_safe_admin_body(r.json())
