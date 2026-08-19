#!/usr/bin/env python
"""RC2.3 étape 3 — Validation staging (index, recherche, export probe, rétention preview).

Usage:
  python -B scripts/rc2/validate_audit_stage3_staging.py --confirm-staging --write-report

N'archive/purge jamais des événements hors probe.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
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


def _prepare(url: str) -> str:
    url = normalize_postgres_url(url)
    url = _maybe_fix_placeholder_host(url)
    if _dialect_kind(url) != "postgres":
        raise RuntimeError("PostgreSQL requis")
    os.environ["ELFIS_ENVIRONMENT"] = "staging"
    os.environ["APP_ENV"] = "staging"
    os.environ["DATABASE_URL"] = url
    host = (urlparse(url).hostname or "").lower()
    if host:
        os.environ["ELFIS_RC1_ALLOW_MANAGED_HOST"] = "true"
        os.environ["ELFIS_RC1_ALLOWED_MANAGED_HOST"] = host
    assert_safe_postgres_url(url, allow_reset=False)
    return url


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default="")
    parser.add_argument("--confirm-staging", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--apply-sql", action="store_true")
    args = parser.parse_args()

    print("AUDIT STAGE3 STAGING VALIDATION")
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
    if not args.confirm_staging:
        print("FATAL: --confirm-staging requis")
        return 2

    try:
        url = _prepare(raw)
    except RuntimeError as exc:
        print(f"NOT EXECUTED: {exc}")
        return 2

    report: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "environment": "staging",
        "database_host_masked": _host_only(url),
        "database_url_masked": mask_database_url(url),
        "status": "FAIL",
        "errors": [],
        "cursor_pagination": "not_introduced_offset_limit_sufficient",
    }

    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(url)
    if args.apply_sql:
        from scripts.rc1.migrate_sql import apply_sql_file

        apply_sql_file(engine, BACKEND / "sql" / "elfis_audit_events_postgres.sql")
        report["sql_applied"] = True

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    for t in ("elfis_audit_events", "elfis_audit_events_archive"):
        if t not in tables:
            report["errors"].append(f"missing_table:{t}")

    idx = {ix["name"] for ix in insp.get_indexes("elfis_audit_events")} if "elfis_audit_events" in tables else set()
    for name in (
        "ix_elfis_audit_cat_occurred",
        "ix_elfis_audit_sev_occurred",
        "ix_elfis_audit_action_occurred",
    ):
        if name not in idx:
            report["errors"].append(f"missing_index:{name}")
    report["indexes_sample"] = sorted(list(idx))[:20]

    Local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Local()
    probe_ids: list[str] = []
    try:
        from app.audit.audit_export import AuditExportService
        from app.audit.audit_filters import AuditEventFilters
        from app.audit.audit_logger import AuditLogger
        from app.audit.audit_retention import AuditRetentionService
        from app.audit.audit_sanitize import assert_no_secrets_in_payload as assert_secrets
        from app.audit.audit_service import AuditService

        svc = AuditService(db, isolated_writes=False)
        al = AuditLogger(service=svc)
        ev = al.record_login_failure(
            email="stage3-probe@example.invalid",
            reason="stage3_probe",
            metadata={"password": "no", "probe": "rc2.3-s3"},
        )
        if ev:
            probe_ids.append(ev.id)

        filt = AuditEventFilters(
            date_from=datetime.utcnow() - timedelta(hours=24),
            q="stage3",
            limit=10,
        )
        items = svc.list_events(filt)
        stats = svc.statistics(hours=24)
        preview = AuditRetentionService(db).preview_retention(sample_limit=100)
        report["search"] = {"q_hits": len(items), "stats_total": stats.get("total")}
        report["retention_preview"] = {
            "expired_count": preview.get("expired_count"),
            "sample_scanned": preview.get("sample_scanned"),
        }

        # Export CSV en mémoire (probe window)
        exporter = AuditExportService(db)
        export_filters = AuditEventFilters(
            date_from=datetime.utcnow() - timedelta(days=1),
            actor_email="stage3-probe@example.invalid",
        )
        err = exporter.validate_export_filters(export_filters)
        chunks = list(exporter.export_csv_chunks(export_filters, actor_user_id=None))
        csv_blob = "".join(chunks)
        report["export"] = {
            "bytes": len(csv_blob.encode("utf-8")),
            "has_password": "password" in csv_blob.lower() and "no" in csv_blob,
            "validate": err,
        }
        if "password" in csv_blob and "\"password\"" in csv_blob:
            report["errors"].append("password_in_export")
        if not assert_secrets({"export_head": csv_blob[:500]}):
            report["errors"].append("secrets_in_export")

        # Cleanup probes only
        for pid in probe_ids:
            db.execute(text("DELETE FROM elfis_audit_events WHERE id = :id"), {"id": pid})
            db.execute(text("DELETE FROM elfis_audit_events_archive WHERE id = :id"), {"id": pid})
        db.commit()
        report["probes_deleted"] = len(probe_ids)

        from app.main import app as fastapi_app

        paths = [getattr(r, "path", "") for r in fastapi_app.routes]
        report["export_route"] = any("/admin/audit/export" in p for p in paths)
        report["routes_total"] = len(fastapi_app.routes)
        report["status"] = "PASS" if not report["errors"] else "FAIL"
    except Exception as exc:  # noqa: BLE001
        report["errors"].append(f"{type(exc).__name__}:{str(exc)[:240]}")
        report["status"] = "FAIL"
        db.rollback()
        for pid in probe_ids:
            try:
                db.execute(text("DELETE FROM elfis_audit_events WHERE id = :id"), {"id": pid})
                db.commit()
            except Exception:  # noqa: BLE001
                db.rollback()
    finally:
        db.close()
        engine.dispose()

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(report, indent=2, default=str))
    print(f"STATUS={report['status']}")

    if args.write_report:
        out = ROOT / "docs" / "rc2-audit-stage3-validation.md"
        out.write_text(
            "\n".join(
                [
                    "# Rapport RC2.3 étape 3 — recherche / rétention / export",
                    "",
                    f"Date : `{report.get('finished_at')}`",
                    f"Statut : **{report['status']}**",
                    "",
                    f"- Environnement : staging",
                    f"- Hôte masqué : `{report.get('database_host_masked')}`",
                    f"- URL masquée : `{report.get('database_url_masked')}`",
                    f"- Pagination cursor : `{report.get('cursor_pagination')}`",
                    f"- Route export présente : `{report.get('export_route')}`",
                    f"- Routes totales : `{report.get('routes_total')}`",
                    "",
                    "## Index / tables",
                    "",
                    f"- indexes : `{report.get('indexes_sample')}`",
                    "",
                    "## Recherche / stats / preview",
                    "",
                    "```json",
                    json.dumps(
                        {
                            "search": report.get("search"),
                            "retention_preview": report.get("retention_preview"),
                            "export": report.get("export"),
                        },
                        indent=2,
                    ),
                    "```",
                    "",
                    f"- Probes supprimés : `{report.get('probes_deleted')}`",
                    "",
                    "## Erreurs",
                    "",
                    f"- `{report.get('errors')}`",
                    "",
                    "Aucun archivage de données réelles. Aucun commit. Aucun push.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"REPORT={out}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
