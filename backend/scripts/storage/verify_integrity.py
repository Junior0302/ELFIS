"""CLI vérification d'intégrité storage.

Usage:
  python -m scripts.storage.verify_integrity --preview
  python -m scripts.storage.verify_integrity --provider supabase --full-checksum --confirm
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true", default=True)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--provider", default="")
    parser.add_argument("--organization-id", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--full-checksum", action="store_true")
    parser.add_argument("--database-url", default="")
    args = parser.parse_args(argv)

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
    env = _require_env()
    print(f"ELFIS_ENVIRONMENT={env}")

    from app.audit.audit_logger import AuditLogger
    from app.database import SessionLocal
    from app.storage.storage_integrity_service import StorageIntegrityService

    db = SessionLocal()
    try:
        svc = StorageIntegrityService(db, audit_logger=AuditLogger(db))
        report = svc.verify(
            provider=args.provider or None,
            organization_id=args.organization_id or None,
            limit=args.batch_size,
            full_checksum=args.full_checksum,
            preview=not args.confirm,
        )
        payload = asdict(report)
        print(json.dumps(payload, indent=2, default=str))
        return 0 if report.failed == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
