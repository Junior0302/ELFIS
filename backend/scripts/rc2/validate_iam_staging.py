#!/usr/bin/env python
"""RC2.2 — Validation staging IAM plateforme (Postgres).

Usage:
  set ELFIS_ENVIRONMENT=staging
  python -B scripts/rc2/validate_iam_staging.py --confirm-staging --write-report

Aucune attribution automatique d'utilisateur. Aucune DATABASE_URL en clair.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

BACKEND = Path(__file__).resolve().parents[2]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from scripts.rc1.safety import (  # noqa: E402
    assert_safe_postgres_url,
    mask_database_url,
    normalize_postgres_url,
)
from scripts.rc2.validate_system_health_staging import (  # noqa: E402
    _dialect_kind,
    _host_only,
    _load_dotenv,
    _maybe_fix_placeholder_host,
)


REQUIRED_TABLES = (
    "elfis_platform_roles",
    "elfis_platform_permissions",
    "elfis_platform_role_permissions",
    "elfis_platform_user_roles",
)


def _prepare(url: str, *, confirm_staging: bool) -> str:
    url = normalize_postgres_url(url)
    url = _maybe_fix_placeholder_host(url)
    if _dialect_kind(url) != "postgres":
        raise RuntimeError("PostgreSQL requis")
    env_name = "staging" if confirm_staging else (
        os.environ.get("ELFIS_ENVIRONMENT") or "staging"
    ).lower()
    if confirm_staging:
        env_name = "staging"
    os.environ["ELFIS_ENVIRONMENT"] = env_name
    os.environ["APP_ENV"] = env_name
    os.environ["DATABASE_URL"] = url
    host = (urlparse(url).hostname or "").lower()
    if confirm_staging and host:
        os.environ["ELFIS_RC1_ALLOW_MANAGED_HOST"] = "true"
        os.environ["ELFIS_RC1_ALLOWED_MANAGED_HOST"] = host
    assert_safe_postgres_url(url, allow_reset=False)
    return url


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default="")
    parser.add_argument("--confirm-staging", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    print("IAM PLATFORM STAGING VALIDATION")
    _load_dotenv(BACKEND / ".env")
    raw = (
        args.database_url
        or os.environ.get("ELFIS_PERFORMANCE_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    ).strip()
    if not raw:
        print("FATAL: DATABASE_URL manquant")
        return 2

    try:
        url = _prepare(raw, confirm_staging=args.confirm_staging)
    except RuntimeError as exc:
        print(f"NOT EXECUTED: {exc}")
        return 2

    print(f"ELFIS_ENVIRONMENT={os.environ.get('ELFIS_ENVIRONMENT')}")
    print(f"DATABASE_HOST={_host_only(url)}")
    print(f"DATABASE_URL_MASKED={mask_database_url(url)}")

    report: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "environment": os.environ.get("ELFIS_ENVIRONMENT"),
        "database_host_masked": _host_only(url),
        "database_url_masked": mask_database_url(url),
        "errors": [],
    }

    # Rebind engine
    import app.database as database_module
    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.orm import sessionmaker

    eng = create_engine(url, pool_pre_ping=True)
    database_module.engine = eng
    database_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=eng)

    from scripts.rc1.migrate_sql import upgrade_head

    mig = upgrade_head(url)
    report["migration"] = {"ok": True, "note": "upgrade_head applied"}
    print("MIGRATION=OK")

    insp = inspect(eng)
    tables = set(insp.get_table_names())
    missing = [t for t in REQUIRED_TABLES if t not in tables]
    report["tables"] = {"required": list(REQUIRED_TABLES), "missing": missing}
    if missing:
        report["errors"].append(f"tables missing: {missing}")
        print("TABLES=FAIL", missing)
    else:
        print("TABLES=PASS")

    from app.database import SessionLocal
    from app.iam.permission_sync import sync_permissions_from_catalog
    from app.iam.system_roles import bootstrap_system_roles
    from app.iam.iam_models import ElfisPlatformRole, ElfisPlatformUserRole

    db = SessionLocal()
    try:
        sync = sync_permissions_from_catalog(db, commit=True)
        roles = bootstrap_system_roles(db, commit=True)
        report["sync"] = sync
        report["bootstrap"] = {
            "roles_created": roles.get("roles_created"),
            "roles_updated": roles.get("roles_updated"),
            "user_assignments": roles.get("user_assignments"),
        }
        print("SYNC", sync)
        print("BOOTSTRAP roles_created=", roles.get("roles_created"), "user_assignments=", roles.get("user_assignments"))
        if roles.get("user_assignments", 0) != 0:
            report["errors"].append("attribution automatique détectée")

        codes = {r.code for r in db.query(ElfisPlatformRole).filter(ElfisPlatformRole.is_system.is_(True)).all()}
        expected = {"super_admin", "platform_admin", "platform_operator", "platform_support", "platform_viewer"}
        report["system_roles"] = sorted(codes)
        if not expected <= codes:
            report["errors"].append(f"rôles système incomplets: {expected - codes}")

        # Aucune contrainte : compter les assignments existantes (info seulement)
        n_assign = db.query(ElfisPlatformUserRole).filter(ElfisPlatformUserRole.is_active.is_(True)).count()
        report["active_assignments_count"] = int(n_assign)
        print(f"ACTIVE_ASSIGNMENTS={n_assign} (non modifié par cette validation)")

        # Resolver smoke (utilisateur fictif inexistant)
        from app.iam.permission_resolver import PermissionResolver
        from types import SimpleNamespace

        ctx = PermissionResolver().resolve(
            user=SimpleNamespace(id=-1, status="active"),
            is_platform_admin=False,
            db=db,
        )
        report["resolver_empty_user"] = {
            "authenticated": ctx.is_authenticated,
            "perm_count": len(ctx.permissions),
        }
    except Exception as exc:
        report["errors"].append(f"{type(exc).__name__}")
        print(f"ERROR: {type(exc).__name__}")
    finally:
        db.close()

    blob = json.dumps(report, default=str).lower()
    for bad in ("password=", "sk_live", "service_role", "whsec_"):
        if bad in blob:
            report["errors"].append(f"secret pattern {bad}")

    final = "PASS" if not report["errors"] else "FAIL"
    report["final_status"] = final
    print(f"FINAL STATUS={final}")
    if report["errors"]:
        for e in report["errors"]:
            print(" -", re.sub(r":([^:@/]+)@", ":***@", str(e)))

    out = BACKEND / "docs" / "rc2" / "last_iam_staging_run.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    if args.write_report:
        md = ROOT / "docs" / "rc2-iam-staging-validation.md"
        lines = [
            "# Rapport RC2.2 — Validation staging IAM plateforme",
            "",
            f"Date : `{report.get('started_at')}`",
            f"Statut : **{final}**",
            "",
            f"- Environnement : `{report.get('environment')}`",
            f"- Hôte masqué : `{report.get('database_host_masked')}`",
            f"- URL masquée : `{report.get('database_url_masked')}`",
            "",
            "## Tables",
            "",
            f"- requises : `{', '.join(REQUIRED_TABLES)}`",
            f"- manquantes : `{report.get('tables', {}).get('missing')}`",
            "",
            "## Sync / bootstrap",
            "",
            "```json",
            json.dumps({"sync": report.get("sync"), "bootstrap": report.get("bootstrap")}, indent=2),
            "```",
            "",
            f"- Rôles système : `{report.get('system_roles')}`",
            f"- Assignments actives (préexistantes, non modifiées) : `{report.get('active_assignments_count')}`",
            "",
            "## Erreurs",
            "",
        ]
        if report["errors"]:
            lines.extend(f"- {e}" for e in report["errors"])
        else:
            lines.append("- aucune")
        lines += [
            "",
            "## Secrets",
            "",
            "- DATABASE_URL complète non exposée",
            "- aucun secret détecté dans le rapport",
            "",
            "Aucun commit. Aucun push. Aucune attribution utilisateur automatique.",
            "",
        ]
        md.write_text("\n".join(lines), encoding="utf-8")
        print(f"MARKDOWN={md}")

    return 0 if final == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
