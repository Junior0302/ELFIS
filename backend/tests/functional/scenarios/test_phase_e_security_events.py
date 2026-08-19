"""Phase E — Security events (SECADMIN-001…002)."""

from __future__ import annotations

from tests.functional.helpers.phase_e import assert_safe_admin_body


def test_secadmin_001_visible_admin(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/security/events?limit=50", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_admin_body(body)
    blob = str(body).lower()
    assert "password=" not in blob
    assert "bearer eyj" not in blob


def test_secadmin_002_org_admin_refused(api):
    api.login_user("org_admin")
    r = api.client.get("/api/platform/security/events", headers=api._headers())
    assert r.status_code in (401, 403)


def test_secadmin_configuration_no_secrets(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/security/configuration", headers=api._headers())
    assert r.status_code == 200
    assert_safe_admin_body(r.json())
