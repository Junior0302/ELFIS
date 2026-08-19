"""Helpers tests PostgreSQL RC1 / RC2.5."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# Import models for create_all
import app.billing.billing_models  # noqa: F401
import app.events.event_models  # noqa: F401
import app.jobs.job_models  # noqa: F401
from app.database import Base

_BACKEND = Path(__file__).resolve().parents[2]


def load_backend_dotenv() -> None:
    """Charge backend/.env sans écraser les variables déjà présentes."""
    path = _BACKEND / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, raw = s.split("=", 1)
        key = key.strip()
        val = raw.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def ensure_postgres_test_env() -> None:
    """Complète les garde-fous RC1 pour staging Supabase (sans révéler l'URL)."""
    load_backend_dotenv()
    if not postgres_tests_enabled():
        return
    # Forcer staging : le conftest fonctionnel peut imposer APP_ENV=test,
    # incompatible avec l'allowlist Supabase (staging + managed host).
    os.environ["ELFIS_ENVIRONMENT"] = "staging"
    os.environ["APP_ENV"] = "staging"
    # Bridge non-live pour toute certification concurrence
    os.environ["COMPTAPILOT_DOCUMENT_BRIDGE_MODE"] = "disabled"
    os.environ["COMPTAPILOT_DOCUMENT_PUBLISH_ENABLED"] = "false"
    os.environ["COMPTAPILOT_DOCUMENT_AUTO_PUBLISH"] = "false"

    raw = (
        os.getenv("ELFIS_RC1_DATABASE_URL")
        or os.getenv("ELFIS_PERFORMANCE_DATABASE_URL")
        or ""
    ).strip()
    if not raw:
        return
    from scripts.rc1.safety import database_name_from_url, normalize_postgres_url

    url = normalize_postgres_url(raw)
    host = (urlparse(url).hostname or "").strip().lower()
    name = database_name_from_url(url)
    is_supabase = host.endswith(".supabase.co") or host.endswith(".supabase.com")
    if is_supabase and name == "postgres":
        os.environ["ELFIS_RC1_ALLOW_MANAGED_HOST"] = "true"
        os.environ["ELFIS_RC1_ALLOWED_MANAGED_HOST"] = host


def postgres_url() -> str:
    from scripts.rc1.safety import normalize_postgres_url

    ensure_postgres_test_env()
    # RC2.5.8 : priorité explicite à ELFIS_RC1_DATABASE_URL (staging certifié)
    raw = (
        os.getenv("ELFIS_RC1_DATABASE_URL")
        or os.getenv("ELFIS_PERFORMANCE_DATABASE_URL")
        or ""
    ).strip()
    return normalize_postgres_url(raw) if raw else ""


def postgres_tests_enabled() -> bool:
    load_backend_dotenv()
    return os.getenv("ELFIS_POSTGRES_TESTS_ENABLED", "").lower() in {"1", "true", "yes"}


def require_postgres():
    """Skip si pas de base PG de recette configurée."""
    ensure_postgres_test_env()
    if not postgres_tests_enabled():
        pytest.skip("ELFIS_POSTGRES_TESTS_ENABLED!=true — PostgreSQL RC1 NOT EXECUTED")
    url = postgres_url()
    if not url.lower().startswith("postgres"):
        pytest.skip("ELFIS_RC1_DATABASE_URL absent — PostgreSQL RC1 NOT EXECUTED")
    if str(_BACKEND) not in sys.path:
        sys.path.insert(0, str(_BACKEND))
    try:
        from scripts.rc1.safety import assert_safe_postgres_url, assert_safe_rc1_environment

        assert_safe_rc1_environment()
        assert_safe_postgres_url(url)
    except RuntimeError as exc:
        pytest.skip(f"Garde-fou RC1: {exc}")
    return url


@lru_cache(maxsize=1)
def _engine_for(url: str):
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=int(os.getenv("ELFIS_DATABASE_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("ELFIS_DATABASE_MAX_OVERFLOW", "10")),
        pool_timeout=int(os.getenv("ELFIS_DATABASE_POOL_TIMEOUT", "30")),
        pool_recycle=int(os.getenv("ELFIS_DATABASE_POOL_RECYCLE", "1800")),
        poolclass=QueuePool,
        # Pooler Supabase (PgBouncer) : prepared statements interdits
        connect_args={"prepare_threshold": None},
    )


def make_pg_session_factory(url: str | None = None):
    url = url or require_postgres()
    engine = _engine_for(url)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine), engine


def pg_version(engine) -> str:
    with engine.connect() as conn:
        return str(conn.execute(text("SHOW server_version")).scalar())


def checked_out_connections(engine) -> int:
    pool = engine.pool
    return int(getattr(pool, "checkedout", lambda: 0)())
