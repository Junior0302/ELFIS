"""Health live / ready / details."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.security.security_config import environment_name, is_production


def live() -> dict[str, Any]:
    return {
        "status": "ok",
        "check": "live",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def ready(db: Session) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    overall = "ok"

    # DB
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as exc:
        checks["database"] = {"status": "error", "message": "database_unavailable"}
        overall = "error"

    # Migrations minimales (tables critiques)
    required_tables = [
        "users",
        "organizations",
        "elfis_jobs",
        "elfis_events",
    ]
    missing: list[str] = []
    for table in required_tables:
        try:
            if settings.database_url.startswith("sqlite"):
                row = db.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
                    {"n": table},
                ).fetchone()
            else:
                row = db.execute(
                    text("SELECT to_regclass(:n)"),
                    {"n": table},
                ).fetchone()
            if not row or not row[0]:
                missing.append(table)
        except Exception:
            missing.append(table)
    if missing:
        checks["migrations"] = {"status": "error", "missing_tables": missing}
        overall = "error"
    else:
        checks["migrations"] = {"status": "ok"}

    # Vault storage config (pas d'appel réseau)
    vault_ok = bool(settings.supabase_url and settings.supabase_service_role_key) or not is_production()
    checks["vault_storage"] = {
        "status": "ok" if vault_ok else "warning",
        "configured": bool(settings.supabase_url and settings.supabase_service_role_key),
    }
    if not vault_ok and overall == "ok":
        overall = "degraded"

    # Workers config (présence flags, pas de ping)
    checks["workers"] = {
        "status": "ok",
        "event_worker_enabled": bool(settings.elfis_event_worker_enabled),
        "job_worker_enabled": bool(settings.elfis_job_worker_enabled),
    }

    # Postgres en production
    if is_production() and settings.database_url.startswith("sqlite"):
        checks["database_engine"] = {"status": "error", "message": "sqlite_forbidden_in_production"}
        overall = "error"
    else:
        checks["database_engine"] = {
            "status": "ok",
            "engine": "sqlite" if settings.database_url.startswith("sqlite") else "postgres",
        }

    return {
        "status": overall,
        "check": "ready",
        "environment": environment_name(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": checks,
    }


def details(db: Session) -> dict[str, Any]:
    base = ready(db)
    modules = {
        "billing": {"enabled": bool(getattr(settings, "elfis_billing_enabled", True))},
        "ai": {"enabled": bool(getattr(settings, "elfis_ai_enabled", True))},
        "document_intelligence": {
            "enabled": bool(getattr(settings, "elfis_document_intelligence_enabled", True))
        },
        "accounting": {"enabled": bool(getattr(settings, "elfis_accounting_pipeline_enabled", True))},
        "search": {"enabled": bool(getattr(settings, "elfis_search_enabled", True))},
        "metrics": {"enabled": bool(getattr(settings, "elfis_metrics_enabled", True))},
        "cleanup": {
            "enabled": bool(getattr(settings, "elfis_cleanup_enabled", False)),
            "dry_run": bool(getattr(settings, "elfis_cleanup_dry_run", True)),
        },
    }
    base["modules"] = modules
    base["check"] = "details"
    return base
