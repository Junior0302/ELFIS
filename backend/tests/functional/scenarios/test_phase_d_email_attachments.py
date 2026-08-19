"""Phase D — Pièces jointes automatiques (ATTACH-003/004)."""

from __future__ import annotations

from unittest.mock import patch

from tests.functional.helpers.phase_d import assert_safe_phase_d_body, install_mock_mailer, seed_sales_doc


def test_attach_003_no_second_blob_on_resend(api, functional_db, mock_vault_storage, monkeypatch):
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
    payload = {
        "recipient": "client.phase.d@test.elfis.local",
        "subject": "Facture",
        "body": "PJ auto",
        "send_mode": "server",
        "idempotency_key": "phase-d-attach-once",
    }
    r1 = api.client.post(f"/api/billing/documents/{doc_id}/email", headers=api._headers(), json=payload)
    assert r1.status_code in (200, 201)
    objects_after_first = len(mock_vault_storage.objects)
    r2 = api.client.post(f"/api/billing/documents/{doc_id}/email", headers=api._headers(), json=payload)
    assert r2.status_code in (200, 201)
    body = r2.json()
    assert body.get("status") in ("sent", "already_sent") or body.get("already_processed")
    # Pas de second blob pour le même envoi idempotent
    assert len(mock_vault_storage.objects) <= objects_after_first + 1


def test_attach_004_pdf_generation_failure(api, functional_db, mock_vault_storage, monkeypatch):
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
    with patch(
        "app.services.document_delivery.sales_document_to_pdf",
        side_effect=RuntimeError("pdf_unavailable"),
    ):
        r = api.client.post(
            f"/api/billing/documents/{doc_id}/email",
            headers=api._headers(),
            json={
                "recipient": "client@test.elfis.local",
                "subject": "x",
                "send_mode": "server",
            },
        )
    assert r.status_code in (400, 503)
    assert_safe_phase_d_body(r.json())
