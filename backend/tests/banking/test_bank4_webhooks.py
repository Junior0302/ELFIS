"""BANK-4 — webhook Bridge : signature officielle, event_id, enqueue, déduplication."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.banking.api.routes import callback_router
from app.banking.banking_models import ElfisBankConnection, ElfisBankWebhookReceipt
from app.banking.webhooks import (
    expected_signature,
    payload_hash,
    provider_event_id_from_body,
    verify_bridge_signature,
)
from app.config import settings
from app.database import get_db
from app.jobs import bootstrap_job_handlers
from app.jobs.job_models import ElfisJob
from app.observability.metrics import metrics_registry

from tests.banking.conftest_helpers import make_banking_db, seed_org

SECRET = "644b2ac3-0797-4ec6-9537-cb5c0af9caf9"
PREVIOUS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
# Vecteur officiel https://docs.bridgeapi.io/docs/secure-your-webhooks
OFFICIAL_PAYLOAD = (
    '{"content":{"item_id":1234567890,"status":0,'
    '"user_uuid":"9a95b38f-f98b-417a-988b-9d0d584893e7"},'
    '"timestamp":1611681789,"type":"TEST_EVENT"}'
)
OFFICIAL_SIGNATURE = "FAA8ECAC21DA6405D789C76EDB4003756398E7169DACC3FA70CF5919A81374A8"


def _sign(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest().upper()
    return f"v1={digest}"


def _refreshed_body(item_id: int, timestamp: int) -> bytes:
    return json.dumps(
        {
            "content": {
                "item_id": item_id,
                "status_code": 0,
                "user_uuid": "766b2f5d-a942-492c-9ea7-2e5aa88cb672",
            },
            "timestamp": timestamp,
            "type": "item.refreshed",
        },
        separators=(",", ":"),
    ).encode("utf-8")


@pytest.fixture()
def webhook_client(monkeypatch):
    monkeypatch.setattr(settings, "banking_bridge_webhook_secret", SECRET)
    monkeypatch.setattr(settings, "banking_bridge_webhook_secret_previous", "")
    monkeypatch.setattr(settings, "elfis_job_worker_enabled", True)
    metrics_registry.reset()
    bootstrap_job_handlers()
    db = make_banking_db()
    org = seed_org(db)
    connection = ElfisBankConnection(
        organization_id=org.id,
        provider="bridge",
        provider_connection_id="4568565",
        bank_name="Banque Test",
        status="connected",
        last_sync_status="never",
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)

    app = FastAPI()
    app.include_router(callback_router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)
    yield client, db, org, connection
    db.close()


def test_official_bridge_signature_vector():
    raw = OFFICIAL_PAYLOAD.encode("utf-8")
    assert expected_signature(SECRET, raw) == OFFICIAL_SIGNATURE
    assert verify_bridge_signature(raw, f"v1={OFFICIAL_SIGNATURE}", secrets=[SECRET]) is True


def test_official_payload_string_is_exact():
    assert OFFICIAL_PAYLOAD == (
        '{"content":{"item_id":1234567890,"status":0,'
        '"user_uuid":"9a95b38f-f98b-417a-988b-9d0d584893e7"},'
        '"timestamp":1611681789,"type":"TEST_EVENT"}'
    )


def test_multiple_v1_accepts_matching_signature():
    raw = OFFICIAL_PAYLOAD.encode("utf-8")
    header = f"v1=DEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF,v1={OFFICIAL_SIGNATURE}"
    assert verify_bridge_signature(raw, header, secrets=[SECRET]) is True


def test_previous_secret_is_accepted():
    raw = b'{"type":"item.refreshed","content":{"item_id":1},"timestamp":1}'
    header = _sign(PREVIOUS, raw)
    assert verify_bridge_signature(raw, header, secrets=[SECRET, PREVIOUS]) is True
    assert verify_bridge_signature(raw, header, secrets=[SECRET]) is False


def test_v0_only_is_rejected():
    raw = OFFICIAL_PAYLOAD.encode("utf-8")
    header = f"v0={OFFICIAL_SIGNATURE}"
    assert verify_bridge_signature(raw, header, secrets=[SECRET]) is False


def test_compare_digest_rejects_modified_body():
    raw = OFFICIAL_PAYLOAD.encode("utf-8")
    tampered = raw[:-1] + (b"X" if raw[-1:] != b"X" else b"Y")
    header = f"v1={OFFICIAL_SIGNATURE}"
    assert verify_bridge_signature(tampered, header, secrets=[SECRET]) is False


def test_provider_event_id_is_sha256_of_raw_body():
    raw = _refreshed_body(4568565, 1612783550980)
    digest = hashlib.sha256(raw).hexdigest()
    assert provider_event_id_from_body(raw) == digest
    assert payload_hash(raw) == digest
    assert len(digest) == 64


def test_same_raw_body_same_provider_event_id():
    raw = _refreshed_body(4568565, 111)
    assert provider_event_id_from_body(raw) == provider_event_id_from_body(raw)


def test_distinct_item_refreshed_bodies_have_distinct_ids():
    a = _refreshed_body(4568565, 111)
    b = _refreshed_body(4568565, 222)
    assert provider_event_id_from_body(a) != provider_event_id_from_body(b)


def test_official_test_event_is_ignored_after_signature(webhook_client):
    client, db, *_ = webhook_client
    raw = OFFICIAL_PAYLOAD.encode("utf-8")
    res = client.post(
        "/api/banking/connectors/bridge/webhook",
        content=raw,
        headers={"BridgeApi-Signature": f"v1={OFFICIAL_SIGNATURE}"},
    )
    assert res.status_code == 200
    assert res.json().get("ignored") is True
    assert db.query(ElfisJob).count() == 0
    receipt = db.query(ElfisBankWebhookReceipt).one()
    assert receipt.provider_event_id == hashlib.sha256(raw).hexdigest()
    assert receipt.status == "ignored"


def test_current_secret_header_enqueues(webhook_client):
    client, db, org, connection = webhook_client
    body = _refreshed_body(4568565, 1612783550980)
    res = client.post(
        "/api/banking/connectors/bridge/webhook",
        content=body,
        headers={"BridgeApi-Signature": _sign(SECRET, body)},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["queued"] is True
    jobs = db.query(ElfisJob).all()
    assert len(jobs) == 1
    assert jobs[0].job_name == "banking.sync_connection.v1"
    assert jobs[0].payload["trigger"] == "webhook"
    assert jobs[0].payload["organization_id"] == org.id
    assert jobs[0].payload["connection_id"] == connection.id
    receipt = db.query(ElfisBankWebhookReceipt).one()
    assert receipt.provider_event_id == hashlib.sha256(body).hexdigest()
    assert receipt.payload_hash == receipt.provider_event_id


def test_previous_secret_http_accepted(webhook_client, monkeypatch):
    client, db, *_ = webhook_client
    monkeypatch.setattr(settings, "banking_bridge_webhook_secret_previous", PREVIOUS)
    body = _refreshed_body(4568565, 99)
    res = client.post(
        "/api/banking/connectors/bridge/webhook",
        content=body,
        headers={"BridgeApi-Signature": _sign(PREVIOUS, body)},
    )
    assert res.status_code == 200
    assert res.json().get("queued") is True


def test_wrong_secret_returns_401(webhook_client):
    client, db, *_ = webhook_client
    body = _refreshed_body(4568565, 1)
    res = client.post(
        "/api/banking/connectors/bridge/webhook",
        content=body,
        headers={"BridgeApi-Signature": _sign("wrong-secret", body)},
    )
    assert res.status_code == 401
    assert db.query(ElfisJob).count() == 0
    assert db.query(ElfisBankWebhookReceipt).count() == 0


def test_one_byte_modified_body_returns_401(webhook_client):
    client, db, *_ = webhook_client
    body = _refreshed_body(4568565, 1)
    header = _sign(SECRET, body)
    tampered = body[:-1] + (b"0" if body[-1:] != b"0" else b"1")
    res = client.post(
        "/api/banking/connectors/bridge/webhook",
        content=tampered,
        headers={"BridgeApi-Signature": header},
    )
    assert res.status_code == 401
    assert db.query(ElfisBankWebhookReceipt).count() == 0


def test_v0_header_returns_401(webhook_client):
    client, db, *_ = webhook_client
    body = _refreshed_body(4568565, 1)
    digest = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest().upper()
    res = client.post(
        "/api/banking/connectors/bridge/webhook",
        content=body,
        headers={"BridgeApi-Signature": f"v0={digest}"},
    )
    assert res.status_code == 401


def test_missing_header_returns_401(webhook_client):
    client, db, *_ = webhook_client
    body = _refreshed_body(4568565, 1)
    res = client.post("/api/banking/connectors/bridge/webhook", content=body)
    assert res.status_code == 401
    assert db.query(ElfisBankWebhookReceipt).count() == 0


def test_missing_secret_fail_closed(webhook_client, monkeypatch):
    client, db, *_ = webhook_client
    monkeypatch.setattr(settings, "banking_bridge_webhook_secret", "")
    body = _refreshed_body(4568565, 1)
    res = client.post(
        "/api/banking/connectors/bridge/webhook",
        content=body,
        headers={"BridgeApi-Signature": _sign(SECRET, body)},
    )
    assert res.status_code == 503
    assert db.query(ElfisJob).count() == 0


def test_duplicate_raw_webhook_one_receipt_one_job(webhook_client):
    client, db, *_ = webhook_client
    body = _refreshed_body(4568565, 1612783550980)
    headers = {"BridgeApi-Signature": _sign(SECRET, body)}
    first = client.post("/api/banking/connectors/bridge/webhook", content=body, headers=headers)
    second = client.post("/api/banking/connectors/bridge/webhook", content=body, headers=headers)
    third = client.post("/api/banking/connectors/bridge/webhook", content=body, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200
    assert second.json().get("duplicate") is True
    assert third.json().get("duplicate") is True
    assert db.query(ElfisJob).count() == 1
    assert db.query(ElfisBankWebhookReceipt).count() == 1


def test_two_item_refreshed_distinct_bodies_two_receipts(webhook_client):
    client, db, *_ = webhook_client
    a = _refreshed_body(4568565, 111)
    b = _refreshed_body(4568565, 222)
    for body in (a, b):
        res = client.post(
            "/api/banking/connectors/bridge/webhook",
            content=body,
            headers={"BridgeApi-Signature": _sign(SECRET, body)},
        )
        assert res.status_code == 200
        assert res.json().get("queued") is True
    receipts = db.query(ElfisBankWebhookReceipt).all()
    ids = {r.provider_event_id for r in receipts}
    assert len(receipts) == 2
    assert ids == {hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest()}


def test_item_account_updated_enqueues_via_item_id(webhook_client):
    client, db, org, connection = webhook_client
    body = json.dumps(
        {
            "content": {
                "account_id": 22908770,
                "item_id": 4568565,
                "nb_new_transactions": 15,
                "user_uuid": "766b2f5d-a942-492c-9ea7-2e5aa88cb672",
            },
            "timestamp": 1612782588323,
            "type": "item.account.updated",
        },
        separators=(",", ":"),
    ).encode("utf-8")
    res = client.post(
        "/api/banking/connectors/bridge/webhook",
        content=body,
        headers={"BridgeApi-Signature": _sign(SECRET, body)},
    )
    assert res.status_code == 200
    assert res.json().get("queued") is True
    job = db.query(ElfisJob).one()
    assert job.payload["connection_id"] == connection.id
    assert job.payload["organization_id"] == org.id


def test_item_account_updated_does_not_resolve_by_account_id(webhook_client):
    client, db, *_ = webhook_client
    body = json.dumps(
        {
            "content": {
                "account_id": 4568565,
                "item_id": 999999,
                "user_uuid": "u",
            },
            "timestamp": 1,
            "type": "item.account.updated",
        },
        separators=(",", ":"),
    ).encode("utf-8")
    res = client.post(
        "/api/banking/connectors/bridge/webhook",
        content=body,
        headers={"BridgeApi-Signature": _sign(SECRET, body)},
    )
    assert res.status_code == 200
    assert res.json().get("ignored") is True
    assert db.query(ElfisJob).count() == 0


@pytest.mark.parametrize(
    "event_type",
    [
        "item.created",
        "item.deleted",
        "item.account.created",
        "item.account.deleted",
        "user.deleted",
        "unknown.future.event",
    ],
)
def test_unsupported_events_are_ignored_2xx(webhook_client, event_type):
    client, db, *_ = webhook_client
    body = json.dumps(
        {
            "content": {"item_id": 4568565, "user_uuid": "u"},
            "timestamp": 3,
            "type": event_type,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    res = client.post(
        "/api/banking/connectors/bridge/webhook",
        content=body,
        headers={"BridgeApi-Signature": _sign(SECRET, body)},
    )
    assert res.status_code == 200
    assert res.json().get("ignored") is True
    assert db.query(ElfisJob).count() == 0
    assert db.query(ElfisBankWebhookReceipt).count() == 1


def test_crash_between_receipt_and_enqueue_recovers(webhook_client):
    client, db, org, connection = webhook_client
    body = _refreshed_body(4568565, 777)
    digest = hashlib.sha256(body).hexdigest()
    db.add(
        ElfisBankWebhookReceipt(
            provider="bridge",
            provider_event_id=digest,
            event_type="item.refreshed",
            payload_hash=digest,
            status="received",
        )
    )
    db.commit()
    assert db.query(ElfisJob).count() == 0
    res = client.post(
        "/api/banking/connectors/bridge/webhook",
        content=body,
        headers={"BridgeApi-Signature": _sign(SECRET, body)},
    )
    assert res.status_code == 200
    assert res.json().get("queued") is True
    assert db.query(ElfisJob).count() == 1
    assert db.query(ElfisBankWebhookReceipt).count() == 1
    receipt = db.query(ElfisBankWebhookReceipt).one()
    assert receipt.status == "queued"
    assert receipt.job_id
    assert receipt.connection_id == connection.id
    assert receipt.organization_id == org.id


def test_webhook_tenant_isolation(webhook_client):
    client, db, org, connection = webhook_client
    other = seed_org(db, "Org Autre")
    foreign = ElfisBankConnection(
        organization_id=other.id,
        provider="bridge",
        provider_connection_id="999999",
        bank_name="Autre",
        status="connected",
    )
    db.add(foreign)
    db.commit()
    body = _refreshed_body(4568565, 42)
    res = client.post(
        "/api/banking/connectors/bridge/webhook",
        content=body,
        headers={"BridgeApi-Signature": _sign(SECRET, body)},
    )
    assert res.status_code == 200
    job = db.query(ElfisJob).one()
    assert job.organization_id == org.id
    assert job.payload["connection_id"] == connection.id
    assert job.payload["connection_id"] != foreign.id


def test_webhook_logs_contain_no_secrets(webhook_client, caplog):
    caplog.set_level(logging.INFO)
    client, *_ = webhook_client
    body = _refreshed_body(4568565, 7)
    client.post(
        "/api/banking/connectors/bridge/webhook",
        content=body,
        headers={"BridgeApi-Signature": _sign(SECRET, body)},
    )
    text = caplog.text
    assert SECRET not in text
    assert "644b2ac3" not in text
    assert "Client-Secret" not in text
    assert "iban" not in text.lower()
