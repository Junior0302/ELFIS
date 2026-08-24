"""Backfill versions documentaires (RC2.4 étape 3) — preview par défaut.

Usage:
  python -m scripts.storage.backfill_document_versions --preview
  python -m scripts.storage.backfill_document_versions --execute --confirm --batch-size 500

Aucune copie physique. Idempotent. Hors ComptaPilot.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))


def _require_env() -> str:
    env = (os.environ.get("ELFIS_ENVIRONMENT") or os.environ.get("APP_ENV") or "").strip().lower()
    if not env:
        print("FATAL: ELFIS_ENVIRONMENT / APP_ENV non défini")
        raise SystemExit(2)
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill ElfisDocumentVersion v1")
    parser.add_argument("--preview", action="store_true", help="Aperçu (défaut)")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--database-url", default="")
    args = parser.parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    env = _require_env()
    print(f"ELFIS_ENVIRONMENT={env}")
    print(f"APP_ENV={os.environ.get('APP_ENV')}")

    execute = bool(args.execute)
    if execute and not args.confirm:
        print("FATAL: --confirm requis avec --execute")
        return 2

    from app.database import SessionLocal
    from app.storage.document_version_service import DocumentVersionService
    from app.storage.storage_models import ElfisDocumentRecord, ElfisStorageObject
    from app.storage.storage_repository import DocumentVersionRepository, StorageObjectRepository

    db = SessionLocal()
    batch = max(1, min(int(args.batch_size or 500), 2000))
    report = {
        "preview": not execute,
        "environment": env,
        "scanned": 0,
        "created": 0,
        "skipped_already": 0,
        "skipped_no_object": 0,
        "mismatch_current": 0,
        "errors": 0,
        "sample": [],
    }
    try:
        q = (
            db.query(ElfisDocumentRecord)
            .filter(ElfisDocumentRecord.current_storage_object_id.isnot(None))
            .order_by(ElfisDocumentRecord.created_at.asc())
        )
        offset = 0
        versions = DocumentVersionRepository(db)
        objects = StorageObjectRepository(db)
        svc = DocumentVersionService(db)

        while True:
            rows = q.offset(offset).limit(batch).all()
            if not rows:
                break
            for doc in rows:
                report["scanned"] += 1
                try:
                    if doc.current_version_id:
                        ver = versions.get(doc.current_version_id)
                        if ver and ver.storage_object_id == doc.current_storage_object_id:
                            report["skipped_already"] += 1
                            continue
                        if ver and ver.storage_object_id != doc.current_storage_object_id:
                            report["mismatch_current"] += 1
                    existing = versions.get_by_document_and_number(doc.id, 1)
                    if existing:
                        if not doc.current_version_id:
                            if execute:
                                doc.current_version_id = existing.id
                                db.commit()
                                report["created"] += 1  # link only
                            else:
                                report["created"] += 1
                        else:
                            report["skipped_already"] += 1
                        continue
                    obj = objects.get(doc.current_storage_object_id)
                    if not obj:
                        report["skipped_no_object"] += 1
                        continue
                    entry = {
                        "document_id": doc.id,
                        "storage_object_id": obj.id,
                        "organization_id": doc.organization_id,
                    }
                    if len(report["sample"]) < 20:
                        report["sample"].append(entry)
                    if execute:
                        svc.create_initial_version(
                            document=doc,
                            storage_obj=obj,
                            created_by_user_id=doc.owner_user_id,
                            source=doc.source,
                            commit=True,
                        )
                    report["created"] += 1
                except Exception as exc:  # noqa: BLE001
                    report["errors"] += 1
                    db.rollback()
                    print(f"ERROR document_id={doc.id} err={type(exc).__name__}")
            offset += batch
            if not execute:
                # preview: one batch enough for sample unless user wants full scan
                if offset >= batch * 5:
                    report["note"] = "preview capped at 5 batches"
                    break

        print(json.dumps(report, indent=2, default=str))
        return 0 if report["errors"] == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
