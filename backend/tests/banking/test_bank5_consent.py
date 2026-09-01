"""BANK-5 — consent_status, expiration, blocage sync, classification erreurs."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.banking.banking_models import ElfisBankConnection
from app.banking.consent import (
    can_reauthenticate,
    classify_item_status,
    consent_status,
    needs_reauth,
    parse_expires_at,
)
from app.banking.connectors import registry
from app.banking.connectors.base import ConnectorError, ConnectorNotConfiguredError
from app.banking.engine import BankingEngine, BankingEngineError
from app.banking.errors import classify_connector_error, error_class
from app.banking.sweep import select_stale_connections
from app.banking.sync_engine import SyncEngine
from app.banking.sync_jobs import BankingSyncEnqueueError, enqueue_connection_sync
from app.config import settings
from app.jobs import bootstrap_job_handlers
from app.jobs.job_models import ElfisJob
from app.jobs.job_types import JobStatus
from app.jobs.job_worker import JobWorker
from app.models import BankAccount, BankTransaction
from app.observability.metrics import metrics_registry

from tests.banking.conftest_helpers import (
    FakeBankConnector,
    make_banking_session_factory,
    make_tx,
    seed_org,
)


@pytest.fixture()
def bank5_ctx(monkeypatch):
    monkeypatch.setattr(settings, "elfis_job_worker_enabled", True)
    monkeypatch.setattr(settings, "banking_reauth_warning_days", 7)
    metrics_registry.reset()
    bootstrap_job_handlers()
    factory, engine = make_banking_session_factory()
    db = factory()
    org = seed_org(db)
    connector = FakeBankConnector(
        transactions={
            "fake-acc-1": [
                make_tx("fake-acc-1", date(2026, 7, 1), "VIREMENT CLIENT ALPHA", 500.0),
            ]
        }
    )
    registry.register_connector("fake", lambda: connector)
    connection = BankingEngine(db).connect(
        organization_id=org.id, provider="fake", bank_name="Banque Factice"
    )
    yield {
        "db": db,
        "factory": factory,
        "org": org,
        "connection": connection,
        "connector": connector,
    }
    registry.unregister_connector("fake")
    db.close()


def _connection(db, org, **kwargs) -> ElfisBankConnection:
    row = ElfisBankConnection(
        organization_id=org.id,
        provider=kwargs.pop("provider", "bridge"),
        provider_connection_id=kwargs.pop("provider_connection_id", "item-1"),
        bank_name=kwargs.pop("bank_name", "Banque"),
        status=kwargs.pop("status", "connected"),
        last_sync_status=kwargs.pop("last_sync_status", "success"),
        **kwargs,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_consent_valid_without_expiry():
    db = make_banking_session_factory()[0]()
    org = seed_org(db)
    connection = _connection(db, org)
    assert consent_status(connection) == "valid"
    assert needs_reauth(connection) is False
    db.close()


def test_expiration_beyond_warning_is_valid(monkeypatch):
    monkeypatch.setattr(settings, "banking_reauth_warning_days", 7)
    db = make_banking_session_factory()[0]()
    org = seed_org(db)
    now = datetime(2026, 8, 27, 12, 0, 0)
    connection = _connection(db, org, authentication_expires_at=now + timedelta(days=30))
    assert consent_status(connection, now=now) == "valid"
    assert needs_reauth(connection, now=now) is False
    db.close()


def test_expiration_within_warning_is_expiring(monkeypatch):
    monkeypatch.setattr(settings, "banking_reauth_warning_days", 7)
    db = make_banking_session_factory()[0]()
    org = seed_org(db)
    now = datetime(2026, 8, 27, 12, 0, 0)
    connection = _connection(db, org, authentication_expires_at=now + timedelta(days=3))
    assert consent_status(connection, now=now) == "expiring"
    assert needs_reauth(connection, now=now) is False
    db.close()


def test_expiration_past_needs_reauth(monkeypatch):
    monkeypatch.setattr(settings, "banking_reauth_warning_days", 7)
    db = make_banking_session_factory()[0]()
    org = seed_org(db)
    now = datetime(2026, 8, 27, 12, 0, 0)
    connection = _connection(db, org, authentication_expires_at=now - timedelta(hours=1))
    assert consent_status(connection, now=now) == "reauth_required"
    assert needs_reauth(connection, now=now) is True
    db.close()


def test_parse_expires_at_iso():
    parsed = parse_expires_at("2025-09-04T10:25:35Z")
    assert parsed is not None
    assert parsed.year == 2025


def test_classify_item_status_documented_and_fail_safe():
    assert classify_item_status(0) is None
    assert classify_item_status(1010) == "sca_required"
    assert classify_item_status(1010, "otp_required") == "sca_required"
    assert classify_item_status(42) == "item_action_required"
    assert classify_item_status(None) is None


def test_http_401_is_not_consent_expired():
    code, retryable = classify_connector_error(
        ConnectorError("Requête Bridge refusée (401)", retryable=False, status_code=401)
    )
    assert code == "provider_unauthorized"
    assert retryable is False
    assert error_class(code) == "configuration"


def test_not_configured_is_configuration():
    code, retryable = classify_connector_error(ConnectorNotConfiguredError("bridge"))
    assert code == "invalid_client"
    assert retryable is False


def test_sync_blocked_when_reauth_required(bank5_ctx):
    connection = bank5_ctx["connection"]
    connection.reauth_reason = "consent_expired"
    connection.reauth_required_at = datetime.utcnow()
    bank5_ctx["db"].add(connection)
    bank5_ctx["db"].commit()
    with pytest.raises(BankingEngineError, match="action utilisateur"):
        SyncEngine(bank5_ctx["db"]).run_sync(
            bank5_ctx["org"].id,
            connection_id=connection.id,
            trigger="manual",
        )


def test_job_completes_user_action_required_no_retry_storm(bank5_ctx):
    connection = bank5_ctx["connection"]
    enqueue_connection_sync(
        bank5_ctx["db"],
        organization_id=bank5_ctx["org"].id,
        connection_id=connection.id,
        trigger="scheduled",
        idempotency_key="queued-then-reauth",
    )
    connection.reauth_reason = "sca_required"
    connection.reauth_required_at = datetime.utcnow()
    bank5_ctx["db"].add(connection)
    bank5_ctx["db"].commit()
    JobWorker(
        bank5_ctx["db"],
        worker_id="w-bank5",
        session_factory=bank5_ctx["factory"],
    ).process_next_batch()
    bank5_ctx["db"].expire_all()
    job = (
        bank5_ctx["db"]
        .query(ElfisJob)
        .filter(ElfisJob.idempotency_key == "queued-then-reauth")
        .one()
    )
    assert job.status == JobStatus.COMPLETED
    assert (job.result or {}).get("reason") == "user_action_required"
    assert (job.result or {}).get("skipped") is True
    assert job.progress_message == "user_action_required"
    assert bank5_ctx["db"].query(ElfisJob).count() == 1
    with pytest.raises(BankingSyncEnqueueError, match="action utilisateur"):
        enqueue_connection_sync(
            bank5_ctx["db"],
            organization_id=bank5_ctx["org"].id,
            connection_id=connection.id,
            trigger="scheduled",
            idempotency_key="blocked-reauth",
        )
    assert bank5_ctx["db"].query(ElfisJob).count() == 1


def test_sweep_skips_expired_and_user_action(bank5_ctx):
    db = bank5_ctx["db"]
    org = bank5_ctx["org"]
    expired = _connection(
        db,
        org,
        provider="fake",
        provider_connection_id="expired-item",
        authentication_expires_at=datetime.utcnow() - timedelta(days=1),
        last_sync_at=datetime.utcnow() - timedelta(hours=72),
    )
    selected = select_stale_connections(db, stale_hours=24, limit=50)
    ids = {c.id for c in selected}
    assert expired.id not in ids
    assert bank5_ctx["connection"].id in ids


def test_item_deleted_does_not_delete_history(bank5_ctx):
    from app.banking.consent import mark_revoked

    db = bank5_ctx["db"]
    connection = bank5_ctx["connection"]
    account = db.query(BankAccount).first()
    assert account is not None
    tx_count = db.query(BankTransaction).count()
    acc_count = db.query(BankAccount).count()
    mark_revoked(connection)
    db.add(connection)
    db.commit()
    assert connection.status == "disconnected"
    assert db.query(BankTransaction).count() == tx_count
    assert db.query(BankAccount).count() == acc_count
    assert db.query(BankAccount).first().id == account.id


def test_can_reauthenticate_bridge_only():
    db = make_banking_session_factory()[0]()
    org = seed_org(db)
    bridge = _connection(db, org, provider="bridge")
    demo = _connection(db, org, provider="demo", provider_connection_id="demo-1")
    gone = _connection(
        db, org, provider="bridge", provider_connection_id="x", status="disconnected"
    )
    reconnecting = _connection(
        db,
        org,
        provider="bridge",
        provider_connection_id="item-reauth",
        status="awaiting_consent",
    )
    assert can_reauthenticate(bridge) is True
    assert can_reauthenticate(demo) is False
    assert can_reauthenticate(gone) is False
    assert consent_status(reconnecting) == "reconnecting"
    db.close()
