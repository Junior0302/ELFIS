"""Phase D — Retries Delivery (RETRY-001 … RETRY-003)."""

from __future__ import annotations

from tests.functional.helpers.phase_d import (
    assert_safe_phase_d_body,
    install_mock_mailer,
    patch_mailer_fail_then_succeed,
    seed_sales_doc,
)


def test_retry_001_manual_after_failure(api, functional_db, mock_vault_storage, monkeypatch):
    """Erreur temporaire : 1er envoi échoue, 2e avec nouvelle clé réussit."""
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id)
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("org_admin")
    # Force échec
    from app.services import mailer as mailer_mod
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-" + ("c" * 40))
    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")

    def boom(*_a, **_k):
        raise RuntimeError("mock_mailer_temporary")

    monkeypatch.setattr(mailer_mod.httpx, "post", boom)
    r1 = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json={
            "recipient": "client@test.elfis.local",
            "subject": "fail1",
            "send_mode": "server",
            "idempotency_key": "phase-d-retry-a",
        },
    )
    assert r1.status_code in (200, 400, 502, 503)
    body1 = r1.json()
    assert_safe_phase_d_body(body1)
    if r1.status_code == 200:
        assert body1.get("status") in ("email_failed", "failed")
        assert "xkeysib" not in str(body1).lower()
        assert "traceback" not in str(body1).lower()

    # Succès au retry manuel (clé différente — politique V1)
    install_mock_mailer(monkeypatch)
    r2 = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json={
            "recipient": "client@test.elfis.local",
            "subject": "ok2",
            "send_mode": "server",
            "idempotency_key": "phase-d-retry-b",
        },
    )
    assert r2.status_code in (200, 201)


def test_retry_002_003_idempotent_key_no_double_send(api, functional_db, mock_vault_storage, monkeypatch):
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
        "subject": "once",
        "send_mode": "server",
        "idempotency_key": "phase-d-retry-idem",
    }
    assert api.client.post(
        f"/api/billing/documents/{doc_id}/email", headers=api._headers(), json=payload
    ).status_code in (200, 201)
    n1 = len(calls)
    r2 = api.client.post(
        f"/api/billing/documents/{doc_id}/email", headers=api._headers(), json=payload
    )
    assert r2.status_code in (200, 201)
    assert r2.json().get("status") in ("sent", "already_sent")
    # Pas de second appel mailer
    assert len(calls) == n1
