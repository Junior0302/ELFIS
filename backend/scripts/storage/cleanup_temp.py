"""Nettoyage des fichiers temporaires storage (_temp uniquement).

Usage:
  python -m scripts.storage.cleanup_temp --preview
  python -m scripts.storage.cleanup_temp --execute --older-than-hours 24 --confirm
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cleanup storage _temp namespace")
    parser.add_argument("--preview", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--older-than-hours", type=float, default=24.0)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--local-root", default="")
    args = parser.parse_args(argv)

    from app.config import settings
    from app.storage.providers.local_storage_provider import LocalStorageProvider
    from app.storage.storage_upload import TEMP_NAMESPACE

    preview = not args.execute
    if args.execute and not args.confirm:
        print(json.dumps({"error": "confirmation_required", "hint": "--confirm obligatoire"}, ensure_ascii=False))
        return 2

    root = Path(args.local_root) if args.local_root else None
    provider = LocalStorageProvider(root=root)
    older_s = max(0.0, float(args.older_than_hours)) * 3600
    candidates = provider.list_temp_keys(older_than_seconds=int(older_s))[: max(1, args.batch_size)]

    report = {
        "environment": settings.app_env,
        "provider": provider.name,
        "namespace": TEMP_NAMESPACE,
        "preview": preview,
        "older_than_hours": args.older_than_hours,
        "candidates": len(candidates),
        "deleted": 0,
        "keys_prefix": [k[:8] for k, _ in candidates],
    }

    if preview:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    deleted = 0
    for key, _age in candidates:
        if provider.delete_object(namespace=TEMP_NAMESPACE, object_key=key):
            deleted += 1
    report["deleted"] = deleted
    report["preview"] = False

    try:
        from app.audit.audit_logger import AuditLogger
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            AuditLogger(db).record_storage_temp_cleanup(deleted=deleted, preview=False)
        finally:
            db.close()
    except Exception:
        pass

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
