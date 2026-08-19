"""Certification PostgreSQL Document Intake Stage 2.5.

Scénarios :
  A. base vide intake → apply Sprint2 + Stage2.5
  B. base avec Sprint2 uniquement → apply Stage2.5
  C. base Migration Center Stage2 + Sprint2 → apply Stage2.5
  D. rejeu Stage2.5 (idempotence)

Usage :
  set ELFIS_POSTGRES_TESTS_ENABLED=true
  python scripts/migration/certify_document_intake_stage2_5_postgres.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from scripts.rc1.migrate_sql import apply_sql_file  # noqa: E402
from tests.concurrency.postgres_helpers import ensure_postgres_test_env, postgres_url  # noqa: E402

SQL_DIR = BACKEND / "sql"
SPRINT2 = SQL_DIR / "elfis_document_intake_postgres.sql"
STAGE25 = SQL_DIR / "elfis_document_intake_stage2_5_postgres.sql"
MIG1 = SQL_DIR / "elfis_migration_center_postgres.sql"
MIG2 = SQL_DIR / "elfis_migration_center_stage2_postgres.sql"

EXPECTED_TABLES = [
    "elfis_document_intake_items",
    "elfis_document_upload_sessions",
    "elfis_document_lifecycle_entries",
    "elfis_document_doc_id_counters",
]

EXPECTED_COLS = [
    "universal_document_id",
    "upload_session_id",
    "lifecycle_status",
    "storage_provider",
    "fingerprint",
    "duplicate_type",
    "idempotency_key",
    "version",
]


def _engine() -> Engine:
    os.environ["ELFIS_POSTGRES_TESTS_ENABLED"] = "true"
    ensure_postgres_test_env()
    os.environ["ELFIS_ENVIRONMENT"] = "staging"
    os.environ["APP_ENV"] = "staging"
    os.environ.setdefault("ELFIS_RC1_ALLOW_MANAGED_HOST", "true")
    from scripts.rc1.safety import assert_safe_postgres_url, assert_safe_rc1_environment

    url = postgres_url()
    assert_safe_rc1_environment()
    assert_safe_postgres_url(url)
    return create_engine(url, pool_pre_ping=True, connect_args={"prepare_threshold": None})


def _q(eng: Engine, sql: str, **params) -> list:
    with eng.connect() as c:
        return list(c.execute(text(sql), params).fetchall())


def intake_tables(eng: Engine) -> list[str]:
    rows = _q(
        eng,
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name LIKE 'elfis_document_%' "
        "ORDER BY 1",
    )
    return [r[0] for r in rows]


def item_columns(eng: Engine) -> list[str]:
    rows = _q(
        eng,
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='elfis_document_intake_items' "
        "ORDER BY ordinal_position",
    )
    return [r[0] for r in rows]


def drop_intake(eng: Engine) -> None:
    with eng.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS elfis_document_lifecycle_entries CASCADE"))
        c.execute(text("DROP TABLE IF EXISTS elfis_document_intake_items CASCADE"))
        c.execute(text("DROP TABLE IF EXISTS elfis_document_upload_sessions CASCADE"))
        c.execute(text("DROP TABLE IF EXISTS elfis_document_doc_id_counters CASCADE"))


def apply_sql_whole(eng: Engine, path: Path) -> None:
    """Exécute un script SQL complet (supporte blocs DO $$ … $$)."""
    sql = path.read_text(encoding="utf-8")
    # psycopg accepte multi-statements via le driver sous-jacent
    raw = eng.raw_connection()
    try:
        with raw.cursor() as cur:
            cur.execute(sql)
        raw.commit()
    finally:
        raw.close()


def ensure_migration_base(eng: Engine) -> None:
    tables = _q(
        eng,
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='elfis_migration_sessions'",
    )
    if not tables:
        apply_sql_file(eng, MIG1)
        apply_sql_file(eng, MIG2)


def verify_schema(eng: Engine) -> dict[str, Any]:
    tables = intake_tables(eng)
    cols = item_columns(eng)
    missing_tables = [t for t in EXPECTED_TABLES if t not in tables]
    missing_cols = [c for c in EXPECTED_COLS if c not in cols]
    return {
        "tables": tables,
        "columns": cols,
        "missing_tables": missing_tables,
        "missing_cols": missing_cols,
        "ok": not missing_tables and not missing_cols,
    }


def seed_sample_item(eng: Engine) -> None:
    """Ligne Sprint 2 minimale pour tester backfill."""
    with eng.begin() as c:
        orgs = c.execute(text("SELECT id FROM organizations LIMIT 1")).fetchone()
        if not orgs:
            c.execute(
                text(
                    "INSERT INTO organizations (name, created_at) VALUES ('Intake Cert Org', NOW()) "
                    "RETURNING id"
                )
            )
            # fallback if created_at absent
        org = c.execute(text("SELECT id FROM organizations LIMIT 1")).fetchone()
        if not org:
            return
        exists = c.execute(
            text("SELECT 1 FROM elfis_document_intake_items WHERE id='cert-item-1'")
        ).fetchone()
        if exists:
            return
        c.execute(
            text(
                """
                INSERT INTO elfis_document_intake_items (
                    id, intake_token, organization_id, original_filename, normalized_filename,
                    extension, format_id, mime, size_bytes, checksum_sha256, status, origin,
                    storage_key, is_duplicate, extract_later, preview_allowed, analysis_allowed,
                    metadata, uploaded_at, created_at, updated_at
                ) VALUES (
                    'cert-item-1', 'din_cert1', :org, 'old.pdf', 'old.pdf',
                    '.pdf', 'pdf', 'application/pdf', 12, 'abc123', 'ready_for_analysis', 'api',
                    'temp/old.pdf', FALSE, FALSE, TRUE, FALSE,
                    '{}'::jsonb, NOW(), NOW(), NOW()
                )
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"org": org[0]},
        )


def run_scenario(name: str, eng: Engine, setup) -> dict[str, Any]:
    setup(eng)
    result = verify_schema(eng)
    result["scenario"] = name
    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    return result


def main() -> int:
    eng = _engine()
    ensure_migration_base(eng)
    results: list[dict[str, Any]] = []

    # A: empty intake
    def setup_a(e: Engine):
        drop_intake(e)
        apply_sql_file(e, SPRINT2)
        apply_sql_whole(e, STAGE25)

    results.append(run_scenario("A_empty", eng, setup_a))

    # B: sprint2 then stage2.5
    def setup_b(e: Engine):
        drop_intake(e)
        apply_sql_file(e, SPRINT2)
        seed_sample_item(e)
        apply_sql_whole(e, STAGE25)

    results.append(run_scenario("B_sprint2_then_25", eng, setup_b))

    # C: migration already present (already ensured) + sprint2 + 2.5
    def setup_c(e: Engine):
        drop_intake(e)
        apply_sql_file(e, SPRINT2)
        apply_sql_whole(e, STAGE25)

    results.append(run_scenario("C_with_migration_center", eng, setup_c))

    # D: replay
    def setup_d(e: Engine):
        apply_sql_whole(e, STAGE25)
        apply_sql_whole(e, STAGE25)

    results.append(run_scenario("D_idempotent_replay", eng, setup_d))

    # Backfill check
    backfill_ok = True
    rows = _q(
        eng,
        "SELECT universal_document_id, lifecycle_status, storage_provider, fingerprint "
        "FROM elfis_document_intake_items WHERE id='cert-item-1'",
    )
    if rows:
        uid, life, prov, fp = rows[0]
        backfill_ok = bool(uid and str(uid).startswith("DOC-") and life and prov == "local" and fp)

    all_ok = all(r["ok"] for r in results) and backfill_ok
    report = {
        "certified": all_ok,
        "backfill_ok": backfill_ok,
        "scenarios": results,
    }
    print(json.dumps(report, indent=2, default=str))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
