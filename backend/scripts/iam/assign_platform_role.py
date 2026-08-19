#!/usr/bin/env python
"""Attribue un rôle plateforme IAM à un utilisateur (manuel, confirmé).

Usage:
  python -m scripts.iam.assign_platform_role --user-id 1 --role platform_viewer --confirm
  python -m scripts.iam.assign_platform_role --user-id 1 --role super_admin --confirm
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

logger = logging.getLogger("iam.assign")


def main() -> int:
    parser = argparse.ArgumentParser(description="Assign platform IAM role to user")
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--role", type=str, required=True, help="code rôle (ex: platform_admin)")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirmation explicite requise",
    )
    parser.add_argument(
        "--revoke",
        action="store_true",
        help="Retire le rôle au lieu de l'attribuer",
    )
    args = parser.parse_args()

    if not args.confirm:
        print("REFUS: --confirm requis")
        return 2

    from app.database import SessionLocal, init_db
    from app.iam.platform_role_service import PlatformRoleService
    from app.iam.system_roles import bootstrap_system_roles
    from app.models_saas import User

    init_db()
    db = SessionLocal()
    try:
        bootstrap_system_roles(db, commit=True)
        user = db.get(User, args.user_id)
        if not user:
            print("FATAL: utilisateur introuvable")
            return 1
        # Ne jamais logger l'email en clair dans les sorties ops? email ok for admin CLI
        print(f"user_id={user.id} status={user.status}")
        print(f"role={args.role} action={'revoke' if args.revoke else 'assign'}")

        svc = PlatformRoleService(db)
        role = svc.get_role_by_code(args.role)
        if not role:
            print("FATAL: rôle introuvable — lancer sync_permissions --bootstrap-roles")
            return 1

        try:
            if args.revoke:
                svc.revoke_role_from_user(args.user_id, args.role, actor_user_id=None)
                print("OK revoked")
            else:
                svc.assign_role_to_user(args.user_id, args.role, actor_user_id=None)
                print("OK assigned")
            logger.info(
                "iam_cli_role_change",
                extra={
                    "user_id": args.user_id,
                    "role": args.role,
                    "action": "revoke" if args.revoke else "assign",
                    "success": True,
                },
            )
        except ValueError as exc:
            print(f"FAIL: {exc}")
            return 1
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
