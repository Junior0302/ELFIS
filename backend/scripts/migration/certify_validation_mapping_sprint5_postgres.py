"""Certification PostgreSQL Validation Mapping Sprint 5."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from scripts.migration.certify_document_extraction_sprint4_postgres import (  # noqa: E402
    SPRINT4,
    apply_sql_whole,
    ensure_base,
    _engine,
    _q,
)
from scripts.migration.certify_document_extraction_sprint4_postgres import (  # noqa: E402
    SPRINT3,
)

SPRINT5 = BACKEND / "sql" / "elfis_validation_mapping_sprint5_postgres.sql"
OUT = BACKEND / "docs" / "migration" / "sprint5-postgres-certification.json"


def verify(eng) -> dict:
    tables = [
        r[0]
        for r in _q(
            eng,
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' "
            "AND table_name LIKE 'elfis_validation_%' ORDER BY 1",
        )
    ]
    needed = {
        "elfis_validation_sessions",
        "elfis_validation_fields",
        "elfis_validation_history",
        "elfis_validation_duplicates",
        "elfis_validation_matches",
    }
    missing = sorted(needed - set(tables))
    return {"ok": not missing, "tables": tables, "missing": missing}


def main() -> int:
    eng = _engine()
    ensure_base(eng)
    if not _q(
        eng,
        "SELECT 1 FROM information_schema.tables WHERE table_name='elfis_document_extractions'",
    ):
        apply_sql_whole(eng, SPRINT3)
        apply_sql_whole(eng, SPRINT4)

    results = []
    apply_sql_whole(eng, SPRINT5)
    results.append({"scenario": "A_apply", **verify(eng)})
    apply_sql_whole(eng, SPRINT5)
    results.append({"scenario": "B_idempotent", **verify(eng)})

    all_ok = all(r["ok"] for r in results)
    report = {
        "certified": all_ok,
        "sprint": "5",
        "scenarios": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": os.getenv("ELFIS_ENVIRONMENT"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
