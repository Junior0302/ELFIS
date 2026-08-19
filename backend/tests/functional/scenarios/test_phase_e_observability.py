"""Phase E — Observabilité (OBS-001…002)."""

from __future__ import annotations

from tests.functional.helpers.phase_e import assert_safe_admin_body


def test_obs_001_platform_metrics(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/observability/metrics", headers=api._headers())
    assert r.status_code == 200
    assert_safe_admin_body(r.json())


def test_obs_002_no_secrets_in_metrics(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/observability/metrics", headers=api._headers())
    assert r.status_code == 200
    blob = str(r.json()).lower()
    assert "sk_live" not in blob
    assert "xkeysib-" not in blob
    assert "jwt_secret" not in blob


def test_obs_metrics_public_policy(api):
    """/api/metrics : auth selon politique (token ou admin)."""
    r = api.client.get("/api/metrics")
    assert r.status_code in (200, 401, 403, 404)
    if r.status_code == 200:
        assert_safe_admin_body(r.json())
