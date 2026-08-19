"""Phase D — Observabilité / corrélation."""

from __future__ import annotations

from tests.functional.helpers.phase_d import assert_safe_phase_d_body, install_mock_mailer, seed_sales_doc


def test_obs_001_correlation_on_send(api, functional_db, mock_vault_storage, monkeypatch):
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
    headers = api._headers({"X-Correlation-Id": "phase-d-corr-abcdef12"})
    r = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=headers,
        json={
            "recipient": "client@test.elfis.local",
            "subject": "obs",
            "send_mode": "server",
            "idempotency_key": "phase-d-obs-1",
        },
    )
    assert r.status_code in (200, 201)
    assert r.headers.get("X-Request-Id")
    assert r.headers.get("X-Correlation-Id")
    assert_safe_phase_d_body(r.json())


def test_obs_002_error_body_filtered(api, functional_db, mock_vault_storage, monkeypatch):
    from app.services import mailer as mailer_mod
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-" + ("d" * 40))
    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")

    def boom(*_a, **_k):
        raise RuntimeError("secret=xkeysib-leak-should-not-appear traceback")

    monkeypatch.setattr(mailer_mod.httpx, "post", boom)

    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
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
        json={"recipient": "client@test.elfis.local", "subject": "fail", "send_mode": "server"},
    )
    assert r.status_code in (200, 400, 502, 503)
    blob = str(r.json()).lower()
    assert "xkeysib" not in blob
    assert "traceback" not in blob
    assert "secret=" not in blob
    assert_safe_phase_d_body(r.json())
    if r.status_code == 200:
        assert r.json().get("status") in ("email_failed", "failed")
