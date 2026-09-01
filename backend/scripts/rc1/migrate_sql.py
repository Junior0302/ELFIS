"""Migrations SQL manuelles RC1 (Alembic absent V1).

Équivalent opérationnel de « alembic upgrade head » :
1. create_all ORM
2. scripts backend/sql/*.sql (IF NOT EXISTS)
3. index Phase F
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

BACKEND = Path(__file__).resolve().parents[2]
SQL_DIR = BACKEND / "sql"
PHASE_F_INDEXES = BACKEND / "docs" / "performance" / "postgres_indexes_phase_f.sql"

SQL_ORDER = [
    "vault_postgres.sql",
    "elfis_sales_crm_postgres.sql",
    "elfis_job_queue_postgres.sql",
    "elfis_event_bus_postgres.sql",
    "elfis_billing_postgres.sql",
    "elfis_document_intelligence_postgres.sql",
    "elfis_ai_engine_postgres.sql",
    "elfis_accounting_pipeline_postgres.sql",
    "elfis_notifications_postgres.sql",
    "elfis_search_engine_postgres.sql",
    "elfis_platform_admin_postgres.sql",
    "elfis_security_observability_postgres.sql",
    "elfis_iam_platform_postgres.sql",
    "elfis_audit_events_postgres.sql",
    "elfis_storage_documents_postgres.sql",
    "elfis_storage_documents_stage2_postgres.sql",
    "elfis_storage_documents_stage3_postgres.sql",
    "elfis_storage_documents_stage4_postgres.sql",
    "elfis_document_processing_stage1_postgres.sql",
    "elfis_document_classification_stage2_postgres.sql",
    "elfis_document_ocr_stage3_postgres.sql",
    "elfis_document_extraction_stage4_postgres.sql",
    "elfis_document_validation_stage5_postgres.sql",
    "elfis_product_document_integrations_stage5_postgres.sql",
    "elfis_product_document_integrations_stage6_postgres.sql",
    "elfis_migration_center_postgres.sql",
    "elfis_migration_center_stage2_postgres.sql",
    "elfis_document_intake_postgres.sql",
    "elfis_document_intake_stage2_5_postgres.sql",
    "elfis_document_analysis_sprint3_postgres.sql",
    "elfis_document_extraction_sprint4_postgres.sql",
    "elfis_validation_mapping_sprint5_postgres.sql",
    "elfis_import_engine_sprint6_postgres.sql",
    "elfis_smart_migration_sprint7_postgres.sql",
    "elfis_accounting_engine_v2_postgres.sql",
    "elfis_accounting_intelligence_v2_postgres.sql",
    "elfis_workspace_provisioning_v1_postgres.sql",
    "elfis_launch_dashboard_v1_postgres.sql",
    "elfis_banking_bank2_postgres.sql",
    "elfis_banking_bank3_postgres.sql",
    "elfis_banking_bank31_postgres.sql",
    "elfis_banking_bank4_postgres.sql",
    "elfis_banking_bank5_postgres.sql",
]

EXPECTED_TABLE_FAMILIES = [
    "users",
    "organizations",
    "organization_members",
    "subscriptions",
    "elfis_subscriptions",
    "elfis_entitlements",
    "elfis_quotas",
    "elfis_usage_counters",
    "vault_documents",
    "elfis_jobs",
    "elfis_events",
    "elfis_search_documents",
    "workspace_provisioning_runs",
    "elfis_operational_incidents",
    "elfis_security_events",
    "elfis_admin_audit_logs",
    "elfis_audit_events",
    "elfis_audit_events_archive",
    "elfis_storage_objects",
    "elfis_document_records",
    "elfis_document_links",
    "elfis_document_versions",
    "elfis_document_legal_holds",
    "elfis_document_tombstones",
    "elfis_storage_migrations",
    "elfis_document_processing_jobs",
    "elfis_document_processing_steps",
    "elfis_document_processing_attempts",
    "elfis_document_classifications",
    "elfis_document_ocr_results",
    "elfis_document_ocr_pages",
    "elfis_document_extraction_results",
    "elfis_document_extracted_fields",
    "elfis_document_extraction_reviews",
    "elfis_document_business_validations",
    "elfis_document_validation_issues",
    "elfis_product_processing_packages",
    "elfis_product_document_deliveries",
    "elfis_product_document_delivery_attempts",
    "elfis_migration_sessions",
    "elfis_migration_timeline_entries",
    "elfis_migration_activities",
    "elfis_migration_memory_entries",
    "elfis_document_intake_items",
    "elfis_document_upload_sessions",
    "elfis_document_lifecycle_entries",
    "elfis_document_doc_id_counters",
    "elfis_document_analysis_reports",
    "elfis_document_extractions",
    "elfis_document_extraction_attempts",
    "elfis_validation_sessions",
    "elfis_validation_fields",
    "elfis_validation_history",
    "elfis_validation_duplicates",
    "elfis_validation_matches",
    "elfis_import_runs",
    "elfis_import_fingerprints",
    "elfis_import_artifacts",
    "elfis_import_reports",
    "elfis_import_audit_log",
    "elfis_smart_migration_runs",
    "elfis_smart_migration_batches",
    "elfis_smart_migration_batch_items",
    "elfis_smart_migration_reports",
    "elfis_smart_migration_cleanup_log",
    "elfis_chart_of_accounts",
    "elfis_accounting_engine_proposals",
    "elfis_accounting_learning_memory",
    "elfis_accounting_engine_audit",
    "elfis_ai_context_profiles",
    "elfis_ai_learning_memory",
    "elfis_ai_recommendation_history",
    "elfis_ai_feedback",
    "elfis_ai_similarity_cache",
    "elfis_ai_audit",
]


def _split_sql(script: str) -> list[str]:
    """Split naïf sur ';' hors dollar-quoting basique pour triggers."""
    # Pour les fichiers avec $$ ... $$, exécuter le fichier entier si contient $$
    if "$$" in script:
        return [script]
    parts: list[str] = []
    buf: list[str] = []
    for line in script.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(buf).strip()
            if stmt:
                parts.append(stmt)
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def apply_sql_file(engine: Engine, path: Path) -> dict[str, Any]:
    text_sql = path.read_text(encoding="utf-8")
    # Retirer commentaires de début pour exécution
    cleaned = re.sub(r"(?m)^\s*--.*?$", "", text_sql)
    statements = _split_sql(cleaned)
    errors: list[str] = []
    executed = 0
    # Scripts avec blocs DO $$ : exécution driver (multi-statements)
    if "$$" in cleaned:
        raw = engine.raw_connection()
        try:
            with raw.cursor() as cur:
                cur.execute(cleaned)
            raw.commit()
            return {"file": path.name, "executed": 1, "errors": []}
        except Exception as exc:
            raw.rollback()
            msg = str(exc).lower()
            if "already exists" in msg or "duplicate" in msg:
                return {"file": path.name, "executed": 1, "errors": []}
            return {"file": path.name, "executed": 0, "errors": [f"{path.name}: {type(exc).__name__}"]}
        finally:
            raw.close()
    with engine.begin() as conn:
        for stmt in statements:
            s = stmt.strip().rstrip(";")
            if not s:
                continue
            try:
                conn.execute(text(stmt if stmt.strip().endswith(";") else stmt + ";"))
                executed += 1
            except Exception as exc:
                # IF NOT EXISTS / already exists → toléré
                msg = str(exc).lower()
                if "already exists" in msg or "duplicate" in msg:
                    executed += 1
                    continue
                errors.append(f"{path.name}: {type(exc).__name__}")
    return {"file": path.name, "executed": executed, "errors": errors}



def ensure_search_gin_index(engine: Engine) -> dict[str, Any]:
    """Garantit search_vector::tsvector + index GIN (idempotent)."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'elfis_search_documents'
                          AND column_name = 'search_vector'
                          AND udt_name IS DISTINCT FROM 'tsvector'
                    ) THEN
                        ALTER TABLE elfis_search_documents
                            ALTER COLUMN search_vector TYPE tsvector USING NULL;
                    END IF;
                END $$;
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_elfis_search_vector_gin
                    ON elfis_search_documents USING GIN (search_vector);
                """
            )
        )
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'ix_elfis_search_vector_gin'
                """
            )
        ).fetchone()
    return {
        "index": row[0] if row else None,
        "definition": row[1] if row else None,
        "ok": bool(row) and "gin" in (row[1] or "").lower(),
    }


def upgrade_head(database_url: str) -> dict[str, Any]:
    """Applique le schéma complet sur PostgreSQL (idempotent)."""
    # Import tardif pour éviter effets de bord
    import app.models  # noqa: F401 — BankAccount et tables cœur (create_all)
    import app.billing.billing_models  # noqa: F401
    import app.jobs.job_models  # noqa: F401
    import app.events.event_models  # noqa: F401
    import app.search.search_models  # noqa: F401
    import app.models_vault  # noqa: F401
    import app.sales_crm.models  # noqa: F401 — sales_attachments FK vault_documents.id
    import app.sales_proposals.models  # noqa: F401 — pdf_vault_document_id FK
    import app.accounting.accounting_models  # noqa: F401
    import app.document_intelligence.document_models  # noqa: F401
    import app.ai.ai_models  # noqa: F401
    import app.notifications.notification_models  # noqa: F401
    import app.iam.iam_models  # noqa: F401
    from app.database import Base

    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)

    file_results = []
    for name in SQL_ORDER:
        path = SQL_DIR / name
        if path.is_file():
            file_results.append(apply_sql_file(engine, path))
    if PHASE_F_INDEXES.is_file():
        file_results.append(apply_sql_file(engine, PHASE_F_INDEXES))

    gin = ensure_search_gin_index(engine)

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    missing = [t for t in EXPECTED_TABLE_FAMILIES if t not in tables]
    # Marqueur de version logique (pas alembic_version)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS elfis_schema_version (
                    id INTEGER PRIMARY KEY,
                    version TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO elfis_schema_version (id, version)
                VALUES (1, 'rc1-sql-head')
                ON CONFLICT (id) DO UPDATE SET version = EXCLUDED.version, applied_at = NOW()
                """
            )
        )

    engine.dispose()
    return {
        "strategy": "orm_create_all_plus_sql_scripts",
        "alembic": False,
        "version_marker": "elfis_schema_version=rc1-sql-head",
        "tables_count": len(tables),
        "missing_expected": missing,
        "files": file_results,
        "search_gin": gin,
        "ok": not missing and bool(gin.get("ok")),
    }


def verify_critical_indexes(database_url: str) -> dict[str, Any]:
    engine = create_engine(database_url, pool_pre_ping=True)
    gin_fix = ensure_search_gin_index(engine)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                ORDER BY indexname
                """
            )
        ).fetchall()
    engine.dispose()
    names = {r[0] for r in rows}
    defs = {r[0]: r[1] for r in rows}
    required = {
        "uq_document_email_org_idempotency": "Delivery idempotency",
        "uq_elfis_billing_provider_event": "Stripe provider_event_id",
        "uq_vault_org_checksum_active": "Vault tenant/hash",
        "ix_elfis_jobs_claim": "Jobs claim",
        "ix_elfis_events_claim": "Events claim",
        "ix_elfis_search_vector_gin": "Search GIN",
    }
    found: dict[str, bool] = {}
    for name, _label in required.items():
        ok = name in names
        if not ok:
            ok = any(name in n for n in names) or any(name.lower() in d.lower() for d in defs.values())
        found[name] = ok
    gin_present = any("gin" in (d or "").lower() for d in defs.values()) or gin_fix.get("ok", False)
    found["ix_elfis_search_vector_gin"] = bool(found.get("ix_elfis_search_vector_gin") or gin_fix.get("ok"))
    return {
        "indexes_checked": found,
        "gin_present": gin_present,
        "search_gin": gin_fix,
        "ok": all(found.values()) and gin_present,
        "index_count": len(names),
    }


def missing_sql_files() -> list[str]:
    return [name for name in SQL_ORDER if not (SQL_DIR / name).is_file()]


def main() -> int:
    """Entrée production : DATABASE_URL → upgrade_head. Jamais de reset."""
    import json
    import os
    import sys

    from scripts.rc1.safety import normalize_postgres_url

    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        print("DATABASE_URL manquant", file=sys.stderr)
        return 2
    if url.lower().startswith("sqlite"):
        print("SQLite interdit — PostgreSQL requis pour migrate_sql", file=sys.stderr)
        return 2
    missing = missing_sql_files()
    if missing:
        print("Fichiers SQL manquants: " + ", ".join(missing), file=sys.stderr)
        return 2
    result = upgrade_head(normalize_postgres_url(url))
    print(
        json.dumps(
            {
                "ok": result.get("ok"),
                "strategy": result.get("strategy"),
                "alembic": result.get("alembic"),
                "version_marker": result.get("version_marker"),
                "tables_count": result.get("tables_count"),
                "missing_expected": result.get("missing_expected"),
                "files": [
                    {"file": item.get("file"), "ok": not item.get("errors")}
                    for item in (result.get("files") or [])
                    if isinstance(item, dict)
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
