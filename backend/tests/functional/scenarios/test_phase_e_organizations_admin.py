"""Phase E — Organisations admin (ORGADMIN-001…005)."""

from __future__ import annotations

from tests.functional.helpers.phase_e import REASON, assert_safe_admin_body, count_admin_audits


def test_orgadmin_001_list(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/organizations", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_admin_body(body)
    blob = str(body).lower()
    assert "sk_live" not in blob


def test_orgadmin_002_detail(api, functional_db):
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    api.login_user("platform_admin")
    r = api.client.get(
        f"/api/platform/organizations/{org_id}/ops-detail",
        headers=api._headers(),
    )
    assert r.status_code == 200
    body = r.json()
    assert_safe_admin_body(body)
    assert "pdf_bytes" not in str(body).lower()
    assert "storage_path" not in str(body).lower() or "storage_key" not in str(body).lower()


def test_orgadmin_003_004_suspend(api, functional_db):
    Session = functional_db["Session"]
    orgs = functional_db["seed"]["organizations"]
    org_id = orgs.get("ORG_QUOTA_NEAR", orgs.get("ORG_TRIAL", orgs["ORG_ACTIVE"]))["id"]

    api.login_user("platform_admin")
    bad = api.client.post(
        f"/api/platform/organizations/{org_id}/suspend",
        headers=api._headers(),
        json={"reason": "ab"},
    )
    assert bad.status_code == 422

    r = api.client.post(
        f"/api/platform/organizations/{org_id}/suspend",
        headers=api._headers(),
        json={"reason": REASON},
    )
    assert r.status_code in (200, 400), r.text
    if r.status_code == 200:
        assert r.json().get("platform_status") == "suspended"
        db = Session()
        try:
            assert count_admin_audits(db, action="organization.suspend") >= 1
        finally:
            db.close()
        api.client.post(
            f"/api/platform/organizations/{org_id}/restore",
            headers=api._headers(),
            json={"reason": REASON},
        )


def test_orgadmin_005_restore(api, functional_db):
    org_id = functional_db["seed"]["organizations"]["ORG_SUSPENDED"]["id"]
    api.login_user("platform_admin")
    r = api.client.post(
        f"/api/platform/organizations/{org_id}/restore",
        headers=api._headers(),
        json={"reason": REASON},
    )
    assert r.status_code == 200
    assert r.json().get("platform_status") == "active"
    # rétablir l’état seed suspendu pour les autres scénarios
    api.client.post(
        f"/api/platform/organizations/{org_id}/suspend",
        headers=api._headers(),
        json={"reason": "Phase E — rétablir état seed suspendu"},
    )
