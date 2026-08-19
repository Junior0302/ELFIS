"""CLI rétention / archivage audit — preview par défaut.

Usage:
  python -m scripts.audit.retention --preview
  python -m scripts.audit.retention --archive --confirm --batch-size 500
  python -m scripts.audit.retention --purge-archive --confirm
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))


def _require_env() -> str:
    env = (os.environ.get("ELFIS_ENVIRONMENT") or os.environ.get("APP_ENV") or "").strip().lower()
    if not env:
        print("FATAL: ELFIS_ENVIRONMENT / APP_ENV non défini (environnement ambigu)")
        raise SystemExit(2)
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description="Rétention audit ELFIS")
    parser.add_argument("--preview", action="store_true", help="Aperçu sans écriture (défaut)")
    parser.add_argument("--archive", action="store_true", help="Archiver les candidats expirés")
    parser.add_argument("--purge-archive", action="store_true", help="Purger archives très anciennes")
    parser.add_argument("--confirm", action="store_true", help="Confirmation obligatoire pour écriture")
    parser.add_argument("--batch-size", type=int, default=0)
    parser.add_argument("--before", default="", help="ISO date cutoff optionnelle (YYYY-MM-DD)")
    parser.add_argument("--database-url", default="")
    args = parser.parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    env = _require_env()
    print(f"ELFIS_ENVIRONMENT={env}")
    print(f"APP_ENV={os.environ.get('APP_ENV')}")
    # Ne jamais afficher DATABASE_URL

    from app.database import SessionLocal
    from app.audit.audit_retention import AuditRetentionService

    before = None
    if args.before.strip():
        before = datetime.fromisoformat(args.before.strip())

    db = SessionLocal()
    try:
        svc = AuditRetentionService(db)
        if args.archive:
            if not args.confirm:
                print("FATAL: --confirm requis pour --archive")
                return 2
            batch = args.batch_size or None
            result = svc.archive_expired(confirm=True, batch_size=batch, before=before)
            print(json.dumps(result, indent=2, default=str))
            return 0 if result.get("errors", 0) == 0 else 1
        if args.purge_archive:
            if not args.confirm:
                print("FATAL: --confirm requis pour --purge-archive")
                return 2
            result = svc.purge_archived_according_to_policy(
                confirm=True, batch_size=args.batch_size or None
            )
            print(json.dumps(result, indent=2, default=str))
            return 0
        # preview (défaut)
        result = svc.preview_retention(before=before)
        print(json.dumps(result, indent=2, default=str))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {type(exc).__name__}: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
