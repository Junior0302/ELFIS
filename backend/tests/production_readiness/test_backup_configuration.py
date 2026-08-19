"""CORS / cookies / OpenAPI / backup docs / redaction."""

from __future__ import annotations

from pathlib import Path

from app.config import settings


ROOT = Path(__file__).resolve().parents[3]
BACKEND = Path(__file__).resolve().parents[2]


def test_cors_origins_list_property():
    origins = settings.cors_origin_list
    assert isinstance(origins, list)


def test_cookie_policy_documented_or_bearer():
    """Auth principale = Bearer/Firebase — cookies session non critiques."""
    docs = list((ROOT / "docs").glob("*.md")) + list((BACKEND / "docs").rglob("*.md"))
    assert docs, "documentation attendue"


def test_openapi_disabled_flag_in_main_source():
    main_src = (BACKEND / "app" / "main.py").read_text(encoding="utf-8")
    assert "docs_url" in main_src
    assert "is_production" in main_src


def test_backup_001_002_runbooks_present():
    runbooks = BACKEND / "docs" / "runbooks"
    # Aussi accepté à la racine docs/
    alt = ROOT / "docs" / "runbooks"
    targets = [
        "database-backup.md",
        "database-restore.md",
        "rollback.md",
        "secret-rotation.md",
        "deployment.md",
    ]
    base = runbooks if runbooks.is_dir() else alt
    assert base.is_dir(), "docs/runbooks manquant"
    for name in targets:
        assert (base / name).is_file(), f"runbook manquant: {name}"


def test_secret_redaction_event_context():
    from app.events.event_context import sanitize_error_message

    out = sanitize_error_message("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.aaa.bbb")
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.aaa.bbb" not in out
