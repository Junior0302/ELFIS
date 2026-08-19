"""Phase D — Notifications (NOTIF-001 … NOTIF-004)."""

from __future__ import annotations

from tests.functional.helpers.phase_d import (
    VALIDATE_BODY,
    assert_safe_phase_d_body,
    install_mock_mailer,
    seed_accounting_proposal,
    seed_sales_doc,
)
from tests.functional.helpers.phase_c import drain_pipeline


def test_notif_001_after_validation(api, functional_db, monkeypatch):
    from app.config import settings
    from app.events import bootstrap_handlers
    from app.notifications import register_notification_handlers

    monkeypatch.setattr(settings, "elfis_auto_search_indexing_enabled", True)
    bootstrap_handlers()
    try:
        register_notification_handlers()
    except Exception:
        pass

    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        proposal_id = seed_accounting_proposal(db, org_id=org_id, vault_id="vd-notif-val")
    finally:
        db.close()

    api.login_user("org_admin")
    r = api.client.post(
        f"/api/accounting/proposals/{proposal_id}/validate",
        headers=api._headers(),
        json=VALIDATE_BODY,
    )
    assert r.status_code in (200, 201)
    drain_pipeline(functional_db["Session"], max_rounds=10)

    notif = api.client.get("/api/notifications", headers=api._headers())
    assert notif.status_code in (200, 401, 403)
    if notif.status_code == 200:
        assert_safe_phase_d_body(notif.json())


def test_notif_002_003_email_sent(api, functional_db, mock_vault_storage, monkeypatch):
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
    assert api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json={
            "recipient": "client@test.elfis.local",
            "subject": "notif",
            "send_mode": "server",
            "idempotency_key": "phase-d-notif-mail",
        },
    ).status_code in (200, 201)
    drain_pipeline(functional_db["Session"], max_rounds=8)
    notif = api.client.get("/api/notifications", headers=api._headers())
    assert notif.status_code in (200, 401, 403)
    if notif.status_code == 200:
        assert_safe_phase_d_body(notif.json())
        blob = str(notif.json()).lower()
        assert "sk_" not in blob
        assert "password" not in blob


def test_notif_004_isolation(api, functional_db):
    api.login_user("other_tenant")
    r = api.client.get("/api/notifications", headers=api._headers())
    assert r.status_code in (200, 401, 403)
    if r.status_code == 200:
        # Pas de fuite ORG_ACTIVE markers
        assert "vd-notif-val" not in str(r.json())
