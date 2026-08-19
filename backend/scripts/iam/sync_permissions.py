#!/usr/bin/env python
"""Synchronise permission_catalog → elfis_platform_permissions.

Usage:
  python -m scripts.iam.sync_permissions
  python -m scripts.iam.sync_permissions --mark-missing-inactive
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync IAM permission catalog to DB")
    parser.add_argument(
        "--mark-missing-inactive",
        action="store_true",
        help="Marque inactive les permissions DB absentes du catalogue (pas de delete)",
    )
    parser.add_argument(
        "--bootstrap-roles",
        action="store_true",
        help="Initialise aussi les rôles système (idempotent, aucun user)",
    )
    args = parser.parse_args()

    from app.database import SessionLocal, init_db
    from app.iam.permission_sync import sync_permissions_from_catalog
    from app.iam.system_roles import bootstrap_system_roles

    init_db()
    db = SessionLocal()
    try:
        stats = sync_permissions_from_catalog(
            db, mark_missing_inactive=args.mark_missing_inactive, commit=True
        )
        print("PERMISSIONS_SYNC", stats)
        if args.bootstrap_roles:
            roles = bootstrap_system_roles(db, commit=True)
            print("SYSTEM_ROLES", {k: roles[k] for k in roles if k != "permissions_sync"})
            print("USER_ASSIGNMENTS=0 (aucune attribution automatique)")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
