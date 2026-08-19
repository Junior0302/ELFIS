"""Phase E — Sécurité admin (SEC-001…003)."""

from __future__ import annotations

from tests.functional.helpers.phase_a import mint_token
from tests.functional.helpers.phase_e import REASON, assert_safe_admin_body


def test_sec_001_mass_assignment_ignored(api, functional_db):
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    api.login_user("platform_admin")
    r = api.client.post(
        f"/api/platform/organizations/{org_id}/suspend",
        headers=api._headers(),
        json={
            "reason": REASON,
            "is_platform_admin": True,
            "role": "owner",
            "platform_status": "closed",
            "actor_id": 99999,
            "stripe_customer_id": "cus_evil",
        },
    )
    # raison valide → 200 ou 400 (déjà suspendu) ; champs extra ignorés (Pydantic)
    assert r.status_code in (200, 400, 422)
    if r.status_code == 200:
        assert r.json().get("platform_status") == "suspended"
        api.client.post(
            f"/api/platform/organizations/{org_id}/restore",
            headers=api._headers(),
            json={"reason": REASON},
        )


def test_sec_002_error_filtered(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/organizations/999999999/ops-detail", headers=api._headers())
    assert r.status_code in (404, 400)
    body = r.json()
    assert_safe_admin_body(body)
    blob = str(body).lower()
    assert "traceback" not in blob
    assert "sqlalchemy" not in blob


def test_sec_003_unauthenticated_and_invalid_token(api):
    r = api.client.get("/api/platform/dashboard")
    assert r.status_code in (401, 403)

    bad = mint_token(sub=1, org_id=1, secret="wrong-secret-key-phase-e")
    r2 = api.client.get(
        "/api/platform/dashboard",
        headers={"Authorization": f"Bearer {bad}"},
    )
    assert r2.status_code in (401, 403)


def test_sec_client_cannot_self_elevate(api, functional_db):
    """Aucun champ is_admin=true client n’accorde le rôle plateforme."""
    api.login_user("member")
    r = api.client.get(
        "/api/platform/dashboard",
        headers=api._headers({"X-Is-Platform-Admin": "true"}),
    )
    assert r.status_code in (401, 403)
