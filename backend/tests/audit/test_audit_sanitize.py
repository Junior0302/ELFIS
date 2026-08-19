"""Tests sanitisation — aucun secret persisté."""

from __future__ import annotations

from app.audit.audit_sanitize import assert_no_secrets_in_payload, sanitize_metadata, sanitize_message


def test_sanitize_metadata_strips_secrets():
    meta = sanitize_metadata(
        {
            "password": "hunter2",
            "api_key": "sk_live_xxx",
            "authorization": "Bearer abc",
            "jwt": "eyJ...",
            "note": "safe",
            "permission": "security.audit.read",
        }
    )
    assert meta is not None
    assert "password" not in meta
    assert "api_key" not in meta
    assert "authorization" not in meta
    assert "jwt" not in meta
    assert meta.get("note") == "safe"
    assert assert_no_secrets_in_payload(meta)


def test_sanitize_message_redacts_bearer():
    msg = sanitize_message("Authorization: Bearer secret-token-value")
    assert msg is not None
    assert "secret-token-value" not in msg
