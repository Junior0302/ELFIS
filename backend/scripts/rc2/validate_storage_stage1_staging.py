#!/usr/bin/env python
"""Validation staging RC2.4 étape 1 — Storage / Document Registry.

Usage:
  python scripts/rc2/validate_storage_stage1_staging.py --apply-sql
  python scripts/rc2/validate_storage_stage1_staging.py --db-only
  python scripts/rc2/validate_storage_stage1_staging.py --local-root /tmp/elfis-storage-probe
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-sql", action="store_true")
    parser.add_argument("--db-only", action="store_true", help="Valide tables/index uniquement")
    parser.add_argument("--local-root", default="", help="Racine temporaire provider local")
    args = parser.parse_args()

    from sqlalchemy import create_engine, inspect, text

    from app.config import settings

    engine = create_engine(settings.database_url)
    report: dict = {"database_url_scheme": settings.database_url.split(":", 1)[0], "checks": []}

    if args.apply_sql:
        from scripts.rc1.migrate_sql import apply_sql_file

        sql_path = BACKEND / "sql" / "elfis_storage_documents_postgres.sql"
        apply_sql_file(engine, sql_path)
        report["checks"].append({"apply_sql": str(sql_path), "ok": True})

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    required = {
        "elfis_storage_objects",
        "elfis_document_records",
        "elfis_document_links",
    }
    missing = sorted(required - tables)
    report["checks"].append({"tables": sorted(required & tables), "missing": missing})
    if missing:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1

    for t in required:
        idxs = {ix["name"] for ix in insp.get_indexes(t)}
        report["checks"].append({"table": t, "index_count": len(idxs)})

    if args.db_only:
        report["status"] = "PASS_DB_ONLY"
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    # Probe local provider (répertoire temporaire si non fourni)
    root = Path(args.local_root) if args.local_root else Path(tempfile.mkdtemp(prefix="elfis-storage-"))
    root.mkdir(parents=True, exist_ok=True)

    from app.storage.providers.local_storage_provider import LocalStorageProvider, new_object_key
    from app.storage.storage_security import validate_upload

    provider = LocalStorageProvider(root=root)
    content = b"%PDF-1.4 elfis-storage-probe"
    validation = validate_upload(
        filename="probe.pdf",
        content=content,
        declared_mime="application/pdf",
    )
    key = new_object_key(extension=".pdf")
    provider.put_object(namespace="_staging", object_key=key, data=content)
    got = provider.get_object(namespace="_staging", object_key=key)
    assert got == content
    assert validation.checksum_sha256
    health = provider.health_check()
    provider.delete_object(namespace="_staging", object_key=key)
    leftovers = list(root.rglob("*.probe"))
    report["checks"].append(
        {
            "local_root_basename": root.name,
            "checksum": validation.checksum_sha256[:12] + "…",
            "health_status": health.get("status"),
            "probe_leftovers": len(leftovers),
            "path_leaked": False,
        }
    )
    report["status"] = "PASS" if health.get("probe_ok") and not leftovers else "FAIL"
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
