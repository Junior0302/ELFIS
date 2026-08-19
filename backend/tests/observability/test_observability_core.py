"""Tests Observability V1."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("AUTH_REQUIRED", "false")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "obs.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "development")

    from app.config import settings

    settings.database_url = url
    settings.app_env = "development"
    settings.auth_required = False
    settings.elfis_metrics_enabled = True
    settings.elfis_metrics_require_auth = True

    from app.database import Base, get_db, init_db
    from app.main import app
    from app.observability.metrics import metrics_registry

    metrics_registry.reset()
    engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    init_db()

    def _override():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    metrics_registry.reset()


def test_live_health_ok(client):
    r = client.get("/api/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ready_db_ok(client):
    r = client.get("/api/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["checks"]["database"]["status"] == "ok"


def test_metrics_protected(client):
    r = client.get("/api/metrics")
    assert r.status_code in (401, 403)


def test_http_metric_incremented(client):
    from app.observability.metrics import metrics_registry

    before = metrics_registry.snapshot()
    client.get("/api/health/live")
    after = metrics_registry.snapshot()
    assert "http_requests_total" in after["counters"]
    assert after["counters"]["http_requests_total"]


def test_structured_log_context_has_ids():
    from app.observability.request_context import bind_request_ids, clear_request_context, current_context
    from app.security.security_redaction import safe_log_context

    bind_request_ids(request_id="req-abc-12345678", correlation_id="corr-xyz-12345678")
    try:
        ctx = current_context()
        assert ctx["request_id"] == "req-abc-12345678"
        log = safe_log_context(event_type="test", body={"secret": "x"}, prompt="nope")
        assert "prompt" not in log or log.get("prompt") == "***"
        assert log.get("secret") == "***" or "secret" not in log
    finally:
        clear_request_context()


def test_error_code_stable():
    from app.security.security_exceptions import build_error_body
    from app.security.security_types import ErrorCode

    body = build_error_body(
        code=ErrorCode.INTERNAL_ERROR,
        message="Erreur serveur inattendue",
        request_id="r1",
        correlation_id="c1",
    )
    assert body["error"]["code"] == "internal_error"
    assert "traceback" not in body


def test_details_health_requires_admin(client):
    r = client.get("/api/health/details")
    assert r.status_code in (401, 403)


def test_incident_dedup(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import Base
    from app.platform_admin.admin_incident_service import AdminIncidentService
    from app.platform_admin.admin_models import ElfisOperationalIncident

    url = f"sqlite:///{(tmp_path / 'inc.db').as_posix()}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        svc = AdminIncidentService(db)
        a = svc.upsert_incident(
            incident_type="stale_job",
            source_type="job",
            source_id="j1",
            title="stale",
        )
        b = svc.upsert_incident(
            incident_type="stale_job",
            source_type="job",
            source_id="j1",
            title="stale again",
        )
        db.commit()
        assert a.incident_id == b.incident_id
        assert db.query(ElfisOperationalIncident).count() == 1
    finally:
        db.close()
