from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models_saas import Organization, OrganizationEmailConnection, User
from app.services import credential_crypto
from app.services.email_connections import (
    activate_platform,
    create_oauth_state,
    disconnect_connection,
    ensure_platform_connection,
    get_connection_for_org,
    list_sendable_connections,
    parse_oauth_state,
    serialize_connection,
    set_default_connection,
    upsert_provider_connection,
)
from app.services.email_dispatch import resolve_send_connection
from app.services.email_oauth_google import refresh_google_access_token
from app.services.email_smtp_org import upsert_custom_smtp


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setattr(
        "app.config.settings.email_credentials_encryption_key",
        "x" * 32 + "yyyyyyyyyyyyyyyyyyyyyy==",  # invalid length will be replaced
    )
    # Generate a real Fernet key
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    monkeypatch.setattr("app.config.settings.email_credentials_encryption_key", key)
    monkeypatch.setattr("app.config.settings.jwt_secret", "test-jwt-secret-for-oauth-state-32c")
    monkeypatch.setattr("app.config.settings.brevo_api_key", "xkeysib-test")
    monkeypatch.setattr("app.config.settings.platform_email_from", "documents@elfiscore.com")
    monkeypatch.setattr("app.config.settings.app_env", "development")
    return _session()


def _org(db):
    org = Organization(name="IOSTAY", legal_name="IOSTAY SAS", email="contact@iostay.fr")
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def test_encrypt_decrypt_roundtrip(db, monkeypatch):
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    monkeypatch.setattr("app.config.settings.email_credentials_encryption_key", key)
    token = credential_crypto.encrypt_secret("super-secret-token")
    assert token.startswith("v1:")
    assert "super-secret" not in token
    assert credential_crypto.decrypt_secret(token) == "super-secret-token"


def test_serialize_never_exposes_tokens(db):
    org = _org(db)
    conn = upsert_provider_connection(
        db,
        organization_id=org.id,
        provider="google",
        user_id=1,
        email="facturation@iostay.fr",
        display_name="IOSTAY",
        access_token="access-secret",
        refresh_token="refresh-secret",
        expires_in=3600,
        make_default=True,
    )
    public = serialize_connection(conn)
    blob = str(public)
    assert "access-secret" not in blob
    assert "refresh-secret" not in blob
    assert "encrypted" not in blob
    assert public["email_address"] == "facturation@iostay.fr"
    assert public["provider"] == "google"


def test_oauth_state_invalid(db):
    with pytest.raises(RuntimeError):
        parse_oauth_state("not-a-valid-jwt")


def test_oauth_state_valid_roundtrip(db):
    state = create_oauth_state(organization_id=7, user_id=3, provider="google", connection_id=9)
    data = parse_oauth_state(state)
    assert data["org_id"] == 7
    assert data["uid"] == 3
    assert data["provider"] == "google"
    assert data["cid"] == 9


def test_google_refresh_revoked(db, monkeypatch):
    org = _org(db)
    conn = upsert_provider_connection(
        db,
        organization_id=org.id,
        provider="google",
        user_id=1,
        email="a@b.fr",
        display_name="A",
        access_token="a",
        refresh_token="r",
        expires_in=1,
    )
    conn.token_expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.add(conn)
    db.commit()

    class FakeResp:
        status_code = 400
        text = "invalid_grant"

        def json(self):
            return {}

    monkeypatch.setattr("app.services.email_oauth_google.httpx.post", lambda *a, **k: FakeResp())
    with pytest.raises(RuntimeError) as exc:
        refresh_google_access_token(db, conn)
    assert "Reconnectez" in str(exc.value)
    db.refresh(conn)
    assert conn.status == "revoked"


def test_google_refresh_valid(db, monkeypatch):
    org = _org(db)
    conn = upsert_provider_connection(
        db,
        organization_id=org.id,
        provider="google",
        user_id=1,
        email="a@b.fr",
        display_name="A",
        access_token="old",
        refresh_token="r",
        expires_in=1,
    )
    conn.token_expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.add(conn)
    db.commit()

    class FakeResp:
        status_code = 200

        def json(self):
            return {"access_token": "new-access", "expires_in": 3600}

    monkeypatch.setattr("app.services.email_oauth_google.httpx.post", lambda *a, **k: FakeResp())
    token = refresh_google_access_token(db, conn)
    assert token == "new-access"
    db.refresh(conn)
    assert conn.status == "connected"


def test_isolation_between_organizations(db):
    org1 = _org(db)
    org2 = Organization(name="Other", legal_name="Other SA")
    db.add(org2)
    db.commit()
    db.refresh(org2)
    c1 = upsert_provider_connection(
        db,
        organization_id=org1.id,
        provider="google",
        user_id=1,
        email="one@a.fr",
        display_name="One",
        access_token="t1",
        refresh_token="r1",
        expires_in=3600,
    )
    assert get_connection_for_org(db, org2.id, c1.id) is None
    assert get_connection_for_org(db, org1.id, c1.id) is not None


def test_disconnect_and_platform_fallback_default(db):
    org = _org(db)
    ensure_platform_connection(db, org.id)
    google = upsert_provider_connection(
        db,
        organization_id=org.id,
        provider="google",
        user_id=1,
        email="g@a.fr",
        display_name="G",
        access_token="t",
        refresh_token="r",
        expires_in=3600,
        make_default=True,
    )
    disconnect_connection(db, org.id, google.id)
    default = next(c for c in list_sendable_connections(db, org.id) if c.is_default)
    assert default.provider == "platform"


def test_resolve_send_expired_no_silent_fallback(db):
    org = _org(db)
    conn = upsert_provider_connection(
        db,
        organization_id=org.id,
        provider="microsoft",
        user_id=1,
        email="m@a.fr",
        display_name="M",
        access_token="t",
        refresh_token="r",
        expires_in=3600,
        make_default=True,
    )
    conn.status = "expired"
    db.add(conn)
    db.commit()
    with pytest.raises(RuntimeError) as exc:
        resolve_send_connection(db, org.id, conn.id)
    assert "ComptaPilot" in str(exc.value)
    assert "Reconnectez" in str(exc.value)


def test_platform_activate(db):
    org = _org(db)
    conn = activate_platform(db, org.id, user_id=1)
    assert conn.provider == "platform"
    assert conn.is_default is True
    assert conn.status == "connected"


def test_smtp_invalid(db, monkeypatch):
    org = _org(db)

    def boom(**kwargs):
        raise RuntimeError("SMTP invalide")

    monkeypatch.setattr("app.services.email_smtp_org.test_smtp_settings", boom)
    with pytest.raises(RuntimeError):
        upsert_custom_smtp(
            db,
            organization_id=org.id,
            user_id=1,
            email_address="smtp@a.fr",
            display_name="SMTP",
            smtp_host="smtp.invalid",
            smtp_port=587,
            smtp_username="smtp@a.fr",
            smtp_password="bad",
            test_before_save=True,
        )


def test_smtp_valid(db, monkeypatch):
    org = _org(db)
    monkeypatch.setattr("app.services.email_smtp_org.test_smtp_settings", lambda **k: None)
    conn = upsert_custom_smtp(
        db,
        organization_id=org.id,
        user_id=1,
        email_address="smtp@a.fr",
        display_name="SMTP Org",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="smtp@a.fr",
        smtp_password="app-password",
        make_default=True,
        test_before_save=True,
    )
    public = serialize_connection(conn)
    assert public["has_smtp_password"] is True
    assert "app-password" not in str(public)
    assert conn.provider == "custom_smtp"
    assert conn.is_default is True


def test_send_via_gmail_attachment(db, monkeypatch):
    from app.services.email_oauth_google import send_via_gmail
    from app.services.mailer import MailAttachment

    org = _org(db)
    conn = upsert_provider_connection(
        db,
        organization_id=org.id,
        provider="google",
        user_id=1,
        email="facturation@iostay.fr",
        display_name="IOSTAY",
        access_token="atok",
        refresh_token="rtok",
        expires_in=3600,
    )
    captured = {}

    class FakeResp:
        status_code = 200

        def json(self):
            return {"id": "gmail-msg-1"}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["auth"] = (headers or {}).get("Authorization")
        return FakeResp()

    monkeypatch.setattr("app.services.email_oauth_google.httpx.post", fake_post)
    monkeypatch.setattr(
        "app.services.email_oauth_google.ensure_google_access_token",
        lambda db, c: "atok",
    )
    result = send_via_gmail(
        db,
        conn,
        to_email="client@email.fr",
        subject="Facture FAC-2026-0002 — IOSTAY",
        body="Bonjour",
        attachments=[MailAttachment(filename="Facture-FAC-2026-0002.pdf", content=b"%PDF-1.4")],
    )
    assert result.provider == "google"
    assert result.sender_email == "facturation@iostay.fr"
    assert result.provider_message_id == "gmail-msg-1"
    assert "raw" in captured["json"]
    # raw MIME contains PDF filename
    import base64

    raw = base64.urlsafe_b64decode(captured["json"]["raw"] + "==")
    assert b"Facture-FAC-2026-0002.pdf" in raw
    assert b"facturation@iostay.fr" in raw


def test_send_via_microsoft(db, monkeypatch):
    from app.services.email_oauth_microsoft import send_via_microsoft
    from app.services.mailer import MailAttachment

    org = _org(db)
    conn = upsert_provider_connection(
        db,
        organization_id=org.id,
        provider="microsoft",
        user_id=1,
        email="contact@entreprise-abc.fr",
        display_name="Entreprise ABC",
        access_token="atok",
        refresh_token="rtok",
        expires_in=3600,
    )
    captured = {}

    class FakeResp:
        status_code = 202
        text = ""

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return FakeResp()

    monkeypatch.setattr("app.services.email_oauth_microsoft.httpx.post", fake_post)
    monkeypatch.setattr(
        "app.services.email_oauth_microsoft.ensure_microsoft_access_token",
        lambda db, c: "atok",
    )
    result = send_via_microsoft(
        db,
        conn,
        to_email="client@email.fr",
        subject="Devis DEV-1",
        body="Bonjour",
        attachments=[MailAttachment(filename="Devis-DEV-1.pdf", content=b"%PDF")],
    )
    assert result.provider == "microsoft"
    assert result.sender_email == "contact@entreprise-abc.fr"
    assert captured["json"]["message"]["attachments"][0]["name"] == "Devis-DEV-1.pdf"


def test_complete_google_oauth_flow(db, monkeypatch):
    from app.services.email_oauth_google import complete_google_oauth

    org = _org(db)

    monkeypatch.setattr(
        "app.services.email_oauth_google.exchange_google_code",
        lambda code: {
            "access_token": "acc",
            "refresh_token": "ref",
            "expires_in": 3600,
        },
    )
    monkeypatch.setattr(
        "app.services.email_oauth_google.fetch_google_profile",
        lambda token: {"email": "facturation@iostay.fr", "name": "IOSTAY", "id": "gid"},
    )
    conn = complete_google_oauth(
        db, organization_id=org.id, user_id=42, code="auth-code"
    )
    assert conn.email_address == "facturation@iostay.fr"
    assert conn.provider == "google"
    assert conn.status == "connected"
    assert conn.is_default is True


def test_complete_microsoft_oauth_flow(db, monkeypatch):
    from app.services.email_oauth_microsoft import complete_microsoft_oauth

    org = _org(db)
    monkeypatch.setattr(
        "app.services.email_oauth_microsoft.exchange_microsoft_code",
        lambda code: {"access_token": "acc", "refresh_token": "ref", "expires_in": 3600},
    )
    monkeypatch.setattr(
        "app.services.email_oauth_microsoft.fetch_microsoft_profile",
        lambda token: {
            "mail": "contact@entreprise-abc.fr",
            "displayName": "Entreprise ABC",
            "id": "mid",
        },
    )
    conn = complete_microsoft_oauth(
        db, organization_id=org.id, user_id=42, code="auth-code"
    )
    assert conn.email_address == "contact@entreprise-abc.fr"
    assert conn.provider == "microsoft"


def test_set_default_requires_connected(db):
    org = _org(db)
    ensure_platform_connection(db, org.id)
    conn = upsert_provider_connection(
        db,
        organization_id=org.id,
        provider="google",
        user_id=1,
        email="g@a.fr",
        display_name="G",
        access_token="t",
        refresh_token="r",
        expires_in=3600,
        make_default=False,
    )
    conn.status = "error"
    db.add(conn)
    db.commit()
    with pytest.raises(RuntimeError):
        set_default_connection(db, org.id, conn.id)
