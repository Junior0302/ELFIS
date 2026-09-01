"""BANK-5 — reauth endpoint, callback, webhooks lifecycle, notifications, isolation."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.banking.api.routes import callback_router, router
from app.banking.banking_events import (
    publish_consent_expiring,
    publish_reauthentication_required,
)
from app.banking.banking_models import ElfisBankConnection, ElfisBankWebhookReceipt
from app.banking.consent_state import issue_consent_state
from app.banking.connectors import registry
from app.banking.connectors.bridge import BridgeBankConnector
from app.config import settings
from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.jobs import bootstrap_job_handlers
from app.jobs.job_models import ElfisJob
from app.models import BankAccount, BankTransaction
from app.models_saas import User
from app.observability.metrics import metrics_registry

from tests.banking.conftest_helpers import make_banking_db, seed_org
from tests.banking.test_bridge_consent import FakeConsentConnector, _SECRET_MARKERS, _assert_no_secrets

SECRET = "644b2ac3-0797-4ec6-9537-cb5c0af9caf9"


def _sign(body: bytes) -> str:
    digest = hmac.new(SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest().upper()
    return f"v1={digest}"


@pytest.fixture()
def reauth_settings(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "bank-5-test-secret")
    monkeypatch.setattr(
        settings,
        "banking_bridge_redirect_uri",
        "http://testserver/api/banking/connectors/bridge/callback",
    )
    monkeypatch.setattr(settings, "frontend_url", "http://frontend.test")
    monkeypatch.setattr(settings, "banking_bridge_webhook_secret", SECRET)
    monkeypatch.setattr(settings, "elfis_job_worker_enabled", True)
    monkeypatch.setattr(settings, "banking_reauth_warning_days", 7)
    metrics_registry.reset()
    bootstrap_job_handlers()


@pytest.fixture()
def reauth_ctx(reauth_settings):
    import app.notifications.notification_models  # noqa: F401
    from app.events import bootstrap_handlers

    bootstrap_handlers()
    db = make_banking_db()
    org_a = seed_org(db, "Org A")
    org_b = seed_org(db, "Org B")
    user_a = User(
        email="a@test.local", first_name="A", last_name="Owner", status="active", password_hash="x"
    )
    db.add(user_a)
    db.commit()
    db.refresh(user_a)
    connector = FakeConsentConnector()
    registry.register_connector("bridge", lambda: connector)
    connection = ElfisBankConnection(
        organization_id=org_a.id,
        provider="bridge",
        provider_connection_id="4568565",
        bank_name="Banque Test",
        status="connected",
        last_sync_status="success",
        reauth_reason="consent_expired",
        reauth_required_at=datetime.utcnow(),
        authentication_expires_at=datetime.utcnow() - timedelta(days=1),
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)

    def _auth():
        return AuthContext(
            user=user_a,
            organization_id=org_a.id,
            role="owner",
            permissions=["*"],
        )

    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.include_router(callback_router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_auth_context] = _auth
    app.dependency_overrides[require_active_subscription] = _auth
    client = TestClient(app, follow_redirects=False)
    yield {
        "client": client,
        "db": db,
        "org_a": org_a,
        "org_b": org_b,
        "user_a": user_a,
        "connection": connection,
        "connector": connector,
        "app": app,
    }
    registry.register_connector("bridge", BridgeBankConnector)
    db.close()


def test_reauth_returns_redirect_url_only(reauth_ctx):
    client = reauth_ctx["client"]
    connection = reauth_ctx["connection"]
    res = client.post(f"/api/banking/connections/{connection.id}/reauthenticate")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["redirect_url"].startswith("https://connect.bridgeapi.io/")
    blob = json.dumps(data)
    _assert_no_secrets(blob)
    assert "client_secret" not in blob.lower()
    call = reauth_ctx["connector"].start_calls[-1]
    assert call["provider_item_id"] == "4568565"
    assert call["force_reauthentication"] is True
    callback = call["callback_url"]
    assert callback
    state = parse_qs(urlparse(callback).query)["state"][0]
    assert state and "." in state
    assert not call.get("context")
    assert state not in (call.get("context") or "")


def test_api_exposes_consent_fields_without_secrets(reauth_ctx):
    res = reauth_ctx["client"].get("/api/banking/connectors")
    assert res.status_code == 200
    data = res.json()
    conn = data["connections"][0]
    assert conn["consent_status"] == "reauth_required"
    assert conn["needs_reauth"] is True
    assert conn["can_reauthenticate"] is True
    assert conn["reauth_reason"] == "consent_expired"
    assert conn["authentication_expires_at"]
    blob = json.dumps(data)
    _assert_no_secrets(blob)
    assert "client_secret" not in blob.lower()
    assert "access_token" not in blob.lower()


def test_reauth_tenant_isolation_wrong_org(reauth_ctx):
    client = reauth_ctx["client"]
    db = reauth_ctx["db"]
    other = ElfisBankConnection(
        organization_id=reauth_ctx["org_b"].id,
        provider="bridge",
        provider_connection_id="999",
        bank_name="Autre",
        status="connected",
    )
    db.add(other)
    db.commit()
    db.refresh(other)
    res = client.post(f"/api/banking/connections/{other.id}/reauthenticate")
    assert res.status_code in {400, 404}


def test_reauth_connect_session_payload_omits_signed_state_context(reauth_ctx, monkeypatch):
    from tests.banking.test_bridge_consent import _bridge_http_fake

    monkeypatch.setattr(settings, "banking_bridge_api_url", "https://api.bridgeapi.io")
    monkeypatch.setattr(settings, "banking_bridge_client_id", "test-client-id")
    monkeypatch.setattr(settings, "banking_bridge_client_secret", "test-client-secret")
    bodies: list[dict] = []
    _bridge_http_fake(monkeypatch, bodies)
    connector = BridgeBankConnector()
    signed = issue_consent_state(
        organization_id=reauth_ctx["org_a"].id,
        connection_id=reauth_ctx["connection"].id,
        purpose="reauth",
    )
    callback = f"http://test/callback?state={signed}"
    connector.start_user_consent(
        organization_id=reauth_ctx["org_a"].id,
        callback_url=callback,
        provider_item_id="4568565",
        force_reauthentication=True,
    )
    payload = bodies[-1]
    assert payload["user_email"].startswith("org-")
    assert payload["callback_url"] == callback
    assert signed in payload["callback_url"]
    assert "context" not in payload
    assert payload.get("force_reauthentication") is True


def test_reauth_tampered_and_expired_state_refused(reauth_ctx):
    import time
    from tests.banking.test_bridge_consent import _signed_state

    connection = reauth_ctx["connection"]
    client = reauth_ctx["client"]
    valid = issue_consent_state(
        organization_id=connection.organization_id,
        connection_id=connection.id,
        purpose="reauth",
    )
    tampered = valid[:-1] + ("0" if valid[-1] != "0" else "1")
    expired = _signed_state(
        organization_id=connection.organization_id,
        connection_id=connection.id,
        expires=int(time.time()) - 30,
        purpose="reauth",
    )
    for bad in (tampered, expired):
        res = client.get(
            "/api/banking/connectors/bridge/callback",
            params={"state": bad, "item_id": "4568565", "success": "true"},
        )
        assert res.status_code == 303
        assert "consent=error" in res.headers["location"]
    reauth_ctx["db"].refresh(connection)
    assert connection.reauth_reason == "consent_expired"


def test_callback_invalid_state_refused(reauth_ctx):
    res = reauth_ctx["client"].get(
        "/api/banking/connectors/bridge/callback",
        params={"state": "not-a-valid-state", "item_id": "4568565", "success": "true"},
    )
    assert res.status_code == 303
    assert "consent=error" in res.headers["location"]


def test_callback_reauth_success_recovers(reauth_ctx):
    db = reauth_ctx["db"]
    connection = reauth_ctx["connection"]
    state = issue_consent_state(
        organization_id=connection.organization_id,
        connection_id=connection.id,
        purpose="reauth",
    )
    res = reauth_ctx["client"].get(
        "/api/banking/connectors/bridge/callback",
        params={"state": state, "item_id": "4568565", "success": "true"},
    )
    assert res.status_code == 303
    assert "consent=ok" in res.headers["location"]
    db.refresh(connection)
    assert connection.status == "connected"
    assert connection.reauth_reason is None
    from app.banking.consent import needs_reauth

    assert needs_reauth(connection) is False
    assert connection.last_reauth_at is not None
    assert connection.authentication_expires_at is not None
    assert connection.consecutive_sync_failures == 0
    events = (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.BANKING_CONNECTION_REAUTHENTICATED)
        .all()
    )
    assert len(events) == 1
    _assert_no_secrets(events[0].payload)


def test_callback_reauth_updates_expires_and_resets_failures(reauth_ctx):
    connection = reauth_ctx["connection"]
    connection.consecutive_sync_failures = 4
    connection.last_sync_error_code = "consent_expired"
    reauth_ctx["db"].add(connection)
    reauth_ctx["db"].commit()
    state = issue_consent_state(
        organization_id=connection.organization_id,
        connection_id=connection.id,
        purpose="reauth",
    )
    reauth_ctx["client"].get(
        "/api/banking/connectors/bridge/callback",
        params={"state": state, "item_id": "4568565", "success": "true"},
    )
    reauth_ctx["db"].refresh(connection)
    assert connection.last_sync_error_code is None
    assert connection.consecutive_sync_failures == 0
    assert connection.authentication_expires_at.year == 2027


def test_webhook_item_refreshed_sca_skips_sync_idempotent(reauth_ctx):
    db = reauth_ctx["db"]
    connection = reauth_ctx["connection"]
    connection.reauth_reason = None
    connection.reauth_required_at = None
    connection.authentication_expires_at = datetime.utcnow() + timedelta(days=30)
    db.add(connection)
    db.commit()
    body = json.dumps(
        {
            "content": {
                "item_id": 4568565,
                "status_code": 1010,
                "status_code_info": "otp_required",
                "authentication_expires_at": "2026-09-01T00:00:00Z",
            },
            "timestamp": 1,
            "type": "item.refreshed",
        },
        separators=(",", ":"),
    ).encode()
    first = reauth_ctx["client"].post(
        "/api/banking/connectors/bridge/webhook",
        content=body,
        headers={"BridgeApi-Signature": _sign(body)},
    )
    second = reauth_ctx["client"].post(
        "/api/banking/connectors/bridge/webhook",
        content=body,
        headers={"BridgeApi-Signature": _sign(body)},
    )
    assert first.status_code == 200
    assert first.json().get("user_action_required") is True
    assert second.status_code == 200
    assert second.json().get("duplicate") is True
    db.refresh(connection)
    assert connection.reauth_reason == "sca_required"
    from app.banking.consent import needs_reauth

    assert needs_reauth(connection) is True
    assert db.query(ElfisJob).count() == 0
    assert db.query(ElfisBankWebhookReceipt).count() == 1


def test_item_deleted_webhook_no_history_delete(reauth_ctx):
    db = reauth_ctx["db"]
    connection = reauth_ctx["connection"]
    account = BankAccount(
        organization_id=connection.organization_id,
        label="Compte",
        bank_name="Banque",
        iban="FR761234",
        currency="EUR",
        balance=10,
        provider="bridge",
        connection_id=connection.id,
        external_id="acc-1",
        connected=True,
    )
    db.add(account)
    db.flush()
    db.add(
        BankTransaction(
            account_id=account.id,
            booked_at="2026-01-01",
            label="Loyer",
            amount=-1,
            currency="EUR",
            category="loyer",
            external_id="tx-1",
        )
    )
    db.commit()
    body = json.dumps(
        {"content": {"item_id": 4568565}, "timestamp": 1, "type": "item.deleted"},
        separators=(",", ":"),
    ).encode()
    first = reauth_ctx["client"].post(
        "/api/banking/connectors/bridge/webhook",
        content=body,
        headers={"BridgeApi-Signature": _sign(body)},
    )
    second = reauth_ctx["client"].post(
        "/api/banking/connectors/bridge/webhook",
        content=body,
        headers={"BridgeApi-Signature": _sign(body)},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json().get("duplicate") is True
    db.refresh(connection)
    assert connection.status == "disconnected"
    assert db.query(BankAccount).count() == 1
    assert db.query(BankTransaction).count() == 1
    assert db.query(ElfisBankWebhookReceipt).count() == 1
    assert db.query(ElfisJob).count() == 0


def test_notification_expiring_idempotent(reauth_ctx):
    db = reauth_ctx["db"]
    connection = reauth_ctx["connection"]
    connection.reauth_reason = None
    connection.reauth_required_at = None
    connection.authentication_expires_at = datetime.utcnow() + timedelta(days=3)
    db.add(connection)
    db.commit()
    publish_consent_expiring(
        db,
        organization_id=connection.organization_id,
        connection_id=connection.id,
        provider="bridge",
        expires_at=connection.authentication_expires_at,
    )
    publish_consent_expiring(
        db,
        organization_id=connection.organization_id,
        connection_id=connection.id,
        provider="bridge",
        expires_at=connection.authentication_expires_at,
    )
    events = (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.BANKING_CONSENT_EXPIRING)
        .all()
    )
    assert len(events) == 1


def test_notification_required_idempotent(reauth_ctx):
    db = reauth_ctx["db"]
    connection = reauth_ctx["connection"]
    publish_reauthentication_required(
        db,
        organization_id=connection.organization_id,
        connection_id=connection.id,
        provider="bridge",
        reason="consent_expired",
    )
    publish_reauthentication_required(
        db,
        organization_id=connection.organization_id,
        connection_id=connection.id,
        provider="bridge",
        reason="consent_expired",
    )
    events = (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.BANKING_REAUTHENTICATION_REQUIRED)
        .all()
    )
    assert len(events) == 1


def test_logs_contain_no_secrets(reauth_ctx, caplog):
    caplog.set_level(logging.INFO)
    connection = reauth_ctx["connection"]
    reauth_ctx["client"].post(f"/api/banking/connections/{connection.id}/reauthenticate")
    text = caplog.text.lower()
    for marker in _SECRET_MARKERS:
        assert marker.lower() not in text
    assert SECRET.lower() not in text
    parsed = urlparse(reauth_ctx["connector"].start_calls[-1]["callback_url"])
    assert "client_secret" not in parse_qs(parsed.query)
