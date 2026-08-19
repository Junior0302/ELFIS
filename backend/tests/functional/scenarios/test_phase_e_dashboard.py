"""Phase E — Dashboard (DASH-001…003) + ADMIN accès."""

from __future__ import annotations

from tests.functional.helpers.phase_e import assert_safe_admin_body


def test_admin_001_platform_admin_authorized(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/dashboard?period=24h", headers=api._headers())
    assert r.status_code == 200
    assert_safe_admin_body(r.json())


def test_admin_002_org_admin_refused(api):
    api.login_user("org_admin")
    r = api.client.get("/api/platform/dashboard?period=24h", headers=api._headers())
    assert r.status_code in (401, 403)


def test_admin_003_member_refused(api):
    api.login_user("member")
    r = api.client.get("/api/platform/dashboard?period=24h", headers=api._headers())
    assert r.status_code in (401, 403)


def test_dash_001_24h(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/dashboard?period=24h", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_admin_body(body)
    assert body.get("organizations_total", 0) >= 1 or "organizations" in body


def test_dash_002_7d(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/dashboard?period=7d", headers=api._headers())
    assert r.status_code == 200
    assert_safe_admin_body(r.json())


def test_dash_003_30d_and_invalid(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/dashboard?period=30d", headers=api._headers())
    assert r.status_code == 200
    assert_safe_admin_body(r.json())
    bad = api.client.get("/api/platform/dashboard?period=99y", headers=api._headers())
    assert bad.status_code in (200, 400, 422)
