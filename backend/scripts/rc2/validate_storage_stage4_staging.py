#!/usr/bin/env python
"""Validation staging RC2.4 étape 4 — Supabase Storage Provider."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-sql", action="store_true")
    parser.add_argument("--db-only", action="store_true")
    parser.add_argument("--provider-only", action="store_true")
    parser.add_argument("--skip-migration", action="store_true")
    parser.add_argument("--keep-probes", action="store_true")
    args = parser.parse_args()

    from sqlalchemy import create_engine, inspect

    from app.config import settings

    engine = create_engine(settings.database_url)
    report: dict = {
        "database_url_scheme": settings.database_url.split(":", 1)[0],
        "storage_provider_configured": (settings.storage_provider or "").strip().lower(),
        "supabase_url_configured": bool(
            (getattr(settings, "supabase_storage_url", None) or settings.supabase_url or "").strip()
        ),
        "supabase_bucket": getattr(settings, "supabase_storage_bucket", None),
        "checks": [],
        "note": "Aucun secret affiché. Probes uniquement.",
    }

    if args.apply_sql:
        from scripts.rc1.migrate_sql import apply_sql_file

        for name in (
            "elfis_storage_documents_postgres.sql",
            "elfis_storage_documents_stage2_postgres.sql",
            "elfis_storage_documents_stage3_postgres.sql",
            "elfis_storage_documents_stage4_postgres.sql",
        ):
            apply_sql_file(engine, BACKEND / "sql" / name)
            report["checks"].append({"apply_sql": name, "ok": True})

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    required = {"elfis_storage_objects", "elfis_storage_migrations"}
    missing = sorted(required - tables)
    report["checks"].append({"tables_missing": missing})
    if missing and args.db_only:
        report["status"] = "FAIL"
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1
    if args.db_only:
        report["status"] = "PASS_DB_ONLY"
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    from app.storage.storage_registry import build_storage_provider, clear_storage_provider_cache

    clear_storage_provider_cache()
    provider = build_storage_provider()
    report["checks"].append({"active_provider": provider.name})

    if args.provider_only or provider.name == "supabase":
        health = provider.health_check()
        report["checks"].append(
            {
                "health_status": health.get("status"),
                "probe_ok": health.get("probe_ok"),
                "latency_ms": health.get("latency_ms"),
            }
        )
        # Ne jamais logger secret
        if provider.name != "supabase":
            report["status"] = "PASS_PROVIDER_LOCAL"
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0
        if not health.get("probe_ok"):
            report["status"] = "FAIL"
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 1

    if provider.name != "supabase":
        report["status"] = "PASS_SKIPPED_NO_SUPABASE"
        report["note"] += " STORAGE_PROVIDER!=supabase — skip probes distants."
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    # Probe upload/download
    key = f"staging/{__import__('uuid').uuid4().hex}.probe"
    provider.put_object(namespace="health-probes", object_key=key, data=b"stage4-probe", overwrite=True)
    with provider.open_stream(namespace="health-probes", object_key=key) as fh:
        data = fh.read()
    assert data == b"stage4-probe"
    if not args.keep_probes:
        provider.delete_object(namespace="health-probes", object_key=key)
    report["checks"].append({"remote_upload_download": True})
    report["status"] = "PASS"
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
