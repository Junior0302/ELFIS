"""Phase A — Rôles (ROLE-001 … ROLE-004)."""

from __future__ import annotations

from tests.functional.helpers.phase_a import assert_safe_error_body

PLATFORM_GETS = (
    "/api/platform/dashboard",
    "/api/platform/health/services",
    "/api/platform/organizations",
    "/api/platform/users",
    "/api/platform/incidents",
    "/api/platform/audit",
    "/api/platform/security/events",
    "/api/platform/observability/metrics",
    "/api/platform/reliability/readiness",
)


def test_role_001_platform_admin_access(api):
    api.login_user("platform_admin")
    for path in PLATFORM_GETS:
        r = api.client.get(path, headers=api._headers())
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"
        blob = str(r.json()).lower()
        assert "sk_live" not in blob
        assert "whsec_" not in blob or "configured" in blob


def test_role_002_org_admin_refused_platform(api):
    api.login_user("org_admin")
    for path in PLATFORM_GETS[:4]:
        r = api.client.get(path, headers=api._headers())
        assert r.status_code in (401, 403), path
        assert_safe_error_body(r.json())


def test_role_003_member_refused_platform_and_admin_actions(api, functional_db):
    api.login_user("member")
    r = api.client.get("/api/platform/dashboard", headers=api._headers())
    assert r.status_code in (401, 403)

    # Suspend org — interdit
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    r2 = api.client.post(
        f"/api/platform/organizations/{org_id}/suspend",
        headers=api._headers(),
        json={"reason": "tentative membre"},
    )
    assert r2.status_code in (401, 403)


def test_role_004_member_read_allowed(api):
    api.login_user("member")
    r = api.client.get("/api/auth/me", headers=api._headers())
    assert r.status_code == 200
    assert r.json()["role"] in ("employe", "member", "admin", "owner") or r.json().get("role")


def test_role_org_admin_not_platform_flag(api):
    api.login_user("org_admin")
    me = api.client.get("/api/auth/me", headers=api._headers()).json()
    user = me.get("user") or {}
    assert user.get("is_platform_admin") in (False, 0, None)
