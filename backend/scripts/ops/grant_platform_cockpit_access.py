"""One-shot: grant Platform Cockpit admin access to a user (config only)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / ".env", override=True)

TARGET = "christambapro@gmail.com"


def check_url(label: str, url: str | None) -> dict:
    out: dict = {"label": label, "ok": False, "user": None, "error": None, "iam_tables": []}
    if not url:
        out["error"] = "missing_url"
        return out
    try:
        eng = create_engine(url, pool_pre_ping=True)
        with eng.connect() as c:
            row = c.execute(
                text(
                    "SELECT id, email, status, is_platform_admin "
                    "FROM users WHERE lower(email) = lower(:e)"
                ),
                {"e": TARGET},
            ).fetchone()
            out["user"] = dict(row._mapping) if row else None
            try:
                tables = c.execute(
                    text(
                        "SELECT tablename FROM pg_tables "
                        "WHERE schemaname='public' AND tablename LIKE 'elfis_platform%' "
                        "ORDER BY 1"
                    )
                ).fetchall()
                out["iam_tables"] = [t[0] for t in tables]
            except Exception:
                # sqlite
                tables = c.execute(
                    text(
                        "SELECT name FROM sqlite_master "
                        "WHERE type='table' AND name LIKE 'elfis_platform%'"
                    )
                ).fetchall()
                out["iam_tables"] = [t[0] for t in tables]
            out["ok"] = True
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
    return out


def main() -> int:
    from app.config import settings
    from app.database import SessionLocal, engine
    from app.models_saas import User

    print("=== LOCAL (settings.database_url) ===")
    local = check_url("local", settings.database_url)
    print(local)

    for key in ("ELFIS_RC1_DATABASE_URL", "ELFIS_PERFORMANCE_DATABASE_URL"):
        print(f"=== {key} ===")
        print(check_url(key, os.getenv(key)))

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email.ilike(TARGET)).first()
        if not user:
            print("LOCAL_USER_NOT_FOUND")
            return 2
        print("LOCAL_BEFORE", user.id, user.email, user.is_platform_admin, user.status)

        # 1) Flag cockpit gate
        user.is_platform_admin = True
        db.add(user)
        db.commit()
        db.refresh(user)
        print("LOCAL_AFTER_FLAG", user.is_platform_admin)

        # 2) IAM bootstrap + super_admin if tables available
        try:
            from app.iam import models as _iam  # noqa: F401
            from app.iam.iam_models import Base as _  # noqa
            from app.database import Base

            Base.metadata.create_all(
                bind=engine,
                tables=[
                    t
                    for name, t in Base.metadata.tables.items()
                    if name.startswith("elfis_platform_")
                    or name
                    in {
                        "elfis_platform_roles",
                        "elfis_platform_permissions",
                        "elfis_platform_role_permissions",
                        "elfis_platform_user_roles",
                    }
                ],
            )
            # create all iam models explicitly
            from app.iam import iam_models

            iam_models.ElfisPlatformRole.__table__.create(bind=engine, checkfirst=True)
            iam_models.ElfisPlatformPermission.__table__.create(bind=engine, checkfirst=True)
            iam_models.ElfisPlatformRolePermission.__table__.create(bind=engine, checkfirst=True)
            iam_models.ElfisPlatformUserRole.__table__.create(bind=engine, checkfirst=True)

            from app.iam.platform_role_service import PlatformRoleService
            from app.iam.permission_resolver import PermissionResolver

            svc = PlatformRoleService(db)
            boot = svc.ensure_system_roles()
            print("IAM_BOOTSTRAP", boot)
            # hiérarchie la plus adaptée : super_admin (toutes permissions catalogue)
            try:
                svc.assign_role_to_user(user.id, "super_admin", actor_user_id=user.id)
                print("ASSIGNED_ROLE super_admin")
            except Exception as exc:
                print("ASSIGN_SUPER_ADMIN_FAIL", exc)
                try:
                    svc.assign_role_to_user(user.id, "platform_admin", actor_user_id=user.id)
                    print("ASSIGNED_ROLE platform_admin")
                except Exception as exc2:
                    print("ASSIGN_PLATFORM_ADMIN_FAIL", exc2)

            roles = svc.list_user_roles(user.id)
            print("USER_ROLES", roles)
            perms = svc.effective_permissions_for_user(user.id)
            needed = {
                "platform.admin",
                "platform.operations",
                "platform.finance",
                "platform.support",
            }
            print("HAS_NEEDED", needed.issubset(perms), sorted(needed & set(perms)))
            ctx = PermissionResolver().resolve(
                user=user, is_platform_admin=True, db=db
            )
            print(
                "RESOLVER",
                "platform_role=",
                ctx.platform_role,
                "perm_count=",
                len(ctx.permissions),
            )
        except Exception as exc:
            print("IAM_SKIP", type(exc).__name__, str(exc)[:200])

        print("ALLOWLIST_CONTAINS_TARGET", TARGET.lower() in settings.platform_admin_email_set)
        print("ALLOWLIST_SIZE", len(settings.platform_admin_email_set))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
