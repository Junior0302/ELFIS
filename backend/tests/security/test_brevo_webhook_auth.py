"""P1-06 — Brevo webhook doit être fail-closed si le secret est absent."""

from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("AUTH_REQUIRED", "false")

GOOD_SECRET = "brevo-test-secret-42"
BREVO_PAYLOAD = [{"event": "delivered", "message-id": "msg-brevo-test-1"}]


@pytest.fixture()
def _brevo_app(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'brevo.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)

    from app.config import settings

    settings.database_url = url
    settings.auth_required = False

    from app.database import get_db
    from app.main import app
    from tests.functional.conftest import bind_and_init_recette_schema

    engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    bind_and_init_recette_schema(engine, Session)

    def _override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    yield {"app": app, "settings": settings, "Session": Session}
    app.dependency_overrides.clear()


def _client(ctx):
    return TestClient(ctx["app"])


def test_secret_absent_rejects_webhook(_brevo_app):
    _brevo_app["settings"].brevo_webhook_secret = ""
    client = _client(_brevo_app)
    r = client.post("/api/webhooks/brevo", json=BREVO_PAYLOAD)
    assert r.status_code == 503


def test_secret_absent_no_data_modified(_brevo_app):
    from app.models_saas import DocumentEmailLog

    _brevo_app["settings"].brevo_webhook_secret = ""
    db = _brevo_app["Session"]()
    try:
        log = DocumentEmailLog(
            organization_id=1,
            provider="brevo",
            provider_message_id="msg-brevo-test-1",
            status="sent",
        )
        db.add(log)
        db.commit()
    finally:
        db.close()

    client = _client(_brevo_app)
    r = client.post("/api/webhooks/brevo", json=BREVO_PAYLOAD)
    assert r.status_code == 503

    db2 = _brevo_app["Session"]()
    try:
        row = db2.query(DocumentEmailLog).filter_by(provider_message_id="msg-brevo-test-1").first()
        assert row is not None
        assert row.status == "sent"
    finally:
        db2.close()


def test_wrong_secret_rejected(_brevo_app):
    _brevo_app["settings"].brevo_webhook_secret = GOOD_SECRET
    client = _client(_brevo_app)
    r = client.post(
        "/api/webhooks/brevo",
        json=BREVO_PAYLOAD,
        headers={"X-Comptapilot-Webhook-Secret": "wrong-secret"},
    )
    assert r.status_code == 401


def test_missing_header_rejected(_brevo_app):
    _brevo_app["settings"].brevo_webhook_secret = GOOD_SECRET
    client = _client(_brevo_app)
    r = client.post("/api/webhooks/brevo", json=BREVO_PAYLOAD)
    assert r.status_code == 401


def test_correct_secret_accepted(_brevo_app):
    _brevo_app["settings"].brevo_webhook_secret = GOOD_SECRET
    client = _client(_brevo_app)
    r = client.post(
        "/api/webhooks/brevo",
        json=BREVO_PAYLOAD,
        headers={"X-Comptapilot-Webhook-Secret": GOOD_SECRET},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True
