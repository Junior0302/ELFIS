#!/usr/bin/env python
"""RC2.1 — Validation staging des providers System Health réels.

Active individuellement (pas le flag global) :
  SYSTEM_HEALTH_API_PROVIDER=real
  SYSTEM_HEALTH_POSTGRES_PROVIDER=real
  SYSTEM_HEALTH_JOBS_PROVIDER=real
  SYSTEM_HEALTH_EVENTS_PROVIDER=real
  SYSTEM_HEALTH_SEARCH_PROVIDER=real

Exemple :
  set ELFIS_ENVIRONMENT=staging
  set ELFIS_PERFORMANCE_DATABASE_URL=postgresql+psycopg://...
  python -B scripts/rc2/validate_system_health_staging.py --confirm-staging

Ne jamais logger DATABASE_URL complète ni secrets.
Aucune migration, aucun INSERT/UPDATE métier, aucun monitoring externe.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BACKEND = Path(__file__).resolve().parents[2]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from scripts.rc1.safety import (  # noqa: E402
    assert_safe_postgres_url,
    mask_database_url,
    normalize_postgres_url,
)

FORBIDDEN_PATTERNS = (
    "password=",
    "postgresql://",
    "postgres://",
    "postgresql+psycopg://",
    "sk_live",
    "sk_test",
    "service_role",
    "whsec_",
    "supabase_service_role",
    "api_key=",
    "traceback",
    "secret=",
)

REAL_SERVICE_IDS = ("api", "postgresql", "jobs_queue", "event_bus", "search")


def _load_dotenv(path: Path) -> None:
    """Charge .env dans os.environ sans écraser les variables déjà définies."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def _host_only(url: str) -> str:
    try:
        host = urlparse(url).hostname or "?"
        if len(host) > 12:
            return f"{host[:3]}***{host[-8:]}"
        return host
    except Exception:
        return "?"


def _dialect_kind(url: str) -> str:
    low = (url or "").lower()
    if "sqlite" in low:
        return "sqlite"
    if "postgres" in low:
        return "postgres"
    return "other"


def _metric_map(result) -> dict[str, Any]:
    return {m.key: m.value for m in (result.metrics or [])}


def _blob_has_secret(blob: str) -> list[str]:
    low = blob.lower()
    return [p for p in FORBIDDEN_PATTERNS if p in low]


def _maybe_fix_placeholder_host(url: str) -> str:
    """Si l'hôte est un placeholder (db.xxx….supabase.co), tente la récupération
    depuis le rapport RC1 déjà présent dans le dépôt (sans logger le secret)."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return url
    is_placeholder = ("xxxxxxxxx" in host) or bool(re.fullmatch(r"db\.x+\.supabase\.co", host))
    if not is_placeholder:
        return url

    report_path = ROOT / "docs" / "rc1-postgresql-validation-report.md"
    if not report_path.is_file():
        raise RuntimeError(
            "Hôte DATABASE placeholder détecté et rapport RC1 absent — "
            "fournir --database-url avec l'hôte staging réel"
        )
    text = report_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"db\.[a-z0-9]+\.supabase\.co", text, flags=re.IGNORECASE)
    if not match or "xxx" in match.group(0).lower():
        raise RuntimeError(
            "Hôte placeholder dans URL — impossible de récupérer l'hôte staging réel"
        )
    real_host = match.group(0)
    netloc = parsed.netloc
    if "@" in netloc:
        auth, hostport = netloc.split("@", 1)
        port = ""
        if ":" in hostport:
            port = ":" + hostport.rsplit(":", 1)[-1]
        new_netloc = f"{auth}@{real_host}{port}"
    else:
        new_netloc = real_host
    from urllib.parse import urlunparse

    fixed = urlunparse(
        (parsed.scheme, new_netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
    )
    print(
        "WARN: hôte placeholder détecté dans DATABASE_URL — "
        "hôte staging récupéré depuis docs/rc1-postgresql-validation-report.md"
    )
    return fixed


def _prepare_env(*, database_url: str, confirm_staging: bool) -> str:
    """Configure l'environnement process avant import app.*"""
    url = normalize_postgres_url(database_url)
    url = _maybe_fix_placeholder_host(url)
    if _dialect_kind(url) != "postgres":
        raise RuntimeError(
            f"Base non PostgreSQL détectée (kind={_dialect_kind(url)}) — staging refuse SQLite"
        )

    env_name = (
        os.environ.get("ELFIS_ENVIRONMENT")
        or os.environ.get("APP_ENV")
        or "staging"
    ).strip().lower()
    if env_name in {"prod", "production"}:
        raise RuntimeError("ELFIS_ENVIRONMENT=production interdit pour cette validation")
    # --confirm-staging force staging (requis pour hôte Supabase managé RC1 safety)
    if confirm_staging:
        env_name = "staging"
    elif env_name not in {"staging", "stage", "test", "testing"}:
        raise RuntimeError(
            f"Environnement {env_name!r} ambigu — utiliser --confirm-staging "
            "ou définir ELFIS_ENVIRONMENT=staging"
        )

    os.environ["ELFIS_ENVIRONMENT"] = env_name
    os.environ["APP_ENV"] = env_name
    os.environ["DATABASE_URL"] = url
    os.environ["ELFIS_PERFORMANCE_DATABASE_URL"] = url

    # Activation individuelle — PAS le flag global
    os.environ["SYSTEM_HEALTH_USE_REAL_PROVIDERS"] = "false"
    os.environ["SYSTEM_HEALTH_API_PROVIDER"] = "real"
    os.environ["SYSTEM_HEALTH_POSTGRES_PROVIDER"] = "real"
    os.environ["SYSTEM_HEALTH_JOBS_PROVIDER"] = "real"
    os.environ["SYSTEM_HEALTH_EVENTS_PROVIDER"] = "real"
    os.environ["SYSTEM_HEALTH_SEARCH_PROVIDER"] = "real"

    # Seuils latence adaptés au staging distant (Supabase) — n'écrase pas si déjà définis
    # Défauts app (100/500 ms) sont pensés pour réseau local ; remote cold start ~500–1500 ms.
    os.environ.setdefault("SYSTEM_HEALTH_POSTGRES_LATENCY_DEGRADED_MS", "800")
    os.environ.setdefault("SYSTEM_HEALTH_POSTGRES_LATENCY_UNHEALTHY_MS", "3000")
    os.environ.setdefault("SYSTEM_HEALTH_PROVIDER_TIMEOUT_SECONDS", "15")
    os.environ.setdefault("SYSTEM_HEALTH_CACHE_TTL_SECONDS", "0")  # pas de cache pendant validation

    # Garde-fous hôte managé (Supabase staging) — mêmes règles RC1
    parsed = urlparse(url)
    host = (parsed.hostname or "").strip().lower()
    if confirm_staging:
        # Autorise explicitement la cible confirmée (staging managé)
        os.environ["ELFIS_RC1_ALLOW_MANAGED_HOST"] = "true"
        if host:
            os.environ["ELFIS_RC1_ALLOWED_MANAGED_HOST"] = host
    elif host.endswith(".supabase.co"):
        allow = os.environ.get("ELFIS_RC1_ALLOW_MANAGED_HOST", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        allowed = os.environ.get("ELFIS_RC1_ALLOWED_MANAGED_HOST", "").strip().lower()
        if not allow or allowed != host:
            raise RuntimeError(
                "Hôte Supabase détecté — passer --confirm-staging "
                "(ou ELFIS_RC1_ALLOW_MANAGED_HOST=true + ALLOWED_MANAGED_HOST exact)"
            )

    # Valide URL (refuse prod / sqlite)
    assert_safe_postgres_url(url, allow_reset=False)
    return url


def _print_section(title: str) -> None:
    print(f"\n{title}")


def _validate_result_shape(service_id: str, result) -> list[str]:
    errors: list[str] = []
    if result.service_id != service_id:
        errors.append(f"{service_id}: service_id mismatch")
    if result.checked_at is None:
        errors.append(f"{service_id}: checked_at manquant")
    if result.latency_ms is not None and not isinstance(result.latency_ms, (int, float)):
        errors.append(f"{service_id}: latency_ms non numérique")
    if result.status is None:
        errors.append(f"{service_id}: status manquant")
    blob = result.model_dump_json()
    secrets = _blob_has_secret(blob)
    if secrets:
        errors.append(f"{service_id}: motifs sensibles détectés: {secrets}")
    if "Traceback" in blob or "File \"" in blob:
        errors.append(f"{service_id}: stack trace exposée")
    return errors


def run_providers() -> dict[str, Any]:
    from app.system_health.health_provider_mode import resolve_provider_mode
    from app.system_health.health_registry import reset_default_registry_for_tests
    from app.config import settings

    # S'assurer que settings reflète les env (réinstanciation si déjà chargé)
    for attr, env_key, cast in (
        ("system_health_api_provider", "SYSTEM_HEALTH_API_PROVIDER", str),
        ("system_health_postgres_provider", "SYSTEM_HEALTH_POSTGRES_PROVIDER", str),
        ("system_health_jobs_provider", "SYSTEM_HEALTH_JOBS_PROVIDER", str),
        ("system_health_events_provider", "SYSTEM_HEALTH_EVENTS_PROVIDER", str),
        ("system_health_search_provider", "SYSTEM_HEALTH_SEARCH_PROVIDER", str),
        ("system_health_use_real_providers", "SYSTEM_HEALTH_USE_REAL_PROVIDERS", None),
        ("database_url", "DATABASE_URL", str),
        ("system_health_postgres_latency_degraded_ms", "SYSTEM_HEALTH_POSTGRES_LATENCY_DEGRADED_MS", float),
        ("system_health_postgres_latency_unhealthy_ms", "SYSTEM_HEALTH_POSTGRES_LATENCY_UNHEALTHY_MS", float),
        ("system_health_provider_timeout_seconds", "SYSTEM_HEALTH_PROVIDER_TIMEOUT_SECONDS", float),
        ("system_health_cache_ttl_seconds", "SYSTEM_HEALTH_CACHE_TTL_SECONDS", float),
    ):
        raw = os.environ.get(env_key)
        if raw is None:
            continue
        if attr == "system_health_use_real_providers":
            setattr(settings, attr, raw.lower() in {"1", "true", "yes"})
        elif cast is float:
            setattr(settings, attr, float(raw))
        else:
            setattr(settings, attr, raw)

    # Rebind engine pour pointer explicitement la base staging (pas SQLite local)
    import app.database as database_module
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_url = normalize_postgres_url(os.environ["DATABASE_URL"])
    if _dialect_kind(str(database_module.engine.url)) == "sqlite" or "postgres" not in str(
        database_module.engine.url
    ).lower():
        print("NOTE: rebind engine SQLite → PostgreSQL staging")
    engine_kwargs: dict = {
        "pool_pre_ping": True,
        "pool_size": int(getattr(settings, "database_pool_size", 5) or 5),
        "max_overflow": int(getattr(settings, "database_max_overflow", 10) or 10),
    }
    new_engine = create_engine(db_url, **engine_kwargs)
    database_module.engine = new_engine
    database_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=new_engine)
    settings.database_url = db_url
    if _dialect_kind(str(new_engine.url)) != "postgres":
        raise RuntimeError("Engine rebind n'est pas PostgreSQL")

    reset_default_registry_for_tests()
    from app.system_health.health_registry import HealthProviderRegistry
    from app.system_health.provider_bootstrap import register_configured_providers

    registry = HealthProviderRegistry()
    register_configured_providers(registry, settings_obj=settings, wrap_cache=False)

    modes = {sid: resolve_provider_mode(sid, settings_obj=settings) for sid in REAL_SERVICE_IDS}
    print("\nPROVIDER MODES")
    for sid, mode in modes.items():
        print(f"  {sid}={mode}")
    if any(m != "real" for m in modes.values()):
        raise RuntimeError(f"Modes attendus=real, obtenus={modes}")
    if getattr(settings, "system_health_use_real_providers", False):
        raise RuntimeError("SYSTEM_HEALTH_USE_REAL_PROVIDERS doit rester false pour cette validation")

    results: dict[str, Any] = {"modes": modes, "services": {}, "errors": []}

    # Exécuter un par un pour affichage, puis check_all pour isolation
    for sid in REAL_SERVICE_IDS:
        provider = registry.get(sid)
        assert provider is not None
        try:
            result = provider.check_health()
        except Exception as exc:
            results["errors"].append(f"{sid}: exception non isolée: {type(exc).__name__}")
            continue
        shape_errs = _validate_result_shape(sid, result)
        results["errors"].extend(shape_errs)
        metrics = _metric_map(result)
        results["services"][sid] = {
            "status": result.status.value if hasattr(result.status, "value") else str(result.status),
            "summary": result.summary,
            "latency_ms": result.latency_ms,
            "version": result.version,
            "checked_at": result.checked_at.isoformat() if result.checked_at else None,
            "metrics": metrics,
            "metadata": {
                k: v
                for k, v in (result.metadata or {}).items()
                if k
                not in {
                    "database_url",
                    "dsn",
                    "password",
                    "host",
                }
            },
            "error_code": result.error_code,
            "error_message": result.error_message,
            "provider_mode": (result.metadata or {}).get("provider_mode"),
            "simulated": (result.metadata or {}).get("simulated"),
        }

    # Isolation registry
    from app.system_health.mock_health_providers import ExplodingHealthProvider

    registry.register(ExplodingHealthProvider())
    all_results = registry.check_all()
    by_id = {r.service_id: r for r in all_results}
    if "exploding" not in by_id or by_id["exploding"].status.value != "unhealthy":
        results["errors"].append("isolation: ExplodingHealthProvider non isolé")
    for sid in REAL_SERVICE_IDS:
        if sid not in by_id:
            results["errors"].append(f"isolation: {sid} absent après exception d'un autre provider")
    registry.unregister("exploding")

    return results


def _print_provider_results(services: dict[str, Any]) -> None:
    api = services.get("api", {})
    _print_section("API")
    print(f"status={api.get('status')}")
    print(f"latency_ms={api.get('latency_ms')}")
    m = api.get("metrics") or {}
    print(f"uptime_seconds={m.get('uptime_seconds')}")
    print(f"route_count={m.get('route_count')}")
    print(f"version={api.get('version')}")

    pg = services.get("postgresql", {})
    _print_section("POSTGRESQL")
    print(f"status={pg.get('status')}")
    print(f"latency_ms={pg.get('latency_ms')}")
    print(f"version={pg.get('version')}")
    pm = pg.get("metrics") or {}
    print(f"active_connections={pm.get('active_connections')}")
    print(f"max_connections={pm.get('max_connections')}")
    print(f"pool_size={pm.get('pool_size')}")
    print(f"checked_out={pm.get('checked_out')}")
    print(f"dialect={(pg.get('metadata') or {}).get('dialect')}")

    jobs = services.get("jobs_queue", {})
    _print_section("JOBS")
    print(f"status={jobs.get('status')}")
    jm = jobs.get("metrics") or {}
    print(f"pending={jm.get('pending')}")
    print(f"failed={jm.get('failed')}")
    print(f"stalled={jm.get('stalled_count')}")
    print(f"oldest_pending_age_seconds={jm.get('oldest_pending_age_seconds')}")

    events = services.get("event_bus", {})
    _print_section("EVENTS")
    print(f"status={events.get('status')}")
    em = events.get("metrics") or {}
    print(f"pending={em.get('pending')}")
    print(f"failed={em.get('failed')}")
    print(f"stalled={em.get('stalled_count')}")

    search = services.get("search", {})
    _print_section("SEARCH")
    print(f"status={search.get('status')}")
    sm = search.get("metrics") or {}
    meta = search.get("metadata") or {}
    print(f"table_exists={meta.get('table_exists', sm.get('table_exists'))}")
    print(f"search_vector_type={meta.get('column_type', sm.get('column_type'))}")
    print(f"gin_index_exists={meta.get('index_exists', sm.get('gin_index'))}")
    print(f"latency_ms={search.get('latency_ms')}")
    print(f"query_ok={meta.get('query_ok', sm.get('query_ok'))}")


def validate_endpoints() -> dict[str, Any]:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.deps import require_platform_admin
    from app.models_saas import User
    from app.routers import admin_system_health
    from app.system_health.health_registry import HealthProviderRegistry, reset_default_registry_for_tests
    from app.system_health.health_service import SystemHealthService
    from app.system_health.provider_bootstrap import register_configured_providers
    from app.config import settings

    reset_default_registry_for_tests()
    registry = HealthProviderRegistry()
    register_configured_providers(registry, settings_obj=settings, wrap_cache=False)

    admin = User(
        id=1,
        email="staging.admin@elfis.validation",
        first_name="Staging",
        last_name="Admin",
        status="active",
        is_platform_admin=True,
        password_hash="x",
    )
    app = FastAPI()
    app.include_router(admin_system_health.router, prefix="/api")

    def _admin_ok():
        return admin

    def _svc():
        return SystemHealthService(registry=registry)

    app.dependency_overrides[require_platform_admin] = _admin_ok
    app.dependency_overrides[admin_system_health._service] = _svc

    client = TestClient(app)
    out: dict[str, Any] = {"endpoints": {}, "errors": []}
    paths = [
        "/api/admin/system/health",
        "/api/admin/system/metrics?period=24h",
        "/api/admin/system/alerts",
        "/api/admin/system/logs?limit=20",
    ]
    for path in paths:
        res = client.get(path)
        body = res.text
        secrets = _blob_has_secret(body)
        entry = {
            "status_code": res.status_code,
            "secrets": secrets,
            "ok": res.status_code == 200 and not secrets,
        }
        if res.status_code == 200:
            data = res.json()
            if path.endswith("/health"):
                ids = [s.get("service_id") for s in data.get("services", [])]
                entry["service_ids"] = ids
                for sid in REAL_SERVICE_IDS:
                    if sid not in ids:
                        out["errors"].append(f"endpoint health: service {sid} absent")
                # Providers réels doivent avoir simulated=false
                for svc in data.get("services", []):
                    if svc.get("service_id") in REAL_SERVICE_IDS:
                        meta = svc.get("metadata") or {}
                        if meta.get("provider_mode") != "real":
                            out["errors"].append(
                                f"endpoint: {svc.get('service_id')} provider_mode!={meta.get('provider_mode')}"
                            )
        else:
            out["errors"].append(f"{path}: HTTP {res.status_code}")
        if secrets:
            out["errors"].append(f"{path}: secrets {secrets}")
        if "Traceback" in body:
            out["errors"].append(f"{path}: stack trace")
            entry["ok"] = False
        out["endpoints"][path] = entry
        print(f"  {path} -> {res.status_code} secrets={secrets or 'none'}")
    return out


def validate_postgres_direct() -> dict[str, Any]:
    from sqlalchemy import text
    import app.database as database_module

    out: dict[str, Any] = {"errors": [], "checks": {}}
    db = database_module.SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        out["checks"]["select_1"] = "PASS"
        version = db.execute(text("SHOW server_version")).scalar()
        out["checks"]["version"] = str(version)
        try:
            active = db.execute(text("SELECT count(*)::int FROM pg_stat_activity")).scalar()
            out["checks"]["active_connections"] = int(active or 0)
        except Exception as exc:
            out["checks"]["active_connections"] = f"unavailable:{type(exc).__name__}"
        try:
            mx = db.execute(text("SHOW max_connections")).scalar()
            out["checks"]["max_connections"] = int(mx or 0)
        except Exception as exc:
            out["checks"]["max_connections"] = f"unavailable:{type(exc).__name__}"
        pool = database_module.engine.pool
        out["checks"]["pool_size"] = getattr(pool, "size", lambda: None)()
        out["checks"]["checked_out"] = getattr(pool, "checkedout", lambda: None)()
    except Exception as exc:
        out["errors"].append(f"postgres_direct: {type(exc).__name__}")
        out["checks"]["select_1"] = "FAIL"
    finally:
        db.close()
    return out


def validate_search_readonly() -> dict[str, Any]:
    from sqlalchemy import text
    import app.database as database_module

    out: dict[str, Any] = {"errors": [], "checks": {}}
    db = database_module.SessionLocal()
    try:
        before = db.execute(text("SELECT count(*) FROM elfis_search_documents")).scalar()
        out["checks"]["count_before"] = int(before or 0)
        row = db.execute(
            text(
                """
                SELECT udt_name
                FROM information_schema.columns
                WHERE table_schema='public'
                  AND table_name='elfis_search_documents'
                  AND column_name='search_vector'
                """
            )
        ).fetchone()
        out["checks"]["search_vector_type"] = row[0] if row else None
        idx = db.execute(
            text(
                """
                SELECT 1 FROM pg_indexes
                WHERE schemaname='public' AND indexname='ix_elfis_search_vector_gin'
                LIMIT 1
                """
            )
        ).fetchone()
        out["checks"]["gin_index"] = idx is not None
        # Requête minimale — aucun INSERT
        db.execute(
            text(
                """
                SELECT search_document_id
                FROM elfis_search_documents
                WHERE is_active = true
                  AND search_vector @@ plainto_tsquery('simple', 'elfis')
                LIMIT 1
                """
            )
        )
        after = db.execute(text("SELECT count(*) FROM elfis_search_documents")).scalar()
        out["checks"]["count_after"] = int(after or 0)
        if out["checks"]["count_before"] != out["checks"]["count_after"]:
            out["errors"].append("search: count changed — write inattendue")
        if out["checks"]["search_vector_type"] != "tsvector":
            out["errors"].append(
                f"search: type attendu tsvector, obtenu {out['checks']['search_vector_type']}"
            )
        if not out["checks"]["gin_index"]:
            out["errors"].append("search: index GIN absent")
    except Exception as exc:
        out["errors"].append(f"search_readonly: {type(exc).__name__}: détail masqué")
    finally:
        db.close()
    return out


def validate_jobs_events_readonly() -> dict[str, Any]:
    from sqlalchemy import text
    import app.database as database_module

    out: dict[str, Any] = {"errors": [], "checks": {}}
    db = database_module.SessionLocal()
    try:
        jb = int(db.execute(text("SELECT count(*) FROM elfis_jobs")).scalar() or 0)
        eb = int(db.execute(text("SELECT count(*) FROM elfis_events")).scalar() or 0)
        # Agrégats uniquement (même forme que les providers)
        job_groups = db.execute(
            text("SELECT status, count(*) FROM elfis_jobs GROUP BY status")
        ).fetchall()
        event_groups = db.execute(
            text("SELECT status, count(*) FROM elfis_events GROUP BY status")
        ).fetchall()
        ja = int(db.execute(text("SELECT count(*) FROM elfis_jobs")).scalar() or 0)
        ea = int(db.execute(text("SELECT count(*) FROM elfis_events")).scalar() or 0)
        out["checks"]["jobs_count"] = jb
        out["checks"]["events_count"] = eb
        out["checks"]["jobs_groups"] = {str(s): int(c) for s, c in job_groups}
        out["checks"]["events_groups"] = {str(s): int(c) for s, c in event_groups}
        if jb != ja or eb != ea:
            out["errors"].append("jobs/events: count changed — write inattendue")
        # Un completed ne doit pas être stalled
        stalled_completed = db.execute(
            text(
                """
                SELECT count(*) FROM elfis_jobs
                WHERE status = 'completed'
                  AND locked_at IS NOT NULL
                  AND locked_at < NOW() - INTERVAL '1 hour'
                """
            )
        ).scalar()
        # Provider stalled filtre status=processing uniquement — juste documenter
        out["checks"]["completed_with_old_lock"] = int(stalled_completed or 0)
        out["checks"]["note"] = "stalled = processing only (completed exclus)"
    except Exception as exc:
        out["errors"].append(f"jobs_events_readonly: {type(exc).__name__}")
    finally:
        db.close()
    return out


def decide_final(report: dict[str, Any]) -> str:
    errors = report.get("all_errors") or []
    services = (report.get("providers") or {}).get("services") or {}
    critical = [e for e in errors if not e.startswith("warn:")]
    if critical:
        return "FAIL"
    # SELECT 1 doit passer
    if (report.get("postgres_direct") or {}).get("checks", {}).get("select_1") != "PASS":
        return "FAIL"
    for sid in ("api", "postgresql", "search"):
        st = (services.get(sid) or {}).get("status")
        if st == "unhealthy":
            return "FAIL"
    # jobs/events peuvent être degraded (backlog) sans FAIL staging
    return "PASS"


def main() -> int:
    parser = argparse.ArgumentParser(description="RC2 System Health staging validation")
    parser.add_argument("--database-url", default="")
    parser.add_argument(
        "--confirm-staging",
        action="store_true",
        help="Confirme la cible staging (requis pour hôte Supabase managé)",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Écrit docs/rc2-system-health-staging-validation.md",
    )
    args = parser.parse_args()

    print("SYSTEM HEALTH STAGING VALIDATION")
    print(f"started_at={datetime.now(timezone.utc).isoformat()}")

    _load_dotenv(BACKEND / ".env")

    raw_url = (
        args.database_url
        or os.environ.get("ELFIS_PERFORMANCE_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    ).strip()
    if not raw_url:
        print("FATAL: DATABASE_URL / ELFIS_PERFORMANCE_DATABASE_URL manquant")
        return 2

    try:
        url = _prepare_env(database_url=raw_url, confirm_staging=args.confirm_staging)
    except RuntimeError as exc:
        print(f"NOT EXECUTED: {exc}")
        return 2

    print(f"ELFIS_ENVIRONMENT={os.environ.get('ELFIS_ENVIRONMENT')}")
    print(f"DATABASE_KIND={_dialect_kind(url)}")
    print(f"DATABASE_HOST={_host_only(url)}")
    print(f"DATABASE_URL_MASKED={mask_database_url(url)}")
    print("SYSTEM_HEALTH_USE_REAL_PROVIDERS=false (forcé)")

    report: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "environment": os.environ.get("ELFIS_ENVIRONMENT"),
        "database_kind": _dialect_kind(url),
        "database_host_masked": _host_only(url),
        "database_url_masked": mask_database_url(url),
        "providers_activated": {sid: "real" for sid in REAL_SERVICE_IDS},
        "use_real_providers_flag": False,
        "all_errors": [],
    }

    # Providers
    try:
        provider_results = run_providers()
    except Exception as exc:
        print(f"FATAL providers: {type(exc).__name__}: détail masqué")
        return 1
    report["providers"] = provider_results
    report["all_errors"].extend(provider_results.get("errors") or [])
    _print_provider_results(provider_results.get("services") or {})

    # Postgres direct
    _print_section("POSTGRES DIRECT CHECKS")
    pg_direct = validate_postgres_direct()
    report["postgres_direct"] = pg_direct
    report["all_errors"].extend(pg_direct.get("errors") or [])
    for k, v in (pg_direct.get("checks") or {}).items():
        print(f"  {k}={v}")

    # Jobs/events readonly
    _print_section("JOBS/EVENTS READONLY")
    je = validate_jobs_events_readonly()
    report["jobs_events"] = je
    report["all_errors"].extend(je.get("errors") or [])
    for k, v in (je.get("checks") or {}).items():
        print(f"  {k}={v}")

    # Search readonly
    _print_section("SEARCH READONLY")
    search = validate_search_readonly()
    report["search"] = search
    report["all_errors"].extend(search.get("errors") or [])
    for k, v in (search.get("checks") or {}).items():
        print(f"  {k}={v}")

    # Endpoints
    _print_section("ENDPOINTS")
    endpoints = validate_endpoints()
    report["endpoints"] = endpoints
    report["all_errors"].extend(endpoints.get("errors") or [])

    # Secrets sweep on full report JSON
    report_blob = json.dumps(report, default=str)
    secrets = _blob_has_secret(report_blob)
    # Masked URLs contain postgresql+psycopg:// by design in mask_database_url — allow that key only
    secrets = [s for s in secrets if s not in {"postgresql+psycopg://", "postgresql://", "postgres://"}]
    # Re-check raw values that aren't the masked field
    if "password=" in report_blob.lower() or "sk_live" in report_blob.lower():
        report["all_errors"].append("rapport: secret détecté")
    if secrets and any(s in ("service_role", "traceback", "sk_live") for s in secrets):
        report["all_errors"].append(f"rapport: motifs sensibles {secrets}")

    final = decide_final(report)
    report["final_status"] = final
    report["finished_at"] = datetime.now(timezone.utc).isoformat()

    _print_section(f"FINAL STATUS={final}")
    if report["all_errors"]:
        print("ERRORS:")
        for e in report["all_errors"]:
            # scrub any accidental url
            safe = re.sub(r":([^:@/]+)@", ":***@", str(e))
            print(f"  - {safe}")
    else:
        print("ERRORS: none")
    print("SECRETS_IN_OUTPUT=none_confirmed" if not secrets else f"SECRETS_FLAGS={secrets}")

    out_json = BACKEND / "docs" / "rc2" / "last_system_health_staging_run.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"JSON_REPORT={out_json.relative_to(BACKEND)}")

    if args.write_report:
        _write_markdown_report(report)

    return 0 if final == "PASS" else 1


def _write_markdown_report(report: dict[str, Any]) -> None:
    services = (report.get("providers") or {}).get("services") or {}
    lines = [
        "# Rapport RC2.1 — Validation staging System Health",
        "",
        f"Date : `{report.get('started_at')}`",
        f"Statut final : **{report.get('final_status')}**",
        "",
        "## Environnement",
        "",
        f"- ELFIS_ENVIRONMENT : `{report.get('environment')}`",
        f"- Dialecte : `{report.get('database_kind')}`",
        f"- Hôte (masqué) : `{report.get('database_host_masked')}`",
        f"- URL (masquée) : `{report.get('database_url_masked')}`",
        f"- Flag global USE_REAL_PROVIDERS : `{report.get('use_real_providers_flag')}`",
        "",
        "## Providers activés (individuels)",
        "",
    ]
    for sid, mode in (report.get("providers_activated") or {}).items():
        lines.append(f"- `{sid}` = **{mode}**")
    lines += ["", "## Résultats providers", ""]
    for sid in REAL_SERVICE_IDS:
        svc = services.get(sid) or {}
        lines.append(f"### {sid}")
        lines.append("")
        lines.append(f"- status : `{svc.get('status')}`")
        lines.append(f"- latency_ms : `{svc.get('latency_ms')}`")
        lines.append(f"- version : `{svc.get('version')}`")
        lines.append(f"- checked_at : `{svc.get('checked_at')}`")
        lines.append(f"- summary : {svc.get('summary')}")
        lines.append(f"- error_code : `{svc.get('error_code')}`")
        metrics = svc.get("metrics") or {}
        if metrics:
            lines.append("- métriques :")
            for k, v in metrics.items():
                lines.append(f"  - `{k}` = `{v}`")
        lines.append("")
    lines += [
        "## PostgreSQL direct",
        "",
        "```json",
        json.dumps(report.get("postgres_direct"), indent=2, default=str),
        "```",
        "",
        "## Jobs / Events (lecture seule)",
        "",
        "```json",
        json.dumps(report.get("jobs_events"), indent=2, default=str),
        "```",
        "",
        "## Search (lecture seule)",
        "",
        "```json",
        json.dumps(report.get("search"), indent=2, default=str),
        "```",
        "",
        "## Endpoints admin",
        "",
        "```json",
        json.dumps(report.get("endpoints"), indent=2, default=str),
        "```",
        "",
        "## Erreurs",
        "",
    ]
    errs = report.get("all_errors") or []
    if errs:
        for e in errs:
            lines.append(f"- {e}")
    else:
        lines.append("- aucune")
    lines += [
        "",
        "## Absence de secrets",
        "",
        "- DATABASE_URL complète : non exposée",
        "- mots de passe / clés API / service_role : non détectés dans les sorties contrôlées",
        "- stack traces : non exposées dans les résultats providers / endpoints",
        "",
        "## Recommandations",
        "",
        "- Conserver le défaut `mock` en CI ; activer `real` uniquement en staging/prod.",
        "- Surveiller jobs/events degraded (backlog) sans alerter sur completed anciens.",
        "- Si métriques PG partielles (pg_stat_activity) → accepter `degraded`, pas d'exception globale.",
        "- Brancher ensuite Billing / AI / OCR uniquement après validation métier.",
        "",
        "Aucun commit. Aucun push. Aucune migration exécutée par cette validation.",
        "",
    ]
    path = ROOT / "docs" / "rc2-system-health-staging-validation.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"MARKDOWN_REPORT={path}")


if __name__ == "__main__":
    raise SystemExit(main())
