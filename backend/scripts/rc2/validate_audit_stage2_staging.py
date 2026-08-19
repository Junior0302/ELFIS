#!/usr/bin/env python
"""RC2.3 étape 2 — Validation staging Activity Center / API audit lecture.

Usage:
  python -B scripts/rc2/validate_audit_stage2_staging.py --confirm-staging --write-report
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


def _prepare(url: str, *, confirm_staging: bool) -> str:
    url = normalize_postgres_url(url)
    url = _maybe_fix_placeholder_host(url)
    if _dialect_kind(url) != "postgres":
        raise RuntimeError("PostgreSQL requis")
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

    print("AUDIT ACTIVITY CENTER STAGING VALIDATION")
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

    report: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "environment": os.environ.get("ELFIS_ENVIRONMENT"),
        "database_host_masked": _host_only(url),
        "database_url_masked": mask_database_url(url),
        "status": "FAIL",
        "errors": [],
    }

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from app.audit.audit_logger import AuditLogger
    from app.audit.audit_sanitize import assert_no_secrets_in_payload
    from app.audit.audit_service import AuditService
    from app.audit.audit_filters import AuditEventFilters

    engine = create_engine(url)
    Local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Local()
    probe_id = None
    try:
        svc = AuditService(db, isolated_writes=False)
        al = AuditLogger(service=svc)
        ev = al.record_login_failure(
            email="stage2-probe@example.invalid",
            reason="stage2_probe",
            metadata={"password": "strip-me", "probe": "rc2.3-stage2"},
        )
        if not ev:
            report["errors"].append("probe_write_failed")
        else:
            probe_id = ev.id
            # pagination
            from datetime import timedelta
            from datetime import datetime as dt

            filt = AuditEventFilters(
                date_from=dt.utcnow() - timedelta(hours=24),
                limit=2,
                offset=0,
            )
            items = svc.list_events(filt)
            total = svc.count_events(filt)
            stats = svc.statistics(hours=24)
            detail = svc.get_event(probe_id)
            report["probe"] = {
                "event_id": probe_id,
                "action": detail.action if detail else None,
                "metadata_keys": list((detail.metadata_json or {}).keys()) if detail else [],
                "page_items": len(items),
                "total_24h": total,
                "stats_keys": sorted(stats.keys()),
                "login_failure": stats.get("login_failure"),
                "permission_denied": stats.get("permission_denied"),
            }
            if detail and detail.metadata_json and "password" in detail.metadata_json:
                report["errors"].append("password_persisted")
            if not assert_no_secrets_in_payload(report["probe"]):
                report["errors"].append("secrets_in_report")
            if "iam_changes" not in stats:
                report["errors"].append("stats_missing_iam_changes")
            if total < 1 or len(items) < 1:
                report["errors"].append("empty_list")

            # cleanup probe
            db.execute(text("DELETE FROM elfis_audit_events WHERE id = :id"), {"id": probe_id})
            db.commit()
            report["probe_deleted"] = True

        from app.main import app as fastapi_app

        paths = [getattr(r, "path", "") for r in fastapi_app.routes]
        report["audit_routes"] = [p for p in paths if "/admin/audit" in p]
        report["routes_total"] = len(fastapi_app.routes)
        report["frontend_route"] = "/elfadmin/activity"
        report["status"] = "PASS" if not report["errors"] else "FAIL"
    except Exception as exc:  # noqa: BLE001
        report["errors"].append(f"{type(exc).__name__}:{str(exc)[:200]}")
        report["status"] = "FAIL"
        if probe_id:
            try:
                db.rollback()
                db.execute(text("DELETE FROM elfis_audit_events WHERE id = :id"), {"id": probe_id})
                db.commit()
            except Exception:  # noqa: BLE001
                pass
    finally:
        db.close()
        engine.dispose()

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(report, indent=2, default=str))
    print(f"STATUS={report['status']}")

    if args.write_report:
        out = ROOT / "docs" / "rc2-audit-stage2-validation.md"
        out.write_text(
            "\n".join(
                [
                    "# Rapport RC2.3 étape 2 — Activity Center / API lecture",
                    "",
                    f"Date : `{report.get('finished_at')}`",
                    f"Statut : **{report['status']}**",
                    "",
                    f"- Environnement : `{report.get('environment')}`",
                    f"- Hôte masqué : `{report.get('database_host_masked')}`",
                    f"- URL masquée : `{report.get('database_url_masked')}`",
                    f"- Route frontend : `{report.get('frontend_route')}`",
                    f"- Routes API audit : `{report.get('audit_routes')}`",
                    f"- Routes totales : `{report.get('routes_total')}`",
                    "",
                    "## Probe",
                    "",
                    "```json",
                    json.dumps(report.get("probe"), indent=2, default=str),
                    "```",
                    "",
                    f"- Probe supprimé : `{report.get('probe_deleted')}`",
                    "",
                    "## Erreurs",
                    "",
                    f"- `{report.get('errors')}`",
                    "",
                    "## Secrets",
                    "",
                    "- DATABASE_URL non exposée en clair",
                    "- métadonnées password absentes du probe",
                    "",
                    "Aucun commit. Aucun push.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"REPORT={out}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
