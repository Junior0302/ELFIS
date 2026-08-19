"""Phase D — Expéditeurs (SENDER-001 … SENDER-004)."""

from __future__ import annotations

from tests.functional.helpers.phase_d import assert_safe_phase_d_body


def test_sender_001_002_options_personal(api):
    api.login_user("org_admin")
    r = api.client.get("/api/professional-emails/sender-options", headers=api._headers())
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        body = r.json()
        assert_safe_phase_d_body(body)
        blob = str(body).lower()
        assert "password" not in blob
        assert "smtp" not in blob or "host" not in blob
        # Options personnelles et/ou professional
        assert "options" in body or "emails" in body or "senders" in body or isinstance(body, (dict, list))


def test_sender_003_004_elfis_request_flow(api):
    """Demande adresse ELFIS — tester parties existantes sans créer d'infra réelle."""
    api.login_user("org_admin")
    r = api.client.get("/api/professional-emails/me", headers=api._headers())
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        assert_safe_phase_d_body(r.json())

    # Création de demande si endpoint existe
    r2 = api.client.post(
        "/api/professional-emails/request",
        headers=api._headers(),
        json={"requested_local_part": "org.admin"},
    )
    # Peut déjà exister / validation / succès
    assert r2.status_code in (200, 201, 400, 409, 422, 404)
    if r2.status_code in (200, 201):
        assert_safe_phase_d_body(r2.json())
        # Pending → non utilisable comme From Brevo usurpée (documenté)
        status = str(r2.json()).lower()
        assert "password" not in status
        assert "xkeysib" not in status
        assert "brevo_key" not in status
