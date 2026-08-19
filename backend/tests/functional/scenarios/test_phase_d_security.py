"""Phase D — Sécurité Delivery / accounting."""

from __future__ import annotations

from tests.functional.helpers.phase_b import enable_enforcement, disable_enforcement
from tests.functional.helpers.phase_d import (
    assert_safe_phase_d_body,
    install_mock_mailer,
    seed_sales_doc,
)


def test_sec_001_mass_assignment_org_id(api, functional_db, mock_vault_storage, monkeypatch):
    install_mock_mailer(monkeypatch)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    foreign = functional_db["seed"]["organizations"]["ORG_SECOND_TENANT"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id)
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("org_admin")
    r = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json={
            "recipient": "client@test.elfis.local",
            "subject": "x",
            "organization_id": foreign,
            "send_mode": "server",
        },
    )
    # organization_id dans body ignoré — envoi sur org du contexte
    assert r.status_code in (200, 201, 400, 422)
    if r.status_code in (200, 201):
        assert_safe_phase_d_body(r.json())


def test_sec_002_cross_tenant_attachment(api, functional_db, mock_vault_storage, monkeypatch):
    install_mock_mailer(monkeypatch)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id)
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("other_tenant")
    r = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json={"recipient": "x@test.elfis.local", "subject": "x", "send_mode": "server"},
    )
    assert r.status_code in (403, 404)


def test_sec_003_mail_entitlement_quota(api, functional_db, mock_vault_storage, monkeypatch):
    enable_enforcement(monkeypatch, entitlements=True, quotas=True)
    install_mock_mailer(monkeypatch)
    Session = functional_db["Session"]
    # Org expired — email.send devrait être refusé
    org_id = functional_db["seed"]["organizations"]["ORG_EXPIRED"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id)
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("expired")
    r = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json={"recipient": "x@test.elfis.local", "subject": "x", "send_mode": "server"},
    )
    assert r.status_code in (402, 403, 429)
    assert_safe_phase_d_body(r.json())
    disable_enforcement(monkeypatch)


def test_sec_unauthenticated_send(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id)
        doc_id = doc.id
    finally:
        db.close()

    r = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        json={"recipient": "x@test.elfis.local", "subject": "x", "send_mode": "server"},
    )
    assert r.status_code in (401, 403)
