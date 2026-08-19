"""SCENARIO 9/10 — Org suspendue + Platform Admin."""

from __future__ import annotations


def test_suspended_org_write_blocked(api):
    api.login_user("suspended")
    from tests.document_intelligence import make_text_pdf

    content = make_text_pdf("test")
    r = api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("a.pdf", content, "application/pdf")},
        data={"tenant_id": str(api.org_id), "document_type": "supplier_invoice"},
    )
    # Lecture OK potentiellement ; écriture refusée (403 organization_suspended) ou 402
    assert r.status_code in (403, 402, 400)
    body = r.json()
    detail = body.get("error") or body.get("detail") or {}
    if isinstance(detail, dict):
        code = detail.get("code") or body.get("error", {}).get("code")
        assert code in {
            "organization_suspended",
            "subscription_inactive",
            "subscription_required",
            "permission_denied",
            "feature_not_available",
            "unsupported_file_type",
            None,
        } or r.status_code in (403, 402)


def test_platform_admin_dashboard(api):
    api.login_user("platform_admin")
    dash = api.get_admin_dashboard()
    assert isinstance(dash, dict)


def test_platform_security_configuration(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/security/configuration", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert "environment" in body or "protections" in body
    blob = str(body).lower()
    assert "sk_live" not in blob
    assert "password" not in blob or "configured" in blob
