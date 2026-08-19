#!/usr/bin/env python
"""RC1.1 — Validation PostgreSQL réelle (migrations SQL, concurrence, search).

Alembic est absent en V1 : « upgrade head » = create_all ORM + sql/*.sql + index Phase F.

Exemple :
  set ELFIS_ENVIRONMENT=staging
  set ELFIS_POSTGRES_TESTS_ENABLED=true
  set ELFIS_ALLOW_DATABASE_RESET=true
  set ELFIS_PERFORMANCE_DATABASE_URL=postgresql+psycopg://user:***@localhost/elfis_rc1_recette
  set ELFIS_CONCURRENCY_TESTS_ENABLED=true
  set ELFIS_DISABLE_EXTERNAL_NETWORK=true

  python scripts/rc1/run_postgres_validation.py --reset-db --migrate --concurrency --search --report

Ne jamais logger le mot de passe. Aucun appel Stripe/OpenAI/SMTP/Supabase réel.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from scripts.rc1.safety import (  # noqa: E402
    assert_postgres_tests_enabled,
    assert_safe_postgres_url,
    assert_safe_rc1_environment,
    enforce_mocks_env,
    mask_database_url,
    normalize_postgres_url,
)


def run(cmd: list[str], *, env: dict, cwd: Path = BACKEND) -> int:
    print(f"\n>> {' '.join(cmd)}")
    resolved = list(cmd)
    if sys.platform == "win32" and resolved and resolved[0].lower() in {"npm", "npx"}:
        resolved[0] = f"{resolved[0]}.cmd"
    return int(subprocess.run(resolved, cwd=str(cwd), env=env).returncode)


def reset_public_schema(url: str) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
    engine.dispose()
    print("OK reset schema public")


def probe_connection(url: str) -> dict:
    from sqlalchemy import create_engine, text

    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        version = conn.execute(text("SHOW server_version")).scalar()
        ext = [
            r[0]
            for r in conn.execute(
                text("SELECT extname FROM pg_extension ORDER BY 1")
            ).fetchall()
        ]
    engine.dispose()
    return {"version": version, "extensions": ext}


def main() -> int:
    parser = argparse.ArgumentParser(description="RC1 PostgreSQL validation")
    parser.add_argument("--database-url", default="")
    parser.add_argument("--reset-db", action="store_true")
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--concurrency", action="store_true")
    parser.add_argument("--performance", action="store_true")
    parser.add_argument("--search", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--dataset-size", choices=("quick", "full"), default="quick")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--keep-data", action="store_true")
    parser.add_argument("--skip-frontend", action="store_true")
    args = parser.parse_args()

    report: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "alembic": False,
        "migration_strategy": "orm_create_all_plus_sql_scripts",
        "status": "running",
        "results": {},
    }
    failures: list[str] = []

    try:
        env_name = assert_safe_rc1_environment()
        assert_postgres_tests_enabled()
    except RuntimeError as exc:
        print(f"NOT EXECUTED: {exc}")
        report["status"] = "NOT_EXECUTED"
        report["reason"] = str(exc)
        _write_report(report, args.report)
        return 2

    url = normalize_postgres_url(
        (args.database_url or os.getenv("ELFIS_PERFORMANCE_DATABASE_URL") or "").strip()
    )
    try:
        url = assert_safe_postgres_url(url, allow_reset=args.reset_db)
    except RuntimeError as exc:
        print(f"NOT EXECUTED: {exc}")
        report["status"] = "NOT_EXECUTED"
        report["reason"] = str(exc)
        _write_report(report, args.report)
        return 2

    report["environment"] = env_name
    report["database_url_masked"] = mask_database_url(url)
    print(f"ELFIS_ENVIRONMENT={env_name}")
    print(f"DATABASE={mask_database_url(url)}")

    env = enforce_mocks_env(os.environ.copy())
    env["ELFIS_ENVIRONMENT"] = env_name
    env["ELFIS_POSTGRES_TESTS_ENABLED"] = "true"
    env["ELFIS_CONCURRENCY_TESTS_ENABLED"] = "true"
    env["ELFIS_PERFORMANCE_TESTS_ENABLED"] = "true"
    env["ELFIS_PERFORMANCE_DATABASE_URL"] = url
    env["DATABASE_URL"] = url
    env["ELFIS_PERFORMANCE_WORKERS"] = str(args.workers)
    env["PYTHONPATH"] = str(BACKEND) + os.pathsep + env.get("PYTHONPATH", "")
    env["ELFIS_AI_PROVIDER"] = "mock"
    env["ELFIS_BILLING_PROVIDER"] = "mock"
    env["ELFIS_OCR_PROVIDER"] = "disabled"
    env["OPENAI_API_KEY"] = ""
    env["BREVO_API_KEY"] = ""
    if env.get("STRIPE_SECRET_KEY", "").startswith("sk_live"):
        print("FATAL: Stripe live interdit")
        return 2

    # Driver
    try:
        import psycopg  # noqa: F401

        report["driver"] = f"psycopg {psycopg.__version__}"
    except ImportError:
        print("FATAL: psycopg non installé — pip install 'psycopg[binary]'")
        report["status"] = "FAILED"
        report["reason"] = "missing_psycopg"
        _write_report(report, args.report)
        return 1

    try:
        probe = probe_connection(url)
        report["postgresql"] = probe
        print(f"PostgreSQL {probe['version']}")
        report["results"]["connection"] = "PASS"
    except Exception as exc:
        print(f"FATAL connexion: {type(exc).__name__}")
        report["results"]["connection"] = "FAIL"
        report["status"] = "FAILED"
        _write_report(report, args.report)
        return 1

    if args.reset_db:
        try:
            assert_safe_postgres_url(url, allow_reset=True)
            reset_public_schema(url)
            report["results"]["reset"] = "PASS"
        except Exception as exc:
            print(f"FATAL reset: {exc}")
            failures.append("reset")
            report["results"]["reset"] = "FAIL"

    if args.migrate or args.reset_db:
        from scripts.rc1.migrate_sql import upgrade_head, verify_critical_indexes

        print("=== Migration 1 (upgrade head SQL) ===")
        r1 = upgrade_head(url)
        report["migration_1"] = {k: v for k, v in r1.items() if k != "files"}
        if not r1.get("ok"):
            failures.append("migrate_1")
            report["results"]["empty_migration"] = "FAIL"
        else:
            report["results"]["empty_migration"] = "PASS"
        print("=== Migration 2 (idempotente) ===")
        r2 = upgrade_head(url)
        report["migration_2_ok"] = r2.get("ok")
        report["results"]["idempotent_migration"] = "PASS" if r2.get("ok") else "FAIL"
        if not r2.get("ok"):
            failures.append("migrate_2")
        idx = verify_critical_indexes(url)
        report["indexes"] = idx
        report["results"]["critical_indexes"] = "PASS" if idx.get("ok") else "FAIL"
        if not idx.get("ok"):
            failures.append("indexes")

    # Tests Postgres
    pytest_paths: list[str] = []
    if args.concurrency or True:
        # Toujours exécuter les tests PG dédiés si connexion OK
        pytest_paths.extend(
            [
                "tests/concurrency/test_postgres_job_claiming.py",
                "tests/concurrency/test_postgres_event_claiming.py",
                "tests/concurrency/test_postgres_quota_atomicity.py",
                "tests/concurrency/test_postgres_pool.py",
                "tests/production_readiness/test_postgres_schema_consistency.py",
            ]
        )
    if args.concurrency:
        pytest_paths.extend(
            [
                "tests/concurrency/test_quota_atomicity.py",
                "tests/concurrency/test_accounting_validation_concurrency.py",
                "tests/concurrency/test_delivery_idempotency_concurrency.py",
                "tests/concurrency/test_webhook_idempotency_concurrency.py",
                "tests/concurrency/test_vault_duplicate_upload_concurrency.py",
                "tests/concurrency/test_tenant_isolation_under_load.py",
                "tests/concurrency/test_worker_recovery.py",
            ]
        )
    if args.search or args.performance:
        pytest_paths.append("tests/performance/test_search_performance.py")
    if args.performance:
        pytest_paths.extend(
            [
                "tests/performance/test_api_latency.py",
                "tests/performance/test_document_listing_performance.py",
                "tests/performance/test_platform_dashboard_performance.py",
            ]
        )

    # Dédupliquer
    seen = set()
    unique_paths = []
    for p in pytest_paths:
        if p not in seen:
            seen.add(p)
            unique_paths.append(p)

    code = run(
        [sys.executable, "-m", "pytest", *unique_paths, "-q", "--tb=line"],
        env=env,
    )
    report["results"]["postgres_pytest"] = "PASS" if code == 0 else "FAIL"
    if code != 0:
        failures.append("postgres_pytest")

    # FastAPI
    code = run(
        [sys.executable, "-c", "from app.main import app; print('routes', len(app.routes))"],
        env=env,
    )
    report["results"]["fastapi"] = "OK" if code == 0 else "FAIL"
    if code != 0:
        failures.append("fastapi")

    if not args.skip_frontend:
        frontend = ROOT / "frontend"
        if frontend.exists():
            code = run(["npm", "run", "build"], env=env, cwd=frontend)
            report["results"]["frontend"] = "OK" if code == 0 else "FAIL"
            if code != 0:
                failures.append("frontend")

    report["failures"] = failures
    report["status"] = "PASS" if not failures else "FAIL"
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["real_external_calls"] = 0
    _write_report(report, True)

    print("\n=== RÉSUMÉ RC1.1 POSTGRESQL ===")
    for k, v in report["results"].items():
        print(f"{k:32} {v}")
    print(f"status={report['status']}")
    print(f"database={report['database_url_masked']}")
    print("Real external calls............. 0")
    return 0 if not failures else 1


def _write_report(report: dict, enabled: bool) -> None:
    if not enabled and report.get("status") not in {"NOT_EXECUTED", "FAILED", "PASS", "FAIL"}:
        return
    out = ROOT / "docs" / "rc1-postgresql-validation-report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    # JSON annex
    json_path = BACKEND / "docs" / "rc1" / "last_postgres_run.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    lines = [
        "# Rapport RC1.1 — Validation PostgreSQL",
        "",
        f"Généré : {report.get('finished_at') or report.get('started_at')}",
        f"Statut : **{report.get('status')}**",
        "",
        "## Environnement",
        "",
        f"- ELFIS_ENVIRONMENT : `{report.get('environment', 'n/a')}`",
        f"- URL (masquée) : `{report.get('database_url_masked', 'n/a')}`",
        f"- Driver : `{report.get('driver', 'n/a')}`",
        f"- PostgreSQL : `{report.get('postgresql', {}).get('version', 'n/a')}`",
        f"- Alembic : **absent** — stratégie `{report.get('migration_strategy')}`",
        "",
        "## Résultats",
        "",
        "```",
        json.dumps(report.get("results", {}), indent=2, ensure_ascii=False),
        "```",
        "",
        f"Real external calls : {report.get('real_external_calls', 0)}",
        "",
        "## Raison / échecs",
        "",
        f"- reason : {report.get('reason', '')}",
        f"- failures : {report.get('failures', [])}",
        "",
        "Aucun commit. Aucun push.",
        "",
    ]
    if report.get("status") == "NOT_EXECUTED":
        lines.insert(
            6,
            "> **NOT EXECUTED** — fournir une base PostgreSQL de recette "
            "(`ELFIS_PERFORMANCE_DATABASE_URL`) + `ELFIS_POSTGRES_TESTS_ENABLED=true`.",
        )
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rapport écrit : {out}")


if __name__ == "__main__":
    raise SystemExit(main())
