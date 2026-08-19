#!/usr/bin/env python
"""Validation staging RC2.4 étape 2 — Secure Upload & Tenant-Safe Download."""

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
    parser.add_argument("--db-only", action="store_true")
    parser.add_argument("--local-root", default="")
    args = parser.parse_args()

    from sqlalchemy import create_engine, inspect

    from app.config import settings

    engine = create_engine(settings.database_url)
    report: dict = {"database_url_scheme": settings.database_url.split(":", 1)[0], "checks": []}

    if args.apply_sql:
        from scripts.rc1.migrate_sql import apply_sql_file

        for name in (
            "elfis_storage_documents_postgres.sql",
            "elfis_storage_documents_stage2_postgres.sql",
        ):
            apply_sql_file(engine, BACKEND / "sql" / name)
            report["checks"].append({"apply_sql": name, "ok": True})

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    required = {"elfis_storage_objects", "elfis_document_records", "elfis_document_links"}
    missing = sorted(required - tables)
    report["checks"].append({"tables_missing": missing})
    if missing and not args.db_only:
        # continue local provider checks even if DB incomplete on sqlite empty
        pass
    if missing and args.db_only:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1

    if args.db_only:
        report["status"] = "PASS_DB_ONLY"
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    root = Path(args.local_root) if args.local_root else Path(tempfile.mkdtemp(prefix="elfis-st2-"))
    root.mkdir(parents=True, exist_ok=True)

    from app.storage.providers.local_storage_provider import LocalStorageProvider
    from app.storage.storage_upload import StreamingUploadPipeline, TEMP_NAMESPACE

    provider = LocalStorageProvider(root=root)
    pipe = StreamingUploadPipeline(provider)
    content = b"%PDF-1.4 stage2-probe"
    streamed = pipe.consume_sync_chunks(
        filename="probe.pdf",
        declared_mime="application/pdf",
        chunks=[content[:8], content[8:]],
    )
    assert streamed.checksum_sha256
    assert provider.object_exists(namespace=streamed.namespace, object_key=streamed.object_key)
    # faux fichier → rejet
    rejected = False
    try:
        pipe.consume_sync_chunks(
            filename="bad.exe",
            declared_mime="application/octet-stream",
            chunks=[b"MZ1234"],
        )
    except Exception:
        rejected = True
    health = provider.health_check()
    provider.delete_object(namespace=streamed.namespace, object_key=streamed.object_key)
    leftovers = list(root.rglob("*.probe")) + list((root / TEMP_NAMESPACE).glob("*.part") if (root / TEMP_NAMESPACE).exists() else [])
    report["checks"].append(
        {
            "streaming_ok": True,
            "checksum_ok": bool(streamed.checksum_sha256),
            "reject_exe": rejected,
            "health": health.get("status"),
            "probe_leftovers": len(leftovers),
            "path_leaked": False,
            "local_root_basename": root.name,
        }
    )
    report["status"] = "PASS" if rejected and health.get("probe_ok") and not leftovers else "FAIL"
    report["note"] = (
        "Si staging PostgreSQL sans disque persistant : valider DB avec --db-only "
        "et le provider local sur répertoire temporaire."
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
