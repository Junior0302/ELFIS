"""Tests Security V1 — request IDs, headers, rate limit, redaction, fichiers."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Env avant import settings/app
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("AUTH_REQUIRED", "false")
os.environ.setdefault("ELFIS_RATE_LIMIT_AUTH_PER_MINUTE", "3")
os.environ.setdefault("ELFIS_HSTS_ENABLED", "false")
os.environ.setdefault("ELFIS_SECURITY_HEADERS_ENABLED", "true")
os.environ.setdefault("ELFIS_CSP_ENABLED", "true")
os.environ.setdefault("ELFIS_CSP_REPORT_ONLY", "true")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "sec.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    monkeypatch.setenv("ELFIS_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("ELFIS_RATE_LIMIT_AUTH_PER_MINUTE", "3")

    from app.config import settings

    settings.database_url = url
    settings.app_env = "development"
    settings.auth_required = False
    settings.elfis_rate_limit_enabled = True
    settings.elfis_rate_limit_auth_per_minute = 3
    settings.elfis_security_headers_enabled = True
    settings.elfis_hsts_enabled = False
    settings.elfis_csp_enabled = True
    settings.elfis_csp_report_only = True

    from app.database import get_db
    from app.main import app
    from app.security.security_rate_limit import get_rate_limit_backend
    from tests.functional.conftest import bind_and_init_recette_schema

    get_rate_limit_backend().reset()

    engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    bind_and_init_recette_schema(engine, TestingSession)

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
    get_rate_limit_backend().reset()


def test_request_id_generated(client):
    r = client.get("/api/health/live")
    assert r.status_code == 200
    assert r.headers.get("X-Request-Id")
    assert r.headers.get("X-Correlation-Id")
    assert r.headers["X-Request-Id"] == r.headers["X-Correlation-Id"]


def test_request_id_preserved(client):
    rid = "req-valid-id-12345"
    r = client.get("/api/health/live", headers={"X-Request-Id": rid, "X-Correlation-Id": "corr-valid-id-999"})
    assert r.headers["X-Request-Id"] == rid
    assert r.headers["X-Correlation-Id"] == "corr-valid-id-999"


def test_request_id_invalid_replaced(client):
    r = client.get("/api/health/live", headers={"X-Request-Id": "bad"})
    assert r.headers["X-Request-Id"] != "bad"
    assert len(r.headers["X-Request-Id"]) >= 8


def test_security_headers_present(client):
    r = client.get("/api/health/live")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy-Report-Only" in r.headers


def test_hsts_absent_in_development(client):
    r = client.get("/api/health/live")
    assert "Strict-Transport-Security" not in r.headers


def test_normalized_error_and_no_stack(client):
    r = client.get("/api/platform/security/events")
    assert r.status_code in (401, 403)
    body = r.json()
    assert "error" in body
    assert body["error"]["code"]
    assert body["error"]["request_id"]
    assert "traceback" not in str(body).lower()
    assert "detail" in body  # compat


def test_redaction_password_token_secret_prompt():
    from app.security.security_redaction import redact_mapping, redact_string

    assert "***" in (redact_string("password=supersecret123") or "")
    data = redact_mapping(
        {
            "password": "x",
            "token": "y",
            "api_key": "z",
            "prompt": "full prompt text",
            "ok": "safe",
        }
    )
    assert data["password"] == "***"
    assert data["token"] == "***"
    assert data["api_key"] == "***"
    assert data["prompt"] == "***"
    assert data["ok"] == "safe"


def test_file_validation_rejects_traversal_double_ext_mime():
    from app.security.security_exceptions import SecurityError
    from app.security.security_file_validation import validate_uploaded_file

    with pytest.raises(SecurityError):
        validate_uploaded_file(
            filename="../etc/passwd.pdf",
            content_type="application/pdf",
            content=b"%PDF-1.4",
            max_bytes=1000,
        )
    with pytest.raises(SecurityError):
        validate_uploaded_file(
            filename="invoice.php.pdf",
            content_type="application/pdf",
            content=b"%PDF-1.4",
            max_bytes=1000,
        )
    with pytest.raises(SecurityError):
        validate_uploaded_file(
            filename="doc.pdf",
            content_type="text/html",
            content=b"%PDF-1.4",
            max_bytes=1000,
        )
    with pytest.raises(SecurityError):
        validate_uploaded_file(
            filename="doc.pdf",
            content_type="application/pdf",
            content=b"NOTPDF",
            max_bytes=1000,
        )


def test_rate_limit_auth_triggers(client):
    from app.security.security_rate_limit import get_rate_limit_backend

    get_rate_limit_backend().reset()
    last = None
    for _ in range(5):
        last = client.post("/api/auth/login", json={"email": "a@b.c", "password": "x"})
    assert last is not None
    assert last.status_code == 429
    assert last.headers.get("Retry-After")
    assert last.json()["error"]["code"] == "rate_limit_exceeded"


def test_auth_path_categories_cover_real_firebase_login():
    from app.security.security_rate_limit import category_for_path
    from app.security.security_types import RateLimitCategory

    assert category_for_path("/api/auth/firebase") == RateLimitCategory.AUTH
    assert category_for_path("/api/auth/firebase/") == RateLimitCategory.AUTH
    assert category_for_path("/api/auth/firebase-session") == RateLimitCategory.AUTH
    assert category_for_path("/api/auth/login") == RateLimitCategory.AUTH
    assert category_for_path("/api/auth/register") == RateLimitCategory.AUTH
    assert category_for_path("/api/auth/me") is None
    assert category_for_path("/api/health/live") is None


def test_rate_limit_firebase_auth_triggers(client):
    from app.security.security_rate_limit import get_rate_limit_backend

    get_rate_limit_backend().reset()
    first = client.post("/api/auth/firebase", json={"id_token": "not-a-valid-firebase-token"})
    assert first.status_code != 429
    last = first
    for _ in range(4):
        last = client.post("/api/auth/firebase", json={"id_token": "not-a-valid-firebase-token"})
    assert last.status_code == 429
    assert last.headers.get("Retry-After")
    assert last.json()["error"]["code"] == "rate_limit_exceeded"


def test_rate_limit_firebase_path_variation_still_auth(client):
    from app.security.security_rate_limit import get_rate_limit_backend

    get_rate_limit_backend().reset()
    last = None
    for _ in range(5):
        last = client.post("/api/auth/firebase/", json={"id_token": "not-a-valid-firebase-token"})
    assert last is not None
    assert last.status_code == 429
    assert last.json()["error"]["code"] == "rate_limit_exceeded"


def test_payload_too_large_declared(client):
    r = client.post(
        "/api/auth/login",
        headers={"Content-Length": str(20_000_000)},
        content=b"{}",
    )
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "payload_too_large"


def test_cors_wildcard_fatal_in_production():
    from app.security.security_startup import ConfigIssue, validate_runtime_configuration
    from app.config import settings

    prev_env = settings.app_env
    prev_cors = settings.cors_origins
    prev_elfis = getattr(settings, "elfis_environment", "")
    try:
        settings.app_env = "production"
        settings.elfis_environment = "production"
        settings.cors_origins = "*"
        settings.jwt_secret = "x" * 40
        issues = validate_runtime_configuration()
        assert any(i.code == "cors_wildcard" and i.level == "fatal" for i in issues)
    finally:
        settings.app_env = prev_env
        settings.cors_origins = prev_cors
        settings.elfis_environment = prev_elfis


def test_dev_weak_secret_warning():
    from app.config import settings
    from app.security.security_startup import validate_runtime_configuration

    prev = settings.jwt_secret
    prev_env = settings.app_env
    try:
        settings.app_env = "development"
        settings.elfis_environment = "development"
        settings.jwt_secret = "short"
        issues = validate_runtime_configuration()
        assert any(i.code == "weak_jwt_secret" and i.level == "warning" for i in issues)
    finally:
        settings.jwt_secret = prev
        settings.app_env = prev_env


def test_security_event_recorded(tmp_path, monkeypatch):
    from datetime import datetime
    from uuid import uuid4

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import Base
    from app.security.security_audit import record_security_event
    from app.security.security_models import ElfisSecurityEvent
    from app.security.security_types import SecurityEventType

    url = f"sqlite:///{(tmp_path / 'sev.db').as_posix()}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        payload = record_security_event(
            db,
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            route="/api/auth/login",
            details={"password": "should-not-appear", "category": "auth"},
            request_id="req-1",
            correlation_id="corr-1",
        )
        db.commit()
        assert payload is not None
        row = db.query(ElfisSecurityEvent).first()
        assert row is not None
        assert "password" not in str(row.details)
        assert row.details.get("category") == "auth"
    finally:
        db.close()
