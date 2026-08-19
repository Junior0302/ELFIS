"""Conftest recette fonctionnelle — SQLite isolée, seed, client API."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Environnement recette avant imports settings
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ELFIS_ENVIRONMENT", "test")
os.environ.setdefault("AUTH_REQUIRED", "true")
os.environ.setdefault("ELFIS_RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("ELFIS_RATE_LIMIT_AUTH_PER_MINUTE", "60")
os.environ.setdefault("ELFIS_CLEANUP_ENABLED", "false")
os.environ.setdefault("ELFIS_HSTS_ENABLED", "false")
os.environ.setdefault("ELFIS_OCR_ENABLED", "false")
os.environ.setdefault("ELFIS_BILLING_ENFORCE_ENTITLEMENTS", "false")
os.environ.setdefault("ELFIS_BILLING_ENFORCE_QUOTAS", "false")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("STRIPE_SECRET_KEY", "")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_recette_test_only")


@pytest.fixture()
def functional_db(tmp_path, monkeypatch):
    db_file = tmp_path / "elfis_functional_recette.db"
    url = f"sqlite:///{db_file.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ELFIS_ENVIRONMENT", "test")
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("PLATFORM_ADMIN_EMAILS", "platform.admin@test.elfis.local")

    from app.config import settings

    settings.database_url = url
    settings.app_env = "test"
    settings.elfis_environment = "test"
    settings.auth_required = True
    settings.platform_admin_emails = "platform.admin@test.elfis.local"
    settings.elfis_billing_enforce_entitlements = False
    settings.elfis_billing_enforce_quotas = False
    settings.elfis_billing_past_due_grace_days = 7
    settings.stripe_past_due_grace_days = 7
    settings.elfis_rate_limit_enabled = False
    settings.elfis_cleanup_enabled = False
    settings.elfis_hsts_enabled = False
    settings.openai_api_key = ""
    settings.stripe_secret_key = ""

    from app.database import Base, get_db
    from app.main import app
    from tests.functional.seed import assert_safe_environment, seed_functional_fixtures

    assert_safe_environment(database_url=url, environment="test")

    engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    # Rebind le moteur module pour que le lifespan FastAPI n’utilise pas Postgres RC1
    import app.database as database_module

    database_module.engine = engine
    database_module.SessionLocal = TestingSession
    # Pas d'init_db() global : create_all sur le moteur de test suffit.

    db = TestingSession()
    try:
        seed = seed_functional_fixtures(db)
    finally:
        db.close()

    def _override():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override

    yield {"app": app, "Session": TestingSession, "seed": seed, "url": url, "engine": engine}

    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture()
def mock_vault_storage(monkeypatch):
    from tests.functional.helpers.phase_c import install_mock_vault_storage

    return install_mock_vault_storage(monkeypatch)


@pytest.fixture()
def api(functional_db, mock_vault_storage):
    from tests.functional.helpers.api_client import FunctionalClient

    with TestClient(functional_db["app"]) as client:
        yield FunctionalClient(client, seed=functional_db["seed"])


@pytest.fixture()
def documents_dir() -> Path:
    path = Path(__file__).resolve().parent / "fixtures" / "documents"
    path.mkdir(parents=True, exist_ok=True)
    return path
