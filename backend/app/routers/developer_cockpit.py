"""Platform Developer Cockpit V1 — agrégation technique sûre (lecture seule / diagnostics)."""

from __future__ import annotations

import ast
import os
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.routing import APIRoute
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.deps import require_developer_cockpit
from app.models_saas import User

router = APIRouter(prefix="/platform/developer", tags=["platform-developer-cockpit"])


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"


def _audit(action: str, user: User, request: Request, metadata: dict[str, Any] | None = None) -> None:
    try:
        from app.audit.audit_logger import AuditLogger
        from app.audit.audit_types import AuditCategory, AuditStatus, Severity

        AuditLogger(isolated_writes=True).service.record(
            action,
            severity=Severity.INFO,
            category=AuditCategory.SECURITY,
            status=AuditStatus.SUCCESS,
            success=True,
            message=f"Developer Cockpit: {action}",
            actor_user_id=user.id,
            actor_email=user.email,
            service="developer_cockpit",
            product="elfis-core",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata=metadata or {},
        )
    except Exception:  # noqa: BLE001
        pass


def _git_commit() -> str | None:
    try:
        root = Path(__file__).resolve().parents[2]
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(root),
            stderr=subprocess.DEVNULL,
            timeout=2,
            text=True,
        )
        return out.strip() or None
    except Exception:  # noqa: BLE001
        return None


def _secret_status(value: Any) -> str:
    if value is None:
        return "missing"
    raw = str(value).strip()
    if not raw:
        return "missing"
    if raw.lower() in {"change-me", "change-me-in-production", "todo", "xxx"}:
        return "invalid"
    return "configured"


@router.get("/meta")
def developer_meta(
    request: Request,
    user: User = Depends(require_developer_cockpit),
) -> dict[str, Any]:
    from app.config import settings

    _audit("DEVELOPER_META_READ", user, request)
    version = getattr(settings, "app_version", None) or "0.8.9"
    env = getattr(settings, "elfis_environment", None) or getattr(settings, "app_env", "development")
    return {
        "environment": env,
        "backend_version": version,
        "frontend_version_hint": "0.8.9",
        "git_commit": _git_commit(),
        "server_time": _utcnow(),
        "database_engine": engine.dialect.name,
        "capabilities": {
            "workers_api": False,
            "feature_flags_api": False,
            "traces_api": False,
            "sql_console": False,
            "shell_console": False,
            "requeue_api": False,
            "worker_restart_api": False,
        },
    }


@router.get("/overview")
def developer_overview(
    request: Request,
    user: User = Depends(require_developer_cockpit),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from app.config import settings
    from app.platform_admin.admin_service import AdminService

    _audit("DEVELOPER_OVERVIEW_READ", user, request)
    started = time.perf_counter()
    period = "24h"
    errors: list[str] = []
    dashboard: dict[str, Any] | None = None
    services: list[dict[str, Any]] = []
    metrics_snap: dict[str, Any] | None = None

    try:
        dashboard = AdminService(db).dashboard.get_dashboard(period=period)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"dashboard:{type(exc).__name__}")

    try:
        health = AdminService(db).health.check_all()
        services = list(health.get("services") or [])
    except Exception as exc:  # noqa: BLE001
        errors.append(f"health:{type(exc).__name__}")

    try:
        from app.observability.metrics import get_metrics_snapshot

        metrics_snap = get_metrics_snapshot()
    except Exception:  # noqa: BLE001
        metrics_snap = None

    uptime = None
    if isinstance(metrics_snap, dict):
        uptime = metrics_snap.get("uptime_seconds")

    return {
        "generated_at": _utcnow(),
        "period": period,
        "environment": getattr(settings, "elfis_environment", None)
        or getattr(settings, "app_env", "development"),
        "uptime_seconds": uptime,
        "dashboard": dashboard,
        "services": services,
        "metrics_available": metrics_snap is not None,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "partial_errors": errors,
        "unavailable": {
            "workers": "Donnée indisponible — aucune API workers",
            "feature_flags": "Donnée indisponible — aucune API feature flags",
            "time_series_15m": "Donnée indisponible — périodes API limitées",
        },
    }


@router.get("/services")
def developer_services(
    request: Request,
    user: User = Depends(require_developer_cockpit),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from app.platform_admin.admin_service import AdminService

    _audit("DEVELOPER_SERVICES_READ", user, request)
    health = AdminService(db).health.check_all()
    items = []
    for data in health.get("services") or []:
        items.append(
            {
                "service": data.get("service"),
                "status": data.get("status"),
                "message": data.get("message"),
                "checked_at": data.get("checked_at"),
                "latency_ms": data.get("latency_ms"),
                "version": data.get("version"),
                "metrics": data.get("metrics") or {},
                "dependencies": [],
                "last_error": None,
                "request_count": None,
                "failure_count": None,
                "uptime": None,
            }
        )
    return {"generated_at": _utcnow(), "services": items, "total": len(items)}


@router.get("/config-status")
def developer_config_status(
    request: Request,
    user: User = Depends(require_developer_cockpit),
) -> dict[str, Any]:
    from app.config import settings

    _audit("DEVELOPER_CONFIG_READ", user, request)
    secret_keys = [
        "jwt_secret",
        "openai_api_key",
        "firebase_web_api_key",
        "stripe_secret_key",
        "brevo_api_key",
        "smtp_password",
    ]
    secrets = []
    for k in secret_keys:
        if hasattr(settings, k):
            secrets.append({"key": k, "status": _secret_status(getattr(settings, k))})
        else:
            secrets.append(
                {
                    "key": k,
                    "status": _secret_status(os.environ.get(k.upper()) or os.environ.get(k)),
                }
            )
    return {
        "generated_at": _utcnow(),
        "public": {
            "environment": getattr(settings, "elfis_environment", None)
            or getattr(settings, "app_env", None),
            "auth_required": bool(getattr(settings, "auth_required", True)),
            "cors_origins_configured": bool(getattr(settings, "cors_origins", None)),
            "database_engine": engine.dialect.name,
            "event_worker_enabled": bool(getattr(settings, "event_worker_enabled", False)),
            "job_worker_enabled": bool(getattr(settings, "job_worker_enabled", False)),
        },
        "secrets": secrets,
        "note": "Valeurs secrètes jamais exposées — statut configured/missing/invalid uniquement.",
    }


@router.get("/diagnostics")
def developer_diagnostics(
    request: Request,
    user: User = Depends(require_developer_cockpit),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from app.config import settings
    from app.platform_admin.admin_service import AdminService

    _audit("DEVELOPER_DIAGNOSTICS_RUN", user, request, {"safe": True})
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, message: str, recommendation: str, duration_ms: float | None) -> None:
        checks.append(
            {
                "name": name,
                "ok": ok,
                "message": message,
                "recommendation": recommendation,
                "duration_ms": duration_ms,
            }
        )

    t0 = time.perf_counter()
    add("api_ping", True, "Processus API vivant", "Aucune", round((time.perf_counter() - t0) * 1000, 2))

    t0 = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        add(
            "database_connectivity",
            True,
            f"OK ({engine.dialect.name})",
            "Aucune",
            round((time.perf_counter() - t0) * 1000, 2),
        )
    except Exception as exc:  # noqa: BLE001
        add(
            "database_connectivity",
            False,
            type(exc).__name__,
            "Vérifier DATABASE_URL",
            round((time.perf_counter() - t0) * 1000, 2),
        )

    ew = bool(getattr(settings, "event_worker_enabled", False))
    jw = bool(getattr(settings, "job_worker_enabled", False))
    add("workers_config", True, f"event_worker={ew} job_worker={jw}", "Flags config — pas de PID", None)

    fb = _secret_status(getattr(settings, "firebase_web_api_key", None))
    add("firebase_readiness", fb == "configured", f"firebase_web_api_key={fb}", "Configurer si auth Firebase", None)

    ai = _secret_status(getattr(settings, "openai_api_key", None))
    add("ai_provider_readiness", True, f"openai_api_key={ai}", "Optionnel en local", None)

    smtp = _secret_status(getattr(settings, "smtp_password", None))
    brevo = _secret_status(getattr(settings, "brevo_api_key", None))
    email_ok = smtp == "configured" or brevo == "configured"
    add("email_readiness", email_ok, f"smtp={smtp} brevo={brevo}", "Configurer SMTP ou Brevo", None)

    try:
        for data in AdminService(db).health.check_all().get("services") or []:
            status = str(data.get("status") or "").lower()
            add(
                f"service:{data.get('service')}",
                status in {"healthy", "ok", "up"},
                data.get("message") or status,
                "Voir Health Center si degraded",
                None,
            )
    except Exception:  # noqa: BLE001
        pass

    return {
        "generated_at": _utcnow(),
        "checks": checks,
        "mutable": False,
        "note": "Diagnostics lecture seule — aucune donnée métier modifiée.",
    }


@router.get("/database-summary")
def developer_database_summary(
    request: Request,
    user: User = Depends(require_developer_cockpit),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _audit("DEVELOPER_DATABASE_READ", user, request)
    t0 = time.perf_counter()
    ok = False
    err = None
    try:
        db.execute(text("SELECT 1"))
        ok = True
    except Exception as exc:  # noqa: BLE001
        err = type(exc).__name__

    table_count = None
    try:
        from app.database import Base

        table_count = len(Base.metadata.tables)
    except Exception:  # noqa: BLE001
        pass

    return {
        "generated_at": _utcnow(),
        "engine": engine.dialect.name,
        "status": "healthy" if ok else "critical",
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        "version": None,
        "size_bytes": None,
        "connections": None,
        "pool": None,
        "table_count_metadata": table_count,
        "error": err,
        "unavailable": ["size_bytes", "connections", "pool", "transactions", "migrations_list"],
        "note": "Console SQL désactivée. Données métier non exposées.",
    }


@router.get("/index-collisions")
def developer_index_collisions(
    request: Request,
    user: User = Depends(require_developer_cockpit),
) -> dict[str, Any]:
    _audit("DEVELOPER_INDEX_COLLISIONS_READ", user, request)
    app_root = Path(__file__).resolve().parents[1]
    idx: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in app_root.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        last_table = "?"
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == "__tablename__":
                        if isinstance(node.value, ast.Constant):
                            last_table = str(node.value.value)
            if isinstance(node, ast.Call):
                func = node.func
                name = None
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name == "Index" and node.args:
                    arg0 = node.args[0]
                    if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                        idx[arg0.value].append(
                            {
                                "file": str(path.relative_to(app_root.parent)),
                                "table": last_table,
                                "line": node.lineno,
                            }
                        )
    collisions = {k: v for k, v in idx.items() if len(v) > 1}
    return {
        "generated_at": _utcnow(),
        "total_named_indexes": len(idx),
        "duplicate_index_names": len(collisions),
        "collisions": collisions,
    }


@router.get("/routes")
def developer_routes_catalog(
    request: Request,
    user: User = Depends(require_developer_cockpit),
) -> dict[str, Any]:
    from app.main import app

    _audit("DEVELOPER_ROUTES_READ", user, request)
    routes: list[dict[str, Any]] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        methods = sorted(m for m in (route.methods or []) if m not in {"HEAD", "OPTIONS"})
        if not methods:
            continue
        path = route.path
        sensitive = any(s in path.lower() for s in ("secret", "token", "password", "key"))
        routes.append(
            {
                "methods": methods,
                "path": path,
                "name": route.name,
                "tags": list(route.tags or []),
                "sensitive_path": sensitive,
                "testable_get": False,
            }
        )
    routes.sort(key=lambda r: (r["path"], ",".join(r["methods"])))
    return {
        "generated_at": _utcnow(),
        "total": len(routes),
        "routes": routes,
        "note": "Catalogue lecture seule — aucune exécution de route depuis cette interface.",
    }


@router.get("/capabilities")
def developer_capabilities(
    request: Request,
    user: User = Depends(require_developer_cockpit),
) -> dict[str, Any]:
    _audit("DEVELOPER_CAPABILITIES_READ", user, request)
    return {
        "generated_at": _utcnow(),
        "pages": {
            "overview": "available",
            "services": "available",
            "api": "available",
            "workers": "unavailable",
            "jobs": "available_via_platform_jobs",
            "events": "available_via_platform_events",
            "logs": "available_via_admin_system_logs",
            "traces": "partial_correlation_ids_only",
            "database": "metrics_only",
            "cache": "unavailable",
            "storage": "available_via_admin_storage",
            "search": "available_via_platform_search",
            "ai": "available_via_platform_ai",
            "notifications": "available_via_platform_notifications",
            "feature_flags": "unavailable",
            "config": "status_only",
            "diagnostics": "available",
            "audit": "available_via_admin_audit",
        },
        "mutable_actions": {
            "job_retry": True,
            "job_cancel": True,
            "event_retry": True,
            "worker_restart": False,
            "sql_execute": False,
            "shell_execute": False,
            "feature_flag_write": False,
        },
    }
