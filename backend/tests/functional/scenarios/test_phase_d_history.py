"""Phase D — Historique comptable / delivery (HIST-001/002)."""

from __future__ import annotations

from tests.functional.helpers.phase_d import (
    VALIDATE_BODY,
    assert_safe_phase_d_body,
    install_mock_mailer,
    seed_accounting_proposal,
    seed_sales_doc,
)


def test_hist_001_proposal_detail_includes_reviews(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        proposal_id = seed_accounting_proposal(db, org_id=org_id, vault_id="vd-hist-1")
    finally:
        db.close()

    api.login_user("org_admin")
    api.client.post(
        f"/api/accounting/proposals/{proposal_id}/validate",
        headers=api._headers(),
        json=VALIDATE_BODY,
    )
    r = api.client.get(f"/api/accounting/proposals/{proposal_id}", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_phase_d_body(body)
    # reviews dans détail
    reviews = body.get("reviews") or body.get("history") or []
    assert isinstance(reviews, list)
    blob = str(body).lower()
    assert "openai" not in blob
    assert "prompt" not in blob


def test_hist_002_email_logs_on_document(api, functional_db, mock_vault_storage, monkeypatch):
    install_mock_mailer(monkeypatch)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id)
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("org_admin")
    api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json={
            "recipient": "client@test.elfis.local",
            "subject": "hist",
            "send_mode": "server",
            "idempotency_key": "phase-d-hist-mail",
        },
    )
    r = api.client.get(f"/api/billing/documents/{doc_id}", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_phase_d_body(body)
    logs = body.get("email_logs") or body.get("emails") or []
    assert isinstance(logs, list)
    blob = str(logs).lower()
    assert "xkeysib" not in blob
    assert "password" not in blob
