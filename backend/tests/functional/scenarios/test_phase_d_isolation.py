"""Phase D — Isolation tenant."""

from __future__ import annotations

from tests.functional.helpers.phase_d import (
    VALIDATE_BODY,
    assert_safe_phase_d_body,
    install_mock_mailer,
    seed_accounting_proposal,
    seed_sales_doc,
)


def test_iso_proposal_invoice_delivery(api, functional_db, mock_vault_storage, monkeypatch):
    install_mock_mailer(monkeypatch)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        proposal_id = seed_accounting_proposal(db, org_id=org_id, vault_id="vd-iso-d")
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
            "subject": "iso",
            "send_mode": "server",
            "idempotency_key": "phase-d-iso-mail",
        },
    )

    api.login_user("other_tenant")
    for method, path, json_body in (
        ("GET", f"/api/accounting/proposals/{proposal_id}", None),
        ("POST", f"/api/accounting/proposals/{proposal_id}/validate", VALIDATE_BODY),
        ("POST", f"/api/accounting/proposals/{proposal_id}/reject", {"reason": "hack"}),
        ("GET", f"/api/billing/documents/{doc_id}", None),
        ("GET", f"/api/billing/documents/{doc_id}/pdf", None),
        (
            "POST",
            f"/api/billing/documents/{doc_id}/email",
            {"recipient": "x@test.elfis.local", "subject": "x", "send_mode": "server"},
        ),
    ):
        r = api.client.request(method, path, headers=api._headers(), json=json_body)
        assert r.status_code in (401, 403, 404), f"{method} {path} → {r.status_code}"
        if r.headers.get("content-type", "").startswith("application/json"):
            assert_safe_phase_d_body(r.json())
