"""Certification PostgreSQL Accounting Engine V2."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from scripts.migration.certify_document_extraction_sprint4_postgres import (  # noqa: E402
    apply_sql_whole,
    ensure_base,
    _engine,
    _q,
)

SQL = BACKEND / "sql" / "elfis_accounting_engine_v2_postgres.sql"
OUT = BACKEND / "docs" / "migration" / "accounting-engine-v2-postgres-certification.json"


def verify(eng) -> dict:
    tables = [
        r[0]
        for r in _q(
            eng,
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' "
            "AND (table_name LIKE 'elfis_accounting_engine_%' OR table_name IN "
            "('elfis_chart_of_accounts','elfis_accounting_learning_memory')) ORDER BY 1",
        )
    ]
    needed = {
        "elfis_chart_of_accounts",
        "elfis_accounting_engine_proposals",
        "elfis_accounting_learning_memory",
        "elfis_accounting_engine_audit",
    }
    missing = sorted(needed - set(tables))
    return {"ok": not missing, "tables": tables, "missing": missing}


def main() -> int:
    eng = _engine()
    ensure_base(eng)
    results = []
    apply_sql_whole(eng, SQL)
    results.append({"scenario": "A_apply", **verify(eng)})
    apply_sql_whole(eng, SQL)
    results.append({"scenario": "B_idempotent", **verify(eng)})
    uq = _q(
        eng,
        "SELECT conname FROM pg_constraint WHERE conname IN "
        "('uq_elfis_coa_org_plan_code','uq_elfis_aep_doc_ver','uq_elfis_alm_org_key')",
    )
    results.append(
        {"scenario": "C_constraints", "ok": len(uq) >= 3, "constraints": [r[0] for r in uq]}
    )
    all_ok = all(r["ok"] for r in results)
    report = {
        "certified": all_ok,
        "module": "accounting_engine_v2",
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
