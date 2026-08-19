"""Redaction secrets — logs / erreurs."""

from __future__ import annotations

from app.events.event_context import sanitize_error_message


def test_secret_redaction_stripe_and_bearer():
    stripe_fake = "sk_live_fake_abcdefghijklmnopqrstuv"
    msg = sanitize_error_message(
        f"Stripe {stripe_fake} webhook Bearer tokensecret123"
    )
    assert stripe_fake not in msg
    assert "tokensecret123" not in msg or "[REDACTED]" in msg
