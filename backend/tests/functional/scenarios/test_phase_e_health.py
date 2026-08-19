"""Phase E — Health checks (HEALTH-001…003)."""

from __future__ import annotations

from tests.functional.helpers.phase_e import assert_safe_admin_body


def test_health_001_live(api):
    r = api.client.get("/api/health/live")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") in ("ok", "up", "alive") or body.get("check") == "live"


def test_health_002_ready(api):
    r = api.client.get("/api/health/ready")
    assert r.status_code in (200, 503)
    body = r.json()
    assert "status" in body or "ready" in str(body).lower()


def test_health_003_details_admin(api):
    api.login_user("org_admin")
    denied = api.client.get("/api/health/details", headers=api._headers())
    assert denied.status_code in (401, 403)

    api.login_user("platform_admin")
    r = api.client.get("/api/health/details", headers=api._headers())
    assert r.status_code == 200
    assert_safe_admin_body(r.json())


def test_health_services_admin(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/health/services", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_admin_body(body)
    services = body.get("services") or []
    names = {s.get("service") or s.get("name") for s in services if isinstance(s, dict)}
    assert "database" in names or any("database" in str(s).lower() for s in services)


def test_health_legacy_compatible(api):
    r = api.client.get("/api/health")
    assert r.status_code == 200
