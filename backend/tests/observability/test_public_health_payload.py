"""Health public — aucun diagnostic mailer / secret."""

from __future__ import annotations

from app.main import health
from app.observability.health import live


FORBIDDEN = (
    "brevo_key_prefix",
    "brevo_key_length",
    "brevo_key_looks_valid",
    "smtp_host",
    "smtp_port",
    "smtp_password",
    "smtp_probe_error",
    "platform_email_from",
    "email_hint",
    "brevo_error",
    "details",
)


def test_public_health_is_minimal():
    body = health()
    assert body["status"] == "ok"
    blob = str(body).lower()
    for leaked in FORBIDDEN:
        assert leaked not in blob


def test_live_health_is_minimal():
    body = live()
    assert body["status"] == "ok"
    assert body["check"] == "live"
    blob = str(body).lower()
    for leaked in FORBIDDEN:
        assert leaked not in blob
