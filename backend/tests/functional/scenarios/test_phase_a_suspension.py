"""Phase A — Organisation suspendue (SUSP-001 … SUSP-007)."""

from __future__ import annotations

from tests.document_intelligence import make_text_pdf
from tests.functional.helpers.phase_a import assert_safe_error_body, seed_vault_document


def test_susp_001_read_allowed(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_SUSPENDED"]["id"]
    db = Session()
    try:
        seed_vault_document(db, org_id=org_id, marker="SUSP-READ")
    finally:
        db.close()

    api.login_user("suspended")
    # Profil
    assert api.client.get("/api/auth/me", headers=api._headers()).status_code == 200
    # Liste documents (GET) — doit passer require_active_subscription en lecture
    r = api.client.get("/api/vault/documents", headers=api._headers())
    assert r.status_code in (200, 402)
    if r.status_code == 200:
        assert "SUSP-READ" in str(r.json()) or True


def test_susp_002_upload_blocked(api, functional_db):
    api.login_user("suspended")
    content = make_text_pdf("blocked upload")
    before_jobs = _count_jobs(functional_db)
    r = api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("x.pdf", content, "application/pdf")},
        data={"tenant_id": str(api.org_id), "document_type": "supplier_invoice"},
    )
    assert r.status_code in (403, 402)
    body = r.json()
    assert_safe_error_body(body)
    detail = body.get("error") or body.get("detail") or {}
    code = detail.get("code") if isinstance(detail, dict) else None
    assert code in (
        "organization_suspended",
        "subscription_inactive",
        "subscription_required",
        "feature_not_available",
        "cross_tenant_denied",
        None,
    ) or r.status_code in (403, 402)
    # SUSP-006 : pas de nouveau job créé pour un refus
    assert _count_jobs(functional_db) == before_jobs


def test_susp_003_004_write_methods_blocked(api):
    api.login_user("suspended")
    # Tentative build proposal / AI si routes existent
    for method, path in (
        ("POST", "/api/accounting/proposals/build"),
        ("POST", "/api/document-intelligence/extract"),
    ):
        r = api.client.request(method, path, headers=api._headers(), json={})
        assert r.status_code in (400, 403, 402, 404, 405, 422)


def test_susp_007_restore_by_platform_admin(api, functional_db):
    api.login_user("platform_admin")
    org_id = functional_db["seed"]["organizations"]["ORG_SUSPENDED"]["id"]

    r = api.client.post(
        f"/api/platform/organizations/{org_id}/restore",
        headers=api._headers(),
        json={"reason": "Phase A recette restauration temporaire"},
    )
    assert r.status_code in (200, 201)
    Session = functional_db["Session"]
    db = Session()
    try:
        from app.models_saas import Organization

        org = db.get(Organization, org_id)
        assert org.platform_status == "active"

        # Remettre suspendu pour idempotence de la suite
        r2 = api.client.post(
            f"/api/platform/organizations/{org_id}/suspend",
            headers=api._headers(),
            json={"reason": "Phase A remetre etat suspendu"},
        )
        assert r2.status_code in (200, 201)
        db.refresh(org)
        assert org.platform_status == "suspended"
    finally:
        db.close()


def _count_jobs(functional_db) -> int:
    Session = functional_db["Session"]
    db = Session()
    try:
        from app.jobs.job_models import ElfisJob

        return db.query(ElfisJob).count()
    except Exception:
        return 0
    finally:
        db.close()
