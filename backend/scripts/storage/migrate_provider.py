"""CLI migration provider — preview par défaut, keep-source par défaut.

Usage:
  python -m scripts.storage.migrate_provider --preview
  python -m scripts.storage.migrate_provider --from-provider local --to-provider supabase \\
      --batch-size 50 --confirm --verify-checksum
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migration Storage provider")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--from-provider", default="local")
    parser.add_argument("--to-provider", default="supabase")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--organization-id", type=int, default=0)
    parser.add_argument("--document-id", default="")
    parser.add_argument("--verify-checksum", action="store_true", default=True)
    parser.add_argument("--no-verify-checksum", action="store_true")
    parser.add_argument("--keep-source", action="store_true", default=True)
    parser.add_argument("--delete-source-after-verify", action="store_true")
    parser.add_argument("--database-url", default="")
    args = parser.parse_args(argv)

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    env = _require_env()
    print(f"ELFIS_ENVIRONMENT={env}")

    execute = not args.preview and args.confirm
    if not args.preview and not args.confirm:
        # défaut preview
        execute = False

    from app.audit.audit_logger import AuditLogger
    from app.database import SessionLocal
    from app.storage.storage_migration_service import StorageMigrationService

    db = SessionLocal()
    try:
        svc = StorageMigrationService(db, audit_logger=AuditLogger(db))
        candidates = svc.preview_candidates(
            from_provider=args.from_provider,
            organization_id=args.organization_id or None,
            document_id=args.document_id or None,
            limit=max(1, min(args.batch_size, 200)),
        )
        report: dict = {
            "preview": not execute,
            "environment": env,
            "from_provider": args.from_provider,
            "to_provider": args.to_provider,
            "candidates": len(candidates),
            "migrated": 0,
            "failed": 0,
            "ids": [c.id for c in candidates[:50]],
        }
        if not execute:
            print(json.dumps(report, indent=2))
            return 0

        verify = not args.no_verify_checksum
        delete_source = bool(args.delete_source_after_verify)
        keep_source = not delete_source
        for obj in candidates:
            try:
                svc.migrate_one(
                    obj,
                    to_provider=args.to_provider,
                    verify_checksum=verify,
                    delete_source_after_verify=delete_source,
                    keep_source=keep_source,
                    dry_run=False,
                )
                report["migrated"] += 1
            except Exception as exc:  # noqa: BLE001
                report["failed"] += 1
                print(f"ERROR object={obj.id} err={type(exc).__name__}")
        print(json.dumps(report, indent=2))
        return 0 if report["failed"] == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
