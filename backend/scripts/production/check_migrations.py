#!/usr/bin/env python
"""Vérifie la présence des scripts SQL de schéma (Alembic absent en V1)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
SQL = BACKEND / "sql"

REQUIRED = [
    "vault_postgres.sql",
    "elfis_job_queue_postgres.sql",
    "elfis_event_bus_postgres.sql",
    "elfis_billing_postgres.sql",
    "elfis_search_engine_postgres.sql",
    "elfis_accounting_pipeline_postgres.sql",
    "elfis_document_intelligence_postgres.sql",
    "elfis_notifications_postgres.sql",
    "elfis_platform_admin_postgres.sql",
    "elfis_security_observability_postgres.sql",
    "elfis_ai_engine_postgres.sql",
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
    "elfis_banking_bank2_postgres.sql",
    "elfis_banking_bank3_postgres.sql",
]


def main() -> int:
    missing = [n for n in REQUIRED if not (SQL / n).is_file()]
    phase_f = BACKEND / "docs" / "performance" / "postgres_indexes_phase_f.sql"
    payload = {
        "alembic": False,
        "strategy": "manual_sql_scripts",
        "sql_dir": str(SQL),
        "required_present": len(REQUIRED) - len(missing),
        "required_total": len(REQUIRED),
        "missing": missing,
        "phase_f_indexes": phase_f.is_file(),
        "postgres_upgrade": "NOT_EXECUTED_in_this_script",
        "note": "Appliquer sql/*.sql puis docs/performance/postgres_indexes_phase_f.sql sur Postgres staging.",
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
