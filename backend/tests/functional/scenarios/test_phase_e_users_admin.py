"""Phase E — Utilisateurs admin (USERADMIN-001…004)."""

from __future__ import annotations

from app.services.auth import create_access_token
from tests.functional.helpers.phase_e import REASON, assert_safe_admin_body


def test_useradmin_001_list(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/users", headers=api._headers())
    assert r.status_code == 200
    assert_safe_admin_body(r.json())
    blob = str(r.json()).lower()
    assert "password_hash" not in blob


def test_useradmin_002_003_disable_blocks_token(api, functional_db):
    user = functional_db["seed"]["users"]["member"]
    uid = user["id"]
    org_id = user.get("org_id")
    api.login_user("platform_admin")
    r = api.client.post(
        f"/api/platform/users/{uid}/disable",
        headers=api._headers(),
        json={"reason": REASON},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("status") in ("suspended", "disabled", "inactive")

    token = create_access_token({"sub": str(uid), "org_id": org_id})
    me = api.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code in (401, 403)

    api.login_user("platform_admin")
    en = api.client.post(
        f"/api/platform/users/{uid}/enable",
        headers=api._headers(),
        json={"reason": REASON},
    )
    assert en.status_code == 200


def test_useradmin_004_enable_reason_required(api, functional_db):
    uid = functional_db["seed"]["users"]["member"]["id"]
    api.login_user("platform_admin")
    bad = api.client.post(
        f"/api/platform/users/{uid}/enable",
        headers=api._headers(),
        json={"reason": "x"},
    )
    assert bad.status_code == 422
