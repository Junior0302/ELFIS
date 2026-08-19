#!/usr/bin/env python
"""RC2.3 — Validation staging Audit Engine (Postgres).

Usage:
  set ELFIS_ENVIRONMENT=staging
  python -B scripts/rc2/validate_audit_staging.py --confirm-staging --write-report

Aucune DATABASE_URL en clair dans le rapport.
"""

from __future__ import annotations

import argparse
import json
import os
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


REQUIRED_TABLES = ("elfis_audit_events",)
REQUIRED_INDEXES = (
    "ix_elfis_audit_events_occurred_at",
    "ix_elfis_audit_events_action",
    "ix_elfis_audit_events_actor_user_id",
    "ix_elfis_audit_events_correlation_id",
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
    parser.add_argument("--apply-sql", action="store_true", help="Appliquer SQL audit si table absente")
    args = parser.parse_args()

    print("AUDIT ENGINE STAGING VALIDATION")
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
        "status": "FAIL",
        "errors": [],
    }

    from sqlalchemy import create_engine, inspect, text

    engine = create_engine(url)
    try:
        if args.apply_sql:
            from scripts.rc1.migrate_sql import apply_sql_file

            sql_path = BACKEND / "sql" / "elfis_audit_events_postgres.sql"
            apply_sql_file(engine, sql_path)
            report["sql_applied"] = True

        insp = inspect(engine)
        tables = set(insp.get_table_names())
        missing = [t for t in REQUIRED_TABLES if t not in tables]
        report["tables"] = {"required": list(REQUIRED_TABLES), "missing": missing}
        if missing:
            report["errors"].append(f"tables_missing:{missing}")

        idx_names: set[str] = set()
        if "elfis_audit_events" in tables:
            for ix in insp.get_indexes("elfis_audit_events"):
                if ix.get("name"):
                    idx_names.add(ix["name"])
        missing_idx = [i for i in REQUIRED_INDEXES if i not in idx_names]
        report["indexes"] = {"required": list(REQUIRED_INDEXES), "missing": missing_idx}
        if missing_idx:
            report["errors"].append(f"indexes_missing:{missing_idx}")

        # Smoke write + read + sanitize
        from app.audit.audit_logger import AuditLogger
        from app.audit.audit_sanitize import assert_no_secrets_in_payload
        from app.audit.audit_service import AuditService
        from app.database import SessionLocal

        os.environ["DATABASE_URL"] = url
        # Rebind SessionLocal engine is already from settings — use local session
        from sqlalchemy.orm import sessionmaker

        Local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = Local()
        try:
            svc = AuditService(db, isolated_writes=False)
            al = AuditLogger(service=svc)
            ev = al.record_login_success(
                user_id=None,
                email="staging-audit-probe@example.invalid",
                metadata={"password": "should-strip", "probe": True},
            )
            if ev is None:
                report["errors"].append("record_failed")
            else:
                row = svc.get_event(ev.id)
                payload = {
                    "action": row.action if row else None,
                    "metadata": row.metadata_json if row else None,
                }
                if not assert_no_secrets_in_payload(payload):
                    report["errors"].append("secrets_detected")
                if row and row.metadata_json and "password" in row.metadata_json:
                    report["errors"].append("password_persisted")
                report["probe"] = {
                    "event_id": ev.id,
                    "action": ev.action,
                    "metadata_keys": list((ev.metadata_json or {}).keys()),
                }
                # cleanup probe
                db.delete(row)
                db.commit()
        finally:
            db.close()

        # Count routes presence (import app)
        from app.main import app as fastapi_app

        paths = [getattr(r, "path", "") for r in fastapi_app.routes]
        audit_routes = [p for p in paths if "/admin/audit" in p]
        report["audit_routes"] = audit_routes
        report["routes_total"] = len(fastapi_app.routes)
        if len(audit_routes) < 3:
            report["errors"].append("audit_routes_missing")

        report["status"] = "PASS" if not report["errors"] else "FAIL"
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:  # noqa: BLE001
        report["errors"].append(f"{type(exc).__name__}:{str(exc)[:200]}")
        report["status"] = "FAIL"
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
    finally:
        engine.dispose()

    print(json.dumps({k: v for k, v in report.items() if k != "database_url"}, default=str, indent=2))
    print(f"STATUS={report['status']}")

    if args.write_report:
        out = ROOT / "docs" / "rc2-audit-stage1-validation.md"
        lines = [
            "# Rapport RC2.3 — Validation staging Audit Engine",
            "",
            f"Date : `{report.get('finished_at')}`",
            f"Statut : **{report['status']}**",
            "",
            f"- Environnement : `{report.get('environment')}`",
            f"- Hôte masqué : `{report.get('database_host_masked')}`",
            f"- URL masquée : `{report.get('database_url_masked')}`",
            "",
            "## Tables",
            "",
            f"- requises : `{report.get('tables')}`",
            "",
            "## Index",
            "",
            f"- `{report.get('indexes')}`",
            "",
            "## Probe",
            "",
            "```json",
            json.dumps(report.get("probe"), indent=2, default=str),
            "```",
            "",
            f"- Routes audit : `{report.get('audit_routes')}`",
            f"- Routes totales : `{report.get('routes_total')}`",
            "",
            "## Erreurs",
            "",
            f"- `{report.get('errors')}`",
            "",
            "## Secrets",
            "",
            "- DATABASE_URL complète non exposée",
            "- aucun secret attendu dans le rapport",
            "",
            "Aucun commit. Aucun push.",
            "",
        ]
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"REPORT={out}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
