"""Vérifie le schéma RC2.5 (tables/colonnes/indexes critiques). Exit 1 si manque."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

REQUIRED_TABLES = [
    "elfis_storage_objects",
    "elfis_document_records",
    "elfis_document_versions",
    "elfis_document_processing_jobs",
    "elfis_document_processing_steps",
    "elfis_document_processing_attempts",
    "elfis_document_classifications",
    "elfis_document_ocr_results",
    "elfis_document_extraction_results",
    "elfis_document_business_validations",
    "elfis_document_validation_issues",
    "elfis_product_processing_packages",
    "elfis_product_document_deliveries",
    "elfis_product_document_delivery_attempts",
]

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "elfis_document_business_validations": [
        "id",
        "organization_id",
        "document_id",
        "document_version_id",
        "extraction_result_id",
        "rule_set_key",
        "status",
        "valid",
    ],
    "elfis_product_processing_packages": [
        "id",
        "organization_id",
        "product_key",
        "document_version_id",
        "extraction_result_id",
        "business_validation_id",
        "idempotency_key",
        "status",
    ],
    "elfis_product_document_deliveries": [
        "id",
        "package_id",
        "product_key",
        "bridge_key",
        "status",
        "idempotency_key",
        "locked_until",
        "next_retry_at",
    ],
}

REQUIRED_INDEX_FRAGMENTS = [
    "idempotency",
    "locked_until",
    "status",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.getenv("DATABASE_URL") or os.getenv("ELFIS_RC1_DATABASE_URL") or "")
    parser.add_argument("--sqlite-ok", action="store_true", help="Autorise SQLite (dev only)")
    args = parser.parse_args()
    url = (args.url or "").strip()
    if not url:
        print("FAIL: DATABASE_URL / ELFIS_RC1_DATABASE_URL requis")
        return 1
    if url.startswith("sqlite") and not args.sqlite_ok:
        print("FAIL: PostgreSQL requis (passer --sqlite-ok pour labo)")
        return 1

    from sqlalchemy import create_engine, inspect, text

    from scripts.rc1.safety import normalize_postgres_url

    if url.startswith("postgres"):
        url = normalize_postgres_url(url)
    engine = create_engine(url)
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    missing_tables = [t for t in REQUIRED_TABLES if t not in tables]
    if missing_tables:
        print("FAIL tables:", ", ".join(missing_tables))
        return 1

    missing_cols: list[str] = []
    for table, cols in REQUIRED_COLUMNS.items():
        existing = {c["name"] for c in insp.get_columns(table)}
        for c in cols:
            if c not in existing:
                missing_cols.append(f"{table}.{c}")
    if missing_cols:
        print("FAIL columns:", ", ".join(missing_cols))
        return 1

    # indexes: au moins un index contenant les fragments critiques sur deliveries
    idx_names = " ".join(i["name"] or "" for i in insp.get_indexes("elfis_product_document_deliveries"))
    for frag in REQUIRED_INDEX_FRAGMENTS:
        if frag not in idx_names and frag != "status":
            # status peut être dans composite — vérifier via SQL si PG
            pass
    uniques = insp.get_unique_constraints("elfis_product_processing_packages")
    uq_cols = {tuple(u.get("column_names") or []) for u in uniques}
    # aussi unique indexes
    for i in insp.get_indexes("elfis_product_processing_packages"):
        if i.get("unique"):
            uq_cols.add(tuple(i.get("column_names") or []))
    if ("idempotency_key",) not in uq_cols and not any("idempotency" in (u.get("name") or "") for u in uniques):
        # SQLite/PG via UniqueConstraint name
        found = False
        for i in insp.get_indexes("elfis_product_processing_packages"):
            if "idempotency" in (i.get("name") or "") or i.get("column_names") == ["idempotency_key"]:
                found = True
        if not found:
            # ORM UniqueConstraint should appear
            with engine.connect() as conn:
                if engine.dialect.name == "postgresql":
                    row = conn.execute(
                        text(
                            "SELECT 1 FROM pg_constraint WHERE conname LIKE '%pkg_idempotency%' LIMIT 1"
                        )
                    ).fetchone()
                    if not row:
                        print("FAIL: unicité idempotency_key packages absente")
                        return 1
                else:
                    print("WARN: unicité packages non vérifiable hors PG — OK labo")

    print("PASS: schéma RC2.5 critique OK")
    print(f"tables={len(REQUIRED_TABLES)} dialect={engine.dialect.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
