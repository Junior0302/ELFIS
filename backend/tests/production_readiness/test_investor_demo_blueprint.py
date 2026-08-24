"""Garde-fous blueprint investor-demo — aucun SQLite, aucun secret."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"


def test_render_yaml_has_no_sqlite_and_links_postgres():
    text = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "sqlite" not in text.lower()
    assert "fromDatabase:" in text
    assert "property: connectionString" in text
    assert "ELFIS_ENVIRONMENT" in text
    assert "ELFIS_BILLING_ENABLED" in text
    assert "ELFIS_DEMO_BANK_ENABLED" in text
    assert "preDeployCommand: python -m scripts.rc1.migrate_sql" in text
    assert "healthCheckPath: /api/health/live" in text
    assert "STORAGE_DIR" in text
    assert "/data/storage" in text
    assert "generateValue: true" in text
    for leaked in ("sk_live_", "sk_test_", "xsmtpsib-", "xkeysib-", "whsec_"):
        assert leaked not in text


def test_ignore_files_do_not_exclude_app_storage_package():
    """Bare `storage/` would drop the Python package from Git and the Docker image."""
    init = BACKEND / "app" / "storage" / "__init__.py"
    integrity = BACKEND / "app" / "storage" / "storage_integrity_service.py"
    assert init.is_file()
    assert integrity.is_file()

    dockerignore_lines = [
        line.strip()
        for line in (BACKEND / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert "storage" not in dockerignore_lines
    assert "storage/" not in dockerignore_lines
    assert any(line.startswith("/storage") for line in dockerignore_lines)
    assert "!app/storage" in dockerignore_lines or "!app/storage/" in dockerignore_lines
    assert "!app/storage/**" in dockerignore_lines

    gitignore_lines = [
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert "storage/" not in gitignore_lines
    assert "/storage/" in gitignore_lines
    assert "/backend/storage/" in gitignore_lines


def test_dockerfile_has_no_sqlite_default_and_ships_migrations():
    text = (BACKEND / "Dockerfile").read_text(encoding="utf-8")
    assert "sqlite" not in text.lower()
    assert "COPY sql ./sql" in text
    assert "COPY scripts/rc1/migrate_sql.py" in text
    assert "STORAGE_DIR=/data/storage" in text


def test_sql_order_includes_bank2_and_bank3():
    from scripts.rc1.migrate_sql import SQL_DIR, SQL_ORDER, missing_sql_files

    assert "elfis_banking_bank2_postgres.sql" in SQL_ORDER
    assert "elfis_banking_bank3_postgres.sql" in SQL_ORDER
    assert SQL_ORDER.index("elfis_banking_bank2_postgres.sql") < SQL_ORDER.index(
        "elfis_banking_bank3_postgres.sql"
    )
    assert missing_sql_files() == []
    for name in SQL_ORDER:
        assert (SQL_DIR / name).is_file(), name


def test_firebase_hosting_rewrites_spa():
    text = (ROOT / "firebase.json").read_text(encoding="utf-8")
    assert '"destination": "/index.html"' in text
    assert '"source": "**"' in text


def test_investor_demo_example_env_has_no_secrets():
    text = (BACKEND / ".env.investor-demo.example").read_text(encoding="utf-8")
    assert "DATABASE_URL=" in text
    assert "sqlite://" not in text.lower()
    assert "sqlite:/" not in text.lower()
    assert "JWT_SECRET=" in text
    assert "ELFIS_DEMO_BANK_ENABLED=true" in text
    assert "ELFIS_BILLING_ENABLED=false" in text
    for leaked in ("sk_live_", "AIza", "xsmtpsib-", "xkeysib-"):
        assert leaked not in text
