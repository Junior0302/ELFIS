"""Certification PostgreSQL Document Analysis Sprint 3."""

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


def drop_analysis(eng: Engine) -> None:
    with eng.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS elfis_document_analysis_reports CASCADE"))


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


def verify(eng: Engine) -> dict[str, Any]:
    tables = [
        r[0]
        for r in _q(
            eng,
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='elfis_document_analysis_reports'",
        )
    ]
    cols = [
        r[0]
        for r in _q(
            eng,
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='elfis_document_analysis_reports' ORDER BY 1",
        )
    ]
    needed = [
        "id",
        "organization_id",
        "document_intake_item_id",
        "report",
        "need_ocr",
        "classification_label",
        "quality_score",
        "status",
    ]
    missing = [c for c in needed if c not in cols]
    return {
        "ok": bool(tables) and not missing,
        "missing_cols": missing,
        "columns": cols,
    }


def main() -> int:
    eng = _engine()
    ensure_base(eng)
    results = []

    drop_analysis(eng)
    apply_sql_whole(eng, SPRINT3)
    results.append({"scenario": "A_apply", **verify(eng)})

    apply_sql_whole(eng, SPRINT3)
    results.append({"scenario": "B_idempotent", **verify(eng)})

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
