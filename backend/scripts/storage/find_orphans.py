"""Détection prudente d'orphelins storage — aucune suppression automatique.

Usage:
  python -m scripts.storage.find_orphans --preview
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find storage orphans (preview only)")
    parser.add_argument("--preview", action="store_true", default=True)
    parser.add_argument("--pending-hours", type=float, default=24.0)
    parser.add_argument("--local-root", default="")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)

    from app.config import settings
    from app.database import SessionLocal
    from app.storage.providers.local_storage_provider import LocalStorageProvider
    from app.storage.storage_models import ElfisDocumentRecord, ElfisStorageObject
    from app.storage.storage_types import StorageObjectStatus
    from app.storage.storage_upload import TEMP_NAMESPACE

    provider = LocalStorageProvider(root=Path(args.local_root) if args.local_root else None)
    db = SessionLocal()
    anomalies: list[dict] = []
    try:
        # StorageObject sans fichier
        rows = (
            db.query(ElfisStorageObject)
            .filter(ElfisStorageObject.status == StorageObjectStatus.AVAILABLE.value)
            .limit(args.limit)
            .all()
        )
        for row in rows:
            if not provider.object_exists(namespace=row.namespace, object_key=row.object_key):
                anomalies.append(
                    {
                        "type": "storage_object_missing_file",
                        "id": row.id,
                        "age_hours": None,
                        "recommended_action": "investigate_then_mark_failed",
                    }
                )

        # Document sans objet courant
        docs = db.query(ElfisDocumentRecord).limit(args.limit).all()
        for doc in docs:
            if not doc.current_storage_object_id:
                anomalies.append(
                    {
                        "type": "document_without_object",
                        "id": doc.id,
                        "recommended_action": "review_or_archive",
                    }
                )
            else:
                obj = db.get(ElfisStorageObject, doc.current_storage_object_id)
                if obj is None:
                    anomalies.append(
                        {
                            "type": "document_object_row_missing",
                            "id": doc.id,
                            "recommended_action": "relink_or_fail",
                        }
                    )

        # pending trop ancien
        cutoff = datetime.utcnow() - timedelta(hours=max(1.0, args.pending_hours))
        pending = (
            db.query(ElfisStorageObject)
            .filter(
                ElfisStorageObject.status == StorageObjectStatus.PENDING.value,
                ElfisStorageObject.created_at < cutoff,
            )
            .limit(args.limit)
            .all()
        )
        for row in pending:
            anomalies.append(
                {
                    "type": "pending_too_old",
                    "id": row.id,
                    "recommended_action": "mark_failed_or_retry",
                }
            )

        failed = (
            db.query(ElfisStorageObject)
            .filter(ElfisStorageObject.status == StorageObjectStatus.FAILED.value)
            .limit(args.limit)
            .all()
        )
        for row in failed:
            anomalies.append(
                {
                    "type": "failed_abandoned",
                    "id": row.id,
                    "recommended_action": "cleanup_physical_if_present",
                }
            )

        # fichiers _temp (physique) — info only
        temps = provider.list_temp_keys(older_than_seconds=0)[: args.limit]
        for key, age in temps:
            anomalies.append(
                {
                    "type": "temp_file_present",
                    "id": f"{TEMP_NAMESPACE}:{key[:8]}",
                    "age_hours": round(age / 3600, 2),
                    "recommended_action": "run_cleanup_temp",
                }
            )
    finally:
        db.close()

    report = {
        "environment": settings.app_env,
        "preview": True,
        "auto_delete": False,
        "anomaly_count": len(anomalies),
        "anomalies": anomalies[: args.limit],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
