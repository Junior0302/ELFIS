"""SQLite recette pour tests de concurrence — connexion distincte par Session."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, Pool


def build_concurrency_sqlite_recette(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    poolclass: type[Pool] = NullPool,
) -> Iterator[dict[str, Any]]:
    """Même schéma/seed que functional_db, pool NullPool pour accès concurrent."""
    db_file = tmp_path / "elfis_concurrency_recette.db"
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

    from app.database import get_db
    from app.main import app
    from tests.functional.conftest import bind_and_init_recette_schema
    from tests.functional.seed import assert_safe_environment, seed_functional_fixtures

    assert_safe_environment(database_url=url, environment="test")

    engine = create_engine(
        url,
        connect_args={"check_same_thread": False},
        poolclass=poolclass,
    )
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    bind_and_init_recette_schema(engine, TestingSession)
    # Le lifespan a déjà importé init_db par nom : désactiver la 2e init (concurrence).
    import app.main as main_module

    monkeypatch.setattr(main_module, "init_db", lambda: None)

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

    with TestClient(app) as client:
        yield {
            "app": app,
            "client": client,
            "Session": TestingSession,
            "seed": seed,
            "url": url,
            "engine": engine,
        }

    app.dependency_overrides.clear()
    engine.dispose()
