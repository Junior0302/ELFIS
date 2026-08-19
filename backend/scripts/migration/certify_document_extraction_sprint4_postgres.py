"""Certification PostgreSQL Document Extraction Sprint 4."""

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
SPRINT3 = SQL_DIR / "elfis_document_analysis_sprint3_postgres.sql"
SPRINT4 = SQL_DIR / "elfis_document_extraction_sprint4_postgres.sql"
MIG1 = SQL_DIR / "elfis_migration_center_postgres.sql"
MIG2 = SQL_DIR / "elfis_migration_center_stage2_postgres.sql"


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


def apply_sql_whole(eng: Engine, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    raw = eng.raw_connection()
    try:
        with raw.cursor() as cur:
            cur.execute(sql)
        raw.commit()
    finally:
        raw.close()


def drop_extraction(eng: Engine) -> None:
    with eng.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS elfis_document_extraction_attempts CASCADE"))
        c.execute(text("DROP TABLE IF EXISTS elfis_document_extractions CASCADE"))


def ensure_base(eng: Engine) -> None:
    if not _q(
        eng,
        "SELECT 1 FROM information_schema.tables WHERE table_name='elfis_migration_sessions'",
    ):
        apply_sql_file(eng, MIG1)
        apply_sql_file(eng, MIG2)
    if not _q(
        eng,
        "SELECT 1 FROM information_schema.tables WHERE table_name='elfis_document_intake_items'",
    ):
        apply_sql_file(eng, SPRINT2)
        apply_sql_whole(eng, STAGE25)
    if not _q(
        eng,
        "SELECT 1 FROM information_schema.tables WHERE table_name='elfis_document_analysis_reports'",
    ):
        apply_sql_whole(eng, SPRINT3)


def verify(eng: Engine) -> dict[str, Any]:
    tables = [
        r[0]
        for r in _q(
            eng,
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name IN "
            "('elfis_document_extractions','elfis_document_extraction_attempts') "
            "ORDER BY 1",
        )
    ]
    cols = [
        r[0]
        for r in _q(
            eng,
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='elfis_document_extractions' ORDER BY 1",
        )
    ]
    needed = [
        "id",
        "organization_id",
        "document_intake_item_id",
        "schema_name",
        "input_fingerprint",
        "structured_data",
        "field_provenance",
        "overall_confidence",
        "requires_human_review",
        "status_scope",
        "version",
    ]
    missing = [c for c in needed if c not in cols]
    uniq = _q(
        eng,
        "SELECT 1 FROM pg_constraint WHERE conname='uq_elfis_extr_active_fingerprint'",
    )
    return {
        "ok": len(tables) == 2 and not missing and bool(uniq),
        "tables": tables,
        "missing_cols": missing,
        "unique_ok": bool(uniq),
        "columns": cols,
    }


def main() -> int:
    eng = _engine()
    ensure_base(eng)
    results = []

    drop_extraction(eng)
    apply_sql_whole(eng, SPRINT4)
    results.append({"scenario": "A_empty_apply", **verify(eng)})

    apply_sql_whole(eng, SPRINT4)
    results.append({"scenario": "B_idempotent", **verify(eng)})

    # after analysis present
    apply_sql_whole(eng, SPRINT3)
    apply_sql_whole(eng, SPRINT4)
    results.append({"scenario": "C_after_sprint3", **verify(eng)})

    all_ok = all(r["ok"] for r in results)
    report = {
        "certified": all_ok,
        "scenarios": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(report, indent=2, default=str))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
