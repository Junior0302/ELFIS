"""Phase A — Réponses sécurité / corrélation (SEC-001 … SEC-006)."""

from __future__ import annotations

from tests.functional.helpers.phase_a import assert_safe_error_body


def test_sec_001_002_003_004_normalized_error(api):
    r = api.client.get("/api/platform/dashboard")
    assert r.status_code in (401, 403)
    body = r.json()
    assert "error" in body
    err = body["error"]
    assert err.get("code")
    assert err.get("message")
    assert err.get("request_id")
    assert err.get("correlation_id")
    assert r.headers.get("X-Request-Id")
    assert r.headers.get("X-Correlation-Id")
    assert_safe_error_body(body)
    assert "traceback" not in str(body).lower()


def test_sec_002_003_generated_ids(api):
    r = api.client.get("/api/health/live")
    assert r.status_code == 200
    assert r.headers.get("X-Request-Id")
    assert r.headers.get("X-Correlation-Id")
    assert r.headers["X-Request-Id"] == r.headers["X-Correlation-Id"]


def test_sec_correlation_preserved(api):
    rid = "phase-a-req-id-123456"
    cid = "phase-a-corr-id-654321"
    r = api.client.get(
        "/api/health/live",
        headers={"X-Request-Id": rid, "X-Correlation-Id": cid},
    )
    assert r.headers.get("X-Request-Id") == rid
    assert r.headers.get("X-Correlation-Id") == cid


def test_sec_invalid_request_id_replaced(api):
    r = api.client.get("/api/health/live", headers={"X-Request-Id": "bad"})
    assert r.headers.get("X-Request-Id") != "bad"
    assert len(r.headers.get("X-Request-Id") or "") >= 8


def test_sec_005_cross_tenant_event_filtered(api, functional_db):
    from tests.document_intelligence import make_text_pdf

    api.login_user("org_admin")
    foreign = functional_db["seed"]["organizations"]["ORG_SECOND_TENANT"]["id"]
    api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("ok.pdf", make_text_pdf("x"), "application/pdf")},
        data={"tenant_id": str(foreign), "document_type": "supplier_invoice"},
    )
    Session = functional_db["Session"]
    db = Session()
    try:
        from app.security.security_models import ElfisSecurityEvent

        rows = db.query(ElfisSecurityEvent).all()
        for row in rows:
            blob = str(row.details or {}).lower()
            assert "password" not in blob
            assert "authorization" not in blob
            assert "bearer" not in blob
    finally:
        db.close()


def test_sec_006_no_debug_routes_in_simulated_production(api, monkeypatch):
    from app.config import settings

    prev = settings.app_env
    try:
        settings.app_env = "production"
        settings.elfis_environment = "production"
        for path in (
            "/api/debug",
            "/api/test/seed",
            "/api/test/reset",
            "/api/functional/outbox",
            "/api/dev/jwt",
        ):
            r = api.client.get(path)
            assert r.status_code in (404, 405, 401, 403)
    finally:
        settings.app_env = prev
        settings.elfis_environment = "test"


def test_sec_plan_catalog_is_public(api):
    """Route volontairement publique documentée."""
    r = api.client.get("/api/auth/plan-catalog")
    assert r.status_code == 200
