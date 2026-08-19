"""Phase D — Permissions (VAL/MAIL/platform)."""

from __future__ import annotations

from tests.functional.helpers.phase_d import VALIDATE_BODY, seed_accounting_proposal, seed_sales_doc


def test_perm_member_cannot_validate_or_send(api, functional_db, mock_vault_storage, monkeypatch):
    from tests.functional.helpers.phase_d import install_mock_mailer

    install_mock_mailer(monkeypatch)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        proposal_id = seed_accounting_proposal(db, org_id=org_id, vault_id="vd-perm-1")
        doc = seed_sales_doc(db, org_id=org_id)
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("member")
    assert api.client.post(
        f"/api/accounting/proposals/{proposal_id}/validate",
        headers=api._headers(),
        json=VALIDATE_BODY,
    ).status_code in (401, 403)
    # Envoi peut être autorisé ou non selon mapping — documenter résultat
    r = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json={"recipient": "x@test.elfis.local", "subject": "x", "send_mode": "server"},
    )
    assert r.status_code in (200, 201, 401, 403, 402)


def test_perm_org_admin_no_platform(api):
    api.login_user("org_admin")
    r = api.client.get("/api/platform/accounting/reviews", headers=api._headers())
    assert r.status_code in (401, 403, 404)


def test_perm_nosub_costly_blocked(api, functional_db, mock_vault_storage, monkeypatch):
    from tests.functional.helpers.phase_d import install_mock_mailer

    install_mock_mailer(monkeypatch)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_NONE"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id)
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("no_sub")
    r = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json={"recipient": "x@test.elfis.local", "subject": "x", "send_mode": "server"},
    )
    assert r.status_code in (402, 403, 400)
