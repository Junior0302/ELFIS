"""BANK-1 — consentement Bridge lecture seule, isolation tenant, anti-CSRF."""

from __future__ import annotations

from datetime import date
from typing import Any, ClassVar
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.banking.api.routes import callback_router, router
from app.banking.banking_models import ElfisBankConnection, ElfisBankSyncRun
from app.banking.banking_types import ConsentCompleteResult, ConsentStartResult
from app.banking.consent_state import issue_consent_state
from app.banking.connectors import registry
from app.banking.connectors.base import ConnectorError
from app.banking.connectors.bridge import BridgeBankConnector, bridge_external_user_id
from app.banking.engine import BankingEngine, BankingEngineError
from app.config import settings
from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models import BankTransaction
from app.models_saas import User

from tests.banking.conftest_helpers import (
    FakeBankConnector,
    make_banking_db,
    make_tx,
    seed_org,
)

_SECRET_MARKERS = (
    "client_secret",
    "Client-Secret",
    "access_token",
    "BANKING_BRIDGE_CLIENT_SECRET",
    "bridge-access-secret",
)


def _assert_no_secrets(payload: object) -> None:
    blob = str(payload).lower()
    for marker in _SECRET_MARKERS:
        assert marker.lower() not in blob


class FakeConsentConnector(FakeBankConnector):
    provider: ClassVar[str] = "bridge"
    display_name: ClassVar[str] = "Bridge"
    requires_user_consent: ClassVar[bool] = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.start_calls: list[dict] = []
        self.complete_calls: list[dict] = []
        self.complete_error: Exception | None = None
        self.redirect_url = "https://connect.bridgeapi.io/session/test-session"

    def start_user_consent(
        self,
        *,
        organization_id: int,
        callback_url: str,
        bank_name: str = "",
        context: str = "",
    ) -> ConsentStartResult:
        self.start_calls.append(
            {
                "organization_id": organization_id,
                "callback_url": callback_url,
                "context": context,
            }
        )
        return ConsentStartResult(redirect_url=self.redirect_url)

    def complete_user_consent(
        self, *, organization_id: int, provider_item_id: str
    ) -> ConsentCompleteResult:
        self.complete_calls.append(
            {"organization_id": organization_id, "provider_item_id": provider_item_id}
        )
        if self.complete_error:
            raise self.complete_error
        return ConsentCompleteResult(
            provider_connection_id=provider_item_id,
            bank_name="Demo Bank",
            authentication_expires_at="2027-02-19T00:00:00Z",
        )

    def connect(self, *, organization_id: int, bank_name: str, options: dict | None = None) -> str:
        raise ConnectorError("Bridge nécessite un consentement utilisateur.")


@pytest.fixture()
def consent_settings(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "bank-1-test-secret")
    monkeypatch.setattr(
        settings,
        "banking_bridge_redirect_uri",
        "http://testserver/api/banking/connectors/bridge/callback",
    )
    monkeypatch.setattr(settings, "frontend_url", "http://frontend.test")
    monkeypatch.setattr(settings, "banking_bridge_api_url", "https://api.bridgeapi.io")
    monkeypatch.setattr(settings, "banking_bridge_client_id", "test-client-id")
    monkeypatch.setattr(settings, "banking_bridge_client_secret", "test-client-secret")


@pytest.fixture()
def consent_ctx(consent_settings):
    db = make_banking_db()
    org_a = seed_org(db, "Org A")
    org_b = seed_org(db, "Org B")
    user_a = User(
        email="a@test.local", first_name="A", last_name="Owner", status="active", password_hash="x"
    )
    user_b = User(
        email="b@test.local", first_name="B", last_name="Owner", status="active", password_hash="x"
    )
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    connector = FakeConsentConnector(
        transactions={
            "fake-acc-1": [
                make_tx("fake-acc-1", date(2026, 8, 1), "VIREMENT CLIENT BRIDGE", 120.0),
            ]
        }
    )
    registry.register_connector("bridge", lambda: connector)

    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.include_router(callback_router, prefix="/api")

    current = {"org_id": org_a.id, "user": user_a}

    def _auth():
        return AuthContext(
            user=current["user"],
            organization_id=current["org_id"],
            role="owner",
            permissions=["*"],
        )

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
        "user_b": user_b,
        "connector": connector,
        "current": current,
    }
    registry.register_connector("bridge", BridgeBankConnector)
    db.close()


def _start(client: TestClient, org_id: int) -> dict:
    res = client.post(
        "/api/banking/connectors/connect",
        json={"provider": "bridge", "bank_name": "Demo Bank"},
        headers={"X-Organization-Id": str(org_id)},
    )
    assert res.status_code == 200, res.text
    return res.json()


def test_org_a_cannot_use_org_b_connection(consent_ctx):
    client = consent_ctx["client"]
    current = consent_ctx["current"]
    org_a = consent_ctx["org_a"]
    org_b = consent_ctx["org_b"]
    user_b = consent_ctx["user_b"]

    started = _start(client, org_a.id)
    connection_id = started["connection"]["id"]

    current["org_id"] = org_b.id
    current["user"] = user_b
    res = client.post(
        f"/api/banking/connectors/{connection_id}/disconnect",
        headers={"X-Organization-Id": str(org_b.id)},
    )
    assert res.status_code == 400

    res = client.post(
        "/api/banking/sync",
        json={"connection_id": connection_id},
        headers={"X-Organization-Id": str(org_b.id)},
    )
    assert res.status_code == 400

    engine = BankingEngine(consent_ctx["db"])
    with pytest.raises(BankingEngineError):
        engine.get_connection(org_b.id, connection_id)
    assert engine.list_connections(org_b.id) == []


def test_connect_session_created_and_frontend_gets_only_temp_url(consent_ctx):
    body = _start(consent_ctx["client"], consent_ctx["org_a"].id)
    _assert_no_secrets(body)
    assert body["redirect_url"] == "https://connect.bridgeapi.io/session/test-session"
    assert body["connection"]["status"] == "awaiting_consent"
    assert "provider_connection_id" not in body["connection"]
    assert consent_ctx["connector"].start_calls
    callback = consent_ctx["connector"].start_calls[0]["callback_url"]
    assert "state=" in callback
    row = consent_ctx["db"].query(ElfisBankConnection).one()
    assert row.provider_connection_id == ""
    assert row.organization_id == consent_ctx["org_a"].id
    sync = consent_ctx["client"].post(
        "/api/banking/sync",
        json={},
        headers={"X-Organization-Id": str(consent_ctx["org_a"].id)},
    )
    assert sync.status_code == 400


def test_bridge_http_creates_connect_session(consent_settings, monkeypatch):
    calls: list[tuple[str, str, dict]] = []

    def fake_request(method: str, url: str, headers=None, **kwargs):
        calls.append((method, url, dict(headers or {})))
        path = urlparse(url).path
        if path.endswith("/v3/aggregation/users"):
            return httpx.Response(201, json={"uuid": "user-uuid-1", "external_user_id": "elfis-org-9"})
        if path.endswith("/v3/aggregation/authorization/token"):
            return httpx.Response(
                201,
                json={
                    "access_token": "bridge-access-secret",
                    "expires_at": "2026-08-23T12:00:00Z",
                    "user": {"uuid": "user-uuid-1"},
                },
            )
        if path.endswith("/v3/aggregation/connect-sessions"):
            return httpx.Response(
                201,
                json={"id": "sess-1", "url": "https://connect.bridgeapi.io/session/live"},
            )
        return httpx.Response(404, json={})

    monkeypatch.setattr(httpx, "request", fake_request)
    connector = BridgeBankConnector()
    result = connector.start_user_consent(
        organization_id=9,
        callback_url="http://test/callback?state=abc",
        context="abc",
    )
    assert result.redirect_url == "https://connect.bridgeapi.io/session/live"
    paths = [urlparse(url).path for _, url, _ in calls]
    assert any(path.endswith("/v3/aggregation/users") for path in paths)
    token_call = next(h for _, u, h in calls if urlparse(u).path.endswith("/authorization/token"))
    session_call = next(h for _, u, h in calls if urlparse(u).path.endswith("/connect-sessions"))
    assert session_call["Authorization"] == "Bearer bridge-access-secret"
    assert "Client-Id" in session_call
    assert token_call["Client-Id"] == "test-client-id"
    assert bridge_external_user_id(9) == "elfis-org-9"


def test_valid_callback_links_item_and_runs_sync_engine(consent_ctx):
    client = consent_ctx["client"]
    org = consent_ctx["org_a"]
    started = _start(client, org.id)
    connection_id = started["connection"]["id"]
    state = parse_qs(urlparse(consent_ctx["connector"].start_calls[0]["callback_url"]).query)["state"][0]

    res = client.get(
        "/api/banking/connectors/bridge/callback",
        params={"state": state, "item_id": "item-42", "success": "true"},
    )
    assert res.status_code == 303
    assert res.headers["location"] == "http://frontend.test/platform/banking?consent=ok"
    _assert_no_secrets(dict(res.headers))

    row = consent_ctx["db"].get(ElfisBankConnection, connection_id)
    assert row.organization_id == org.id
    assert row.provider_connection_id == "item-42"
    assert row.status == "connected"
    assert consent_ctx["connector"].complete_calls == [
        {"organization_id": org.id, "provider_item_id": "item-42"}
    ]

    run = consent_ctx["db"].query(ElfisBankSyncRun).one()
    assert run.trigger == "consent"
    assert run.status == "completed"
    assert run.transactions_created == 1
    assert consent_ctx["db"].query(BankTransaction).count() == 1


def test_invalid_and_replayed_state_refused(consent_ctx):
    client = consent_ctx["client"]
    org = consent_ctx["org_a"]
    started = _start(client, org.id)
    connection_id = started["connection"]["id"]
    state = parse_qs(urlparse(consent_ctx["connector"].start_calls[0]["callback_url"]).query)["state"][0]

    res = client.get(
        "/api/banking/connectors/bridge/callback",
        params={"state": "not-a-valid-state", "item_id": "item-99", "success": "true"},
    )
    assert res.status_code == 303
    assert res.headers["location"].endswith("consent=error")
    row = consent_ctx["db"].get(ElfisBankConnection, connection_id)
    assert row.status == "awaiting_consent"
    assert row.provider_connection_id == ""

    ok = client.get(
        "/api/banking/connectors/bridge/callback",
        params={"state": state, "item_id": "item-42", "success": "true"},
    )
    assert ok.headers["location"].endswith("consent=ok")

    replay = client.get(
        "/api/banking/connectors/bridge/callback",
        params={"state": state, "item_id": "item-99", "success": "true"},
    )
    assert replay.headers["location"].endswith("consent=error")
    row = consent_ctx["db"].get(ElfisBankConnection, connection_id)
    assert row.provider_connection_id == "item-42"


def test_user_abort_in_bridge_connect(consent_ctx):
    client = consent_ctx["client"]
    org = consent_ctx["org_a"]
    started = _start(client, org.id)
    connection_id = started["connection"]["id"]
    state = parse_qs(urlparse(consent_ctx["connector"].start_calls[0]["callback_url"]).query)["state"][0]

    res = client.get(
        "/api/banking/connectors/bridge/callback",
        params={"state": state, "success": "false", "user_uuid": "uuid-only"},
    )
    assert res.status_code == 303
    assert res.headers["location"].endswith("consent=denied")
    row = consent_ctx["db"].get(ElfisBankConnection, connection_id)
    assert row.status == "error"
    assert row.provider_connection_id == ""
    assert consent_ctx["connector"].complete_calls == []


def test_callback_item_id_without_state_refused(consent_ctx):
    client = consent_ctx["client"]
    org = consent_ctx["org_a"]
    started = _start(client, org.id)
    connection_id = started["connection"]["id"]

    res = client.get(
        "/api/banking/connectors/bridge/callback",
        params={"item_id": "item-stolen", "success": "true"},
    )
    assert res.headers["location"].endswith("consent=error")
    row = consent_ctx["db"].get(ElfisBankConnection, connection_id)
    assert row.provider_connection_id == ""
    assert row.status == "awaiting_consent"


def test_state_for_org_a_cannot_attach_to_org_b(consent_ctx):
    client = consent_ctx["client"]
    current = consent_ctx["current"]
    org_a = consent_ctx["org_a"]
    org_b = consent_ctx["org_b"]
    user_b = consent_ctx["user_b"]

    _start(client, org_a.id)
    current["org_id"] = org_b.id
    current["user"] = user_b
    started_b = _start(client, org_b.id)
    state_a = parse_qs(urlparse(consent_ctx["connector"].start_calls[0]["callback_url"]).query)[
        "state"
    ][0]

    client.get(
        "/api/banking/connectors/bridge/callback",
        params={"state": state_a, "item_id": "item-a", "success": "true"},
    )
    row_b = consent_ctx["db"].get(ElfisBankConnection, started_b["connection"]["id"])
    assert row_b.provider_connection_id == ""
    row_a = (
        consent_ctx["db"]
        .query(ElfisBankConnection)
        .filter(ElfisBankConnection.organization_id == org_a.id)
        .order_by(ElfisBankConnection.id.asc())
        .first()
    )
    assert row_a.provider_connection_id == "item-a"
    assert row_a.organization_id == org_a.id


def test_forged_state_with_other_org_connection_id_refused(consent_ctx):
    client = consent_ctx["client"]
    current = consent_ctx["current"]
    org_a = consent_ctx["org_a"]
    org_b = consent_ctx["org_b"]
    user_b = consent_ctx["user_b"]

    started_a = _start(client, org_a.id)
    current["org_id"] = org_b.id
    current["user"] = user_b
    _start(client, org_b.id)
    forged = issue_consent_state(
        organization_id=org_b.id, connection_id=started_a["connection"]["id"]
    )
    res = client.get(
        "/api/banking/connectors/bridge/callback",
        params={"state": forged, "item_id": "item-x", "success": "true"},
    )
    assert res.headers["location"].endswith("consent=error")
    row_a = consent_ctx["db"].get(ElfisBankConnection, started_a["connection"]["id"])
    assert row_a.provider_connection_id == ""


def test_connect_response_never_contains_bridge_secrets(consent_ctx):
    body = _start(consent_ctx["client"], consent_ctx["org_a"].id)
    _assert_no_secrets(body)
    assert set(body.keys()) <= {"ok", "redirect_url", "connection", "accounts", "message"}
    assert "client_id" not in str(body).lower()
    assert "token" not in str(body).lower()
