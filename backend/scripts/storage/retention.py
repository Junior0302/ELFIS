"""CLI rétention / purge documentaire (RC2.4 étape 3) — preview par défaut.

Usage:
  python -m scripts.storage.retention --preview
  python -m scripts.storage.retention --purge --before YYYY-MM-DD --batch-size 100 --confirm

Aucune purge automatique. Confirmation obligatoire. Pas d'API publique.
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
        print("FATAL: ELFIS_ENVIRONMENT / APP_ENV non défini")
        raise SystemExit(2)
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description="Rétention / purge documents ELFIS")
    parser.add_argument("--preview", action="store_true", help="Aperçu (défaut)")
    parser.add_argument("--purge", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--confirm-production", action="store_true", help="Renforcé si production")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--before", default="", help="YYYY-MM-DD")
    parser.add_argument("--database-url", default="")
    parser.add_argument("--reason", default="retention_purge")
    args = parser.parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    env = _require_env()
    print(f"ELFIS_ENVIRONMENT={env}")
    print(f"APP_ENV={os.environ.get('APP_ENV')}")

    before = None
    if args.before.strip():
        before = datetime.fromisoformat(args.before.strip())

    from app.audit.audit_logger import AuditLogger
    from app.database import SessionLocal
    from app.storage.document_retention_service import DocumentRetentionService

    db = SessionLocal()
    try:
        audit = AuditLogger(db)
        svc = DocumentRetentionService(db, audit_logger=audit)
        dry_run = not args.purge
        if args.purge:
            if not args.confirm:
                print("FATAL: --confirm requis pour --purge")
                return 2
            if env in {"production", "prod"} and not args.confirm_production:
                print("FATAL: production — --confirm-production requis")
                return 2
            dry_run = False

        if dry_run:
            decisions = svc.preview_expired_documents(limit=args.batch_size or 100)
            eligible = [d for d in decisions if d.eligible]
            blocked = [d for d in decisions if not d.eligible]
            try:
                audit.record_document_purge_requested(
                    candidate_count=len(eligible),
                    preview=True,
                )
            except Exception:
                pass
            report = {
                "preview": True,
                "environment": env,
                "scanned_deleted": len(decisions),
                "eligible": len(eligible),
                "blocked": [
                    {"document_id": d.document_id, "blocked_reason": d.blocked_reason, "rule": d.rule}
                    for d in blocked[:50]
                ],
                "eligible_ids": [d.document_id for d in eligible[:50]],
            }
            print(json.dumps(report, indent=2, default=str))
            return 0

        result = svc.purge_candidates(
            before=before or datetime.utcnow(),
            batch_size=args.batch_size,
            reason=args.reason,
            dry_run=False,
        )
        result["environment"] = env
        try:
            audit.record_document_purge_requested(
                candidate_count=result.get("candidates", 0),
                preview=False,
            )
        except Exception:
            pass
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("failed", 0) == 0 else 1
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: {type(exc).__name__}: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
