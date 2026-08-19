"""Certification PostgreSQL Import Engine Sprint 6."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from scripts.migration.certify_document_extraction_sprint4_postgres import (  # noqa: E402
    SPRINT3,
    SPRINT4,
    apply_sql_whole,
    ensure_base,
    _engine,
    _q,
)

SPRINT5 = BACKEND / "sql" / "elfis_validation_mapping_sprint5_postgres.sql"
SPRINT6 = BACKEND / "sql" / "elfis_import_engine_sprint6_postgres.sql"
OUT = BACKEND / "docs" / "migration" / "sprint6-postgres-certification.json"


def verify(eng) -> dict:
    tables = [
        r[0]
        for r in _q(
            eng,
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' "
            "AND table_name LIKE 'elfis_import_%' ORDER BY 1",
        )
    ]
    needed = {
        "elfis_import_runs",
        "elfis_import_fingerprints",
        "elfis_import_artifacts",
        "elfis_import_reports",
        "elfis_import_audit_log",
    }
    missing = sorted(needed - set(tables))

    # contraintes / index
    idxs = [
        r[0]
        for r in _q(
            eng,
            "SELECT indexname FROM pg_indexes WHERE schemaname='public' "
            "AND tablename LIKE 'elfis_import_%' ORDER BY 1",
        )
    ]
    return {
        "ok": not missing and len(idxs) >= 5,
        "tables": tables,
        "missing": missing,
        "indexes": idxs,
    }


def main() -> int:
    eng = _engine()
    ensure_base(eng)
    if not _q(
        eng,
        "SELECT 1 FROM information_schema.tables WHERE table_name='elfis_validation_sessions'",
    ):
        apply_sql_whole(eng, SPRINT3)
        apply_sql_whole(eng, SPRINT4)
        apply_sql_whole(eng, SPRINT5)

    results = []
    apply_sql_whole(eng, SPRINT6)
    results.append({"scenario": "A_apply", **verify(eng)})
    apply_sql_whole(eng, SPRINT6)
    results.append({"scenario": "B_idempotent", **verify(eng)})

    # contrainte status lifecycle étendue
    ck = _q(
        eng,
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname='ck_elfis_intake_status'",
    )
    ck_ok = bool(ck) and "import_completed" in str(ck[0][0]) and "import_failed" in str(
        ck[0][0]
    )
    results.append({"scenario": "C_lifecycle_check", "ok": ck_ok, "def": str(ck)})

    all_ok = all(r["ok"] for r in results)
    report = {
        "certified": all_ok,
        "sprint": "6",
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
