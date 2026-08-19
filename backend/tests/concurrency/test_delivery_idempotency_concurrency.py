"""CONC-005 — Delivery double-clic même clé (séquentiel SQLite ; threads = Postgres)."""

from __future__ import annotations

from app.models_saas import DocumentEmailLog
from tests.functional.helpers.phase_d import install_mock_mailer, seed_sales_doc


def test_conc_005_delivery_idempotency_concurrency(api, functional_db, mock_vault_storage, monkeypatch):
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
        "recipient": "client.phase.f@test.elfis.local",
        "subject": "Concurrent Phase F",
        "body": "PJ",
        "send_mode": "server",
        "idempotency_key": "phase-f-conc-delivery-1",
    }
    r1 = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json=payload,
    )
    assert r1.status_code in (200, 201), r1.text
    r2 = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json=payload,
    )
    assert r2.status_code in (200, 201)
    assert r2.json().get("status") in ("sent", "already_sent")
    assert len(calls) == 1

    db = Session()
    try:
        logs = (
            db.query(DocumentEmailLog)
            .filter(DocumentEmailLog.idempotency_key == "phase-f-conc-delivery-1")
            .all()
        )
        assert len(logs) == 1
    finally:
        db.close()
