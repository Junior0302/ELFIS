"""Phase D — Idempotence Delivery / validation."""

from __future__ import annotations

from tests.functional.helpers.phase_d import (
    VALIDATE_BODY,
    install_mock_mailer,
    seed_accounting_proposal,
    seed_sales_doc,
)


def test_idemp_001_double_click_send(api, functional_db, mock_vault_storage, monkeypatch):
    calls = install_mock_mailer(monkeypatch)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id)
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("org_admin")
    payload = {
        "recipient": "client@test.elfis.local",
        "subject": "dbl",
        "send_mode": "server",
        "idempotency_key": "phase-d-dbl-click",
    }
    r1 = api.client.post(f"/api/billing/documents/{doc_id}/email", headers=api._headers(), json=payload)
    r2 = api.client.post(f"/api/billing/documents/{doc_id}/email", headers=api._headers(), json=payload)
    assert r1.status_code in (200, 201)
    assert r2.status_code in (200, 201)
    assert len(calls) == 1


def test_idemp_validation_double(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        proposal_id = seed_accounting_proposal(db, org_id=org_id, vault_id="vd-idemp-val-d2")
    finally:
        db.close()

    api.login_user("org_admin")
    for _ in range(2):
        r = api.client.post(
            f"/api/accounting/proposals/{proposal_id}/validate",
            headers=api._headers(),
            json=VALIDATE_BODY,
        )
        assert r.status_code in (200, 201)
