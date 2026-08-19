#!/usr/bin/env python
"""Applique les migrations SQL SalesPilot (DDL réel) + create_all ORM.

Usage (depuis backend/) :
  python -m scripts.apply_salespilot_migrations
  python -m scripts.apply_salespilot_migrations --report-only

Ne remplace pas Alembic. Les fichiers SQL CRM sont documentaires ;
le schéma CRM vient de SQLAlchemy create_all. Les modules S1.6–S1.9
ont du DDL IF NOT EXISTS / ALTER à appliquer sur Postgres persistant.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parents[1]
SQL_DIR = BACKEND / "sql"

# Ordre : fondation → propositions → bridge → intelligence → ops → collab
SALES_SQL_FILES: list[str] = [
    "elfis_sales_crm_postgres.sql",  # doc only — no-op DDL
    "elfis_sales_proposals_postgres.sql",
    "elfis_proposal_invoice_bridge_s161_postgres.sql",
    "elfis_sales_intelligence_s17_postgres.sql",
    "elfis_sales_operations_s18_postgres.sql",
    "elfis_sales_collaboration_s19_postgres.sql",
]

EXPECTED_TABLES: list[tuple[str, str]] = [
    ("CRM Foundation", "sales_pipelines"),
    ("CRM Foundation", "sales_pipeline_stages"),
    ("CRM Foundation", "sales_companies"),
    ("CRM Foundation", "sales_people"),
    ("CRM Foundation", "sales_leads"),
    ("CRM Foundation", "sales_opportunities"),
    ("CRM Foundation", "sales_opportunity_products"),
    ("CRM Foundation", "sales_opportunity_participants"),
    ("CRM Foundation", "sales_activities"),
    ("CRM Foundation", "sales_tasks"),
    ("CRM Foundation", "sales_notes"),
    ("Proposals", "sales_commercial_proposals"),
    ("Proposals", "sales_commercial_proposal_versions"),
    ("Proposals", "sales_commercial_proposal_lines"),
    ("Proposals", "sales_commercial_proposal_events"),
    ("Intelligence", "sales_insight_items"),
    ("Operations", "sales_saved_views"),
    ("Collaboration", "sales_teams"),
    ("Collaboration", "sales_team_members"),
    ("Collaboration", "sales_comments"),
    ("Collaboration", "sales_followers"),
    ("Collaboration", "sales_review_requests"),
]


def _split_sql(script: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    for line in script.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
    leftover = "\n".join(buf).strip()
    if leftover:
        statements.append(leftover)
    return statements


def apply_sql_file(engine: Any, path: Path) -> dict[str, Any]:
    from sqlalchemy import text

    if not path.is_file():
        return {"file": path.name, "status": "missing", "statements": 0, "errors": ["file not found"]}
    raw = path.read_text(encoding="utf-8")
    # Skip pure-comment documentation files
    meaningful = [
        ln for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith("--")
    ]
    if not meaningful:
        return {"file": path.name, "status": "doc_only", "statements": 0, "errors": []}

    statements = _split_sql(raw)
    errors: list[str] = []
    applied = 0
    with engine.begin() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
                applied += 1
            except Exception as exc:  # noqa: BLE001
                # Idempotent: ignore "already exists" style errors on SQLite/Postgres
                msg = str(exc).lower()
                if any(
                    x in msg
                    for x in (
                        "already exists",
                        "duplicate column",
                        "duplicate",
                        "exists",
                    )
                ):
                    applied += 1
                    continue
                errors.append(f"{stmt[:80]}… → {exc}")
    status = "ok" if not errors else ("partial" if applied else "failed")
    return {"file": path.name, "status": status, "statements": applied, "errors": errors}


def report_tables(engine: Any) -> list[dict[str, Any]]:
    from sqlalchemy import inspect

    insp = inspect(engine)
    existing = set(insp.get_table_names())
    rows: list[dict[str, Any]] = []
    for family, table in EXPECTED_TABLES:
        rows.append(
            {
                "migration": family,
                "table": table,
                "applied": table in existing,
                "missing": table not in existing,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrations SalesPilot locales")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="N'applique rien ; affiche l'état des tables",
    )
    parser.add_argument(
        "--skip-create-all",
        action="store_true",
        help="Ne pas appeler Base.metadata.create_all",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(BACKEND))
    from app.config import settings
    from app.database import Base, engine

    env = (settings.app_env or "").strip().lower()
    if env in {"production", "prod"}:
        print("REFUS: migrations SalesPilot interdites en production via ce script")
        return 2

    # Import models so metadata is complete
    import app.sales_crm.models  # noqa: F401
    import app.sales_proposals.models  # noqa: F401
    import app.sales_intelligence.models  # noqa: F401
    import app.sales_operations.models  # noqa: F401
    import app.sales_collaboration.models  # noqa: F401

    results: dict[str, Any] = {
        "database_url": settings.database_url.split("@")[-1] if "@" in settings.database_url else settings.database_url,
        "environment": settings.app_env,
        "create_all": None,
        "sql_files": [],
        "tables": [],
    }

    if not args.report_only and not args.skip_create_all:
        Base.metadata.create_all(bind=engine)
        results["create_all"] = "ok"

    if not args.report_only:
        for name in SALES_SQL_FILES:
            results["sql_files"].append(apply_sql_file(engine, SQL_DIR / name))

    results["tables"] = report_tables(engine)

    missing = [t for t in results["tables"] if t["missing"]]
    print("=== SalesPilot migrations ===")
    print(f"env={results['environment']} db={results['database_url']}")
    if results["create_all"]:
        print(f"create_all={results['create_all']}")
    for f in results["sql_files"]:
        err = f" errors={len(f['errors'])}" if f["errors"] else ""
        print(f"  SQL {f['file']}: {f['status']} stmts={f['statements']}{err}")
        for e in f["errors"][:5]:
            print(f"    ! {e}")
    print("--- Tables ---")
    for t in results["tables"]:
        mark = "OK" if t["applied"] else "MISSING"
        print(f"  [{mark}] {t['migration']}: {t['table']}")

    if missing:
        print(f"FAIL: {len(missing)} table(s) manquante(s)")
        return 1
    print("OK: schéma SalesPilot présent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
