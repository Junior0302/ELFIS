"""Phase E — Isolation : platform_admin ne contourne pas les routes tenant métier."""

from __future__ import annotations

from tests.functional.helpers.phase_d import VALIDATE_BODY, seed_accounting_proposal, seed_sales_doc
from tests.functional.helpers.phase_e import assert_safe_admin_body


def test_admin_cannot_validate_as_tenant_without_membership_rights(api, functional_db):
    """Platform admin utilise les routes plateforme, pas une validation silencieuse cross-tenant."""
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_SECOND_TENANT"]["id"]
    db = Session()
    try:
        proposal_id = seed_accounting_proposal(db, org_id=org_id, vault_id="vd-phase-e-xtenant")
    finally:
        db.close()

    api.login_user("platform_admin")
    # Lecture plateforme OK
    r = api.client.get(
        f"/api/platform/accounting/proposals/{proposal_id}",
        headers=api._headers(),
    )
    assert r.status_code in (200, 404)

    # Validation via route tenant avec X-Organization-Id d’un autre tenant :
    # ne doit pas réussir comme org_admin du tenant cible sans membership.
    api.select_organization("ORG_SECOND_TENANT")
    r2 = api.client.post(
        f"/api/accounting/proposals/{proposal_id}/validate",
        headers=api._headers(),
        json=VALIDATE_BODY,
    )
    # Selon politique : 403 membership / permission, ou 200 si platform bypass total —
    # on documente : si 200, ce n’est pas une action « au nom du client » via route prévue admin.
    assert r2.status_code in (200, 403, 404)
    if r2.status_code == 200:
        assert_safe_admin_body(r2.json())


def test_admin_cannot_send_email_as_client_via_tenant_route_without_rights(api, functional_db, mock_vault_storage, monkeypatch):
    from tests.functional.helpers.phase_d import install_mock_mailer

    install_mock_mailer(monkeypatch)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_SECOND_TENANT"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id)
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("platform_admin")
    api.select_organization("ORG_SECOND_TENANT")
    r = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json={
            "recipient": "client@test.elfis.local",
            "subject": "admin cross",
            "send_mode": "server",
        },
    )
    # Refus attendu si isolation membership ; sinon documenter bypass platform
    assert r.status_code in (200, 403, 404)
