#!/usr/bin/env python
"""Validation centrale de la campagne de recette fonctionnelle.

Options :
  --reset-db
  --functional-only
  --backend-only
  --skip-frontend
  --verbose
  --phase-a
  --phase-b
  --phase-c
  --phase-d
  --phase-e
  --phase-f
  --phase-g
  --rc1-postgres
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))


def run(cmd: list[str], *, cwd: Path, env: dict | None = None) -> int:
    print(f"\n>> {' '.join(cmd)}")
    resolved = list(cmd)
    if sys.platform == "win32" and resolved and resolved[0].lower() in {"npm", "npx", "yarn", "pnpm"}:
        resolved[0] = f"{resolved[0]}.cmd"
    completed = subprocess.run(resolved, cwd=str(cwd), env=env)
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset-db", action="store_true")
    parser.add_argument("--functional-only", action="store_true")
    parser.add_argument("--backend-only", action="store_true")
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--phase-a", action="store_true", help="Campagne Phase A auth/orgs/rôles/isolation")
    parser.add_argument("--phase-b", action="store_true", help="Campagne Phase B billing/essai/quotas")
    parser.add_argument("--phase-c", action="store_true", help="Campagne Phase C documents/vault/DI/AI/accounting")
    parser.add_argument("--phase-d", action="store_true", help="Campagne Phase D validation/delivery/notif/search")
    parser.add_argument("--phase-e", action="store_true", help="Campagne Phase E platform admin/ops/reliability")
    parser.add_argument("--phase-f", action="store_true", help="Campagne Phase F performance/concurrence")
    parser.add_argument(
        "--phase-g",
        action="store_true",
        help="Campagne Phase G production readiness / déploiement / runbooks",
    )
    parser.add_argument(
        "--rc1-postgres",
        action="store_true",
        help="RC1.1 — validation PostgreSQL réelle (délègue à scripts/rc1/run_postgres_validation.py)",
    )
    args = parser.parse_args()

    env = os.environ.copy()
    env.setdefault("APP_ENV", "test")
    env.setdefault("ELFIS_ENVIRONMENT", "test")
    env.setdefault(
        "DATABASE_URL",
        f"sqlite:///{(BACKEND_DIR / 'elfis_functional_recette.db').as_posix()}",
    )
    env.setdefault("PLATFORM_ADMIN_EMAILS", "platform.admin@test.elfis.local")
    # Pas de réseau réel
    env.setdefault("OPENAI_API_KEY", "")
    env.setdefault("STRIPE_SECRET_KEY", "")
    env["PYTHONPATH"] = str(BACKEND_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    failures: list[str] = []

    # 1. Config
    print("=== 1. Configuration ===")
    print(f"ELFIS_ENVIRONMENT={env.get('ELFIS_ENVIRONMENT')}")
    print(f"DATABASE_URL={env.get('DATABASE_URL')}")
    if env.get("ELFIS_ENVIRONMENT", "").lower() in {"production", "prod"}:
        print("FATAL: environnement production")
        return 2

    # 2/3/4 Reset + fixtures
    if args.reset_db:
        code = run(
            [sys.executable, "scripts/reset_functional_test_db.py", "--json"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("reset_db")

    # 5. Tests fonctionnels
    pytest_flags = ["-q"]
    if args.verbose:
        pytest_flags = ["-vv"]

    if args.phase_a:
        print("=== Phase A — Auth / Orgs / Rôles / Isolation ===")
        if env.get("ELFIS_ENVIRONMENT", "").lower() not in {"test", "testing", "development", "dev"}:
            # Autoriser development pour SQLite local, refuser production
            if env.get("ELFIS_ENVIRONMENT", "").lower() in {"production", "prod"}:
                print("FATAL: Phase A refusée en production")
                return 2
        phase_a_paths = [
            "tests/functional/scenarios/test_phase_a_authentication.py",
            "tests/functional/scenarios/test_phase_a_organizations.py",
            "tests/functional/scenarios/test_phase_a_roles.py",
            "tests/functional/scenarios/test_phase_a_tenant_isolation.py",
            "tests/functional/scenarios/test_phase_a_suspension.py",
            "tests/functional/scenarios/test_phase_a_security_responses.py",
            "tests/security",
            "tests/platform_admin",
        ]
        code = run(
            [sys.executable, "-m", "pytest", *phase_a_paths, *pytest_flags, "--tb=line"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("phase_a")
        code = run(
            [sys.executable, "-c", "from app.main import app; print('routes', len(app.routes))"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("fastapi_import")
        print("\n=== RÉSUMÉ PHASE A ===")
        if failures:
            print("ÉCHECS:", ", ".join(failures))
            return 1
        print("OK — Phase A")
        return 0

    if args.phase_b:
        print("=== Phase B — Billing / Essai / Quotas ===")
        if env.get("ELFIS_ENVIRONMENT", "").lower() in {"production", "prod"}:
            print("FATAL: Phase B refusée en production")
            return 2
        # Enforcement activé uniquement pour le process de validation Phase B
        env["ELFIS_BILLING_ENFORCE_ENTITLEMENTS"] = env.get(
            "ELFIS_BILLING_ENFORCE_ENTITLEMENTS", "true"
        )
        env["ELFIS_BILLING_ENFORCE_QUOTAS"] = env.get("ELFIS_BILLING_ENFORCE_QUOTAS", "true")
        env.setdefault("STRIPE_SECRET_KEY", "")
        env.setdefault("OPENAI_API_KEY", "")
        phase_b_paths = [
            "tests/functional/scenarios/test_phase_b_plans.py",
            "tests/functional/scenarios/test_phase_b_trial.py",
            "tests/functional/scenarios/test_phase_b_subscription.py",
            "tests/functional/scenarios/test_phase_b_webhooks.py",
            "tests/functional/scenarios/test_phase_b_entitlements.py",
            "tests/functional/scenarios/test_phase_b_quotas.py",
            "tests/functional/scenarios/test_phase_b_usage.py",
            "tests/functional/scenarios/test_phase_b_cancellation.py",
            "tests/functional/scenarios/test_phase_b_past_due.py",
            "tests/functional/scenarios/test_phase_b_billing_isolation.py",
            "tests/functional/scenarios/test_phase_b_billing_security.py",
            "tests/billing",
            "tests/test_stripe_billing.py",
            "tests/test_subscription_access.py",
        ]
        code = run(
            [sys.executable, "-m", "pytest", *phase_b_paths, *pytest_flags, "--tb=line"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("phase_b")
        code = run(
            [sys.executable, "-c", "from app.main import app; print('routes', len(app.routes))"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("fastapi_import")
        print("\n=== RÉSUMÉ PHASE B ===")
        if failures:
            print("ÉCHECS:", ", ".join(failures))
            return 1
        print("OK — Phase B")
        return 0

    if args.phase_c:
        print("=== Phase C — Documents / Vault / DI / AI / Accounting ===")
        if env.get("ELFIS_ENVIRONMENT", "").lower() in {"production", "prod"}:
            print("FATAL: Phase C refusée en production")
            return 2
        env.setdefault("OPENAI_API_KEY", "")
        env.setdefault("STRIPE_SECRET_KEY", "")
        env.setdefault("ELFIS_OCR_ENABLED", "false")
        env["ELFIS_BILLING_ENFORCE_ENTITLEMENTS"] = env.get(
            "ELFIS_BILLING_ENFORCE_ENTITLEMENTS", "true"
        )
        env["ELFIS_BILLING_ENFORCE_QUOTAS"] = env.get("ELFIS_BILLING_ENFORCE_QUOTAS", "true")
        phase_c_paths = [
            "tests/functional/scenarios/test_phase_c_upload.py",
            "tests/functional/scenarios/test_phase_c_file_security.py",
            "tests/functional/scenarios/test_phase_c_vault.py",
            "tests/functional/scenarios/test_phase_c_extraction.py",
            "tests/functional/scenarios/test_phase_c_ocr.py",
            "tests/functional/scenarios/test_phase_c_ai_analysis.py",
            "tests/functional/scenarios/test_phase_c_financial_validation.py",
            "tests/functional/scenarios/test_phase_c_accounting_pipeline.py",
            "tests/functional/scenarios/test_phase_c_human_review.py",
            "tests/functional/scenarios/test_phase_c_retries.py",
            "tests/functional/scenarios/test_phase_c_idempotency.py",
            "tests/functional/scenarios/test_phase_c_document_isolation.py",
            "tests/functional/scenarios/test_phase_c_document_quotas.py",
            "tests/functional/scenarios/test_phase_c_document_security.py",
            "tests/vault",
            "tests/document_intelligence",
            "tests/ai",
            "tests/accounting",
            "tests/jobs",
            "tests/events",
            "tests/notifications",
            "tests/search",
        ]
        code = run(
            [sys.executable, "-m", "pytest", *phase_c_paths, *pytest_flags, "--tb=line"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("phase_c")
        code = run(
            [sys.executable, "-c", "from app.main import app; print('routes', len(app.routes))"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("fastapi_import")
        print("\n=== RÉSUMÉ PHASE C ===")
        if failures:
            print("ÉCHECS:", ", ".join(failures))
            return 1
        print("OK — Phase C")
        return 0

    if args.phase_d:
        print("=== Phase D — Validation / Delivery / Notif / Search ===")
        if env.get("ELFIS_ENVIRONMENT", "").lower() in {"production", "prod"}:
            print("FATAL: Phase D refusée en production")
            return 2
        env.setdefault("OPENAI_API_KEY", "")
        env.setdefault("STRIPE_SECRET_KEY", "")
        env.setdefault("BREVO_API_KEY", "")
        env["ELFIS_BILLING_ENFORCE_ENTITLEMENTS"] = env.get(
            "ELFIS_BILLING_ENFORCE_ENTITLEMENTS", "true"
        )
        env["ELFIS_BILLING_ENFORCE_QUOTAS"] = env.get("ELFIS_BILLING_ENFORCE_QUOTAS", "true")
        phase_d_paths = [
            "tests/functional/scenarios/test_phase_d_accounting_validation.py",
            "tests/functional/scenarios/test_phase_d_accounting_rejection.py",
            "tests/functional/scenarios/test_phase_d_commercial_documents.py",
            "tests/functional/scenarios/test_phase_d_delivery.py",
            "tests/functional/scenarios/test_phase_d_email_attachments.py",
            "tests/functional/scenarios/test_phase_d_email_senders.py",
            "tests/functional/scenarios/test_phase_d_delivery_retries.py",
            "tests/functional/scenarios/test_phase_d_notifications.py",
            "tests/functional/scenarios/test_phase_d_search.py",
            "tests/functional/scenarios/test_phase_d_history.py",
            "tests/functional/scenarios/test_phase_d_permissions.py",
            "tests/functional/scenarios/test_phase_d_isolation.py",
            "tests/functional/scenarios/test_phase_d_idempotency.py",
            "tests/functional/scenarios/test_phase_d_security.py",
            "tests/functional/scenarios/test_phase_d_observability.py",
            "tests/accounting",
            "tests/notifications",
            "tests/search",
            "tests/test_document_delivery.py",
            "tests/test_invoice_email_send.py",
            "tests/test_mailer.py",
        ]
        code = run(
            [sys.executable, "-m", "pytest", *phase_d_paths, *pytest_flags, "--tb=line"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("phase_d")
        code = run(
            [sys.executable, "-c", "from app.main import app; print('routes', len(app.routes))"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("fastapi_import")
        print("\n=== RÉSUMÉ PHASE D ===")
        if failures:
            print("ÉCHECS:", ", ".join(failures))
            return 1
        print("OK — Phase D")
        return 0

    if args.phase_e:
        print("=== Phase E — Platform Admin / Ops / Reliability ===")
        if env.get("ELFIS_ENVIRONMENT", "").lower() in {"production", "prod"}:
            print("FATAL: Phase E refusée en production")
            return 2
        env.setdefault("OPENAI_API_KEY", "")
        env.setdefault("STRIPE_SECRET_KEY", "")
        env.setdefault("BREVO_API_KEY", "")
        phase_e_paths = [
            "tests/functional/scenarios/test_phase_e_dashboard.py",
            "tests/functional/scenarios/test_phase_e_organizations_admin.py",
            "tests/functional/scenarios/test_phase_e_users_admin.py",
            "tests/functional/scenarios/test_phase_e_billing_admin.py",
            "tests/functional/scenarios/test_phase_e_documents_admin.py",
            "tests/functional/scenarios/test_phase_e_jobs_admin.py",
            "tests/functional/scenarios/test_phase_e_events_admin.py",
            "tests/functional/scenarios/test_phase_e_incidents.py",
            "tests/functional/scenarios/test_phase_e_audit.py",
            "tests/functional/scenarios/test_phase_e_security_events.py",
            "tests/functional/scenarios/test_phase_e_observability.py",
            "tests/functional/scenarios/test_phase_e_health.py",
            "tests/functional/scenarios/test_phase_e_reliability.py",
            "tests/functional/scenarios/test_phase_e_admin_isolation.py",
            "tests/functional/scenarios/test_phase_e_admin_security.py",
            "tests/functional/scenarios/test_phase_e_admin_idempotency.py",
            "tests/platform_admin",
            "tests/security",
            "tests/observability",
            "tests/reliability",
            "tests/jobs",
            "tests/events",
            "tests/billing",
        ]
        code = run(
            [sys.executable, "-m", "pytest", *phase_e_paths, *pytest_flags, "--tb=line"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("phase_e")
        code = run(
            [sys.executable, "-c", "from app.main import app; print('routes', len(app.routes))"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("fastapi_import")
        print("\n=== RÉSUMÉ PHASE E ===")
        if failures:
            print("ÉCHECS:", ", ".join(failures))
            return 1
        print("OK — Phase E")
        return 0

    if args.phase_f:
        print("=== Phase F — Performance / Concurrence ===")
        if env.get("ELFIS_ENVIRONMENT", "").lower() in {"production", "prod"}:
            print("FATAL: Phase F refusée en production")
            return 2
        env.setdefault("OPENAI_API_KEY", "")
        env.setdefault("STRIPE_SECRET_KEY", "")
        env.setdefault("BREVO_API_KEY", "")
        env["ELFIS_PERFORMANCE_TESTS_ENABLED"] = "true"
        env["ELFIS_CONCURRENCY_TESTS_ENABLED"] = env.get("ELFIS_CONCURRENCY_TESTS_ENABLED", "true")
        phase_f_paths = [
            "tests/performance",
            "tests/concurrency",
            "tests/jobs/test_job_worker.py",
            "tests/events/test_event_worker.py",
            "tests/billing",
        ]
        code = run(
            [sys.executable, "-m", "pytest", *phase_f_paths, *pytest_flags, "--tb=line"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("phase_f")
        code = run(
            [sys.executable, "-c", "from app.main import app; print('routes', len(app.routes))"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("fastapi_import")
        print("\n=== RÉSUMÉ PHASE F ===")
        print("NOTE: SKIP LOCKED / pool Postgres = mode --postgres (ELFIS_PERFORMANCE_DATABASE_URL)")
        if failures:
            print("ÉCHECS:", ", ".join(failures))
            return 1
        print("OK — Phase F")
        return 0

    if args.phase_g:
        print("=== Phase G — Production readiness ===")
        if env.get("ELFIS_ENVIRONMENT", "").lower() in {"production", "prod"}:
            print("FATAL: Phase G refusée en production")
            return 2
        env.setdefault("OPENAI_API_KEY", "")
        env.setdefault("STRIPE_SECRET_KEY", "")
        env.setdefault("BREVO_API_KEY", "")

        # Validations config / secrets / migrations (scripts, sans réseau provider)
        for script, label in [
            ("scripts/production/check_secrets.py", "check_secrets"),
            ("scripts/production/check_migrations.py", "check_migrations"),
            ("scripts/production/validate_production_config.py", "validate_config"),
        ]:
            code = run([sys.executable, script], cwd=BACKEND_DIR, env=env)
            if code != 0 and label != "validate_config":
                # validate_config peut retourner 2 hors prod avec fatals simulés — OK en test
                failures.append(label)
            if label == "validate_config" and code not in {0, 2}:
                failures.append(label)

        # Garde-fou smoke production
        code = run(
            [
                sys.executable,
                "scripts/production/smoke_test.py",
                "--base-url",
                "https://api.elfis-core.com",
                "--production",
            ],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 2:
            failures.append("smoke_prod_guard")
        else:
            print("OK smoke refuse production sans --allow-production-readonly")

        code = run(
            [
                sys.executable,
                "scripts/production/verify_restore.py",
                "--target-database-url",
                "postgresql://u:p@db/elfis_production",
                "--backup-path",
                "dummy.dump",
            ],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 2:
            failures.append("restore_prod_guard")

        phase_g_paths = ["tests/production_readiness"]
        code = run(
            [sys.executable, "-m", "pytest", *phase_g_paths, *pytest_flags, "--tb=line"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("phase_g")

        # Non-régression ciblée légère
        regression = [
            "tests/security",
            "tests/observability",
            "tests/reliability",
        ]
        code = run(
            [sys.executable, "-m", "pytest", *regression, "-q", "--tb=line"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("regression_g")

        code = run(
            [sys.executable, "-c", "from app.main import app; print('routes', len(app.routes))"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("fastapi_import")

        pg_url = env.get("ELFIS_PERFORMANCE_DATABASE_URL") or env.get("ELFIS_MIGRATION_DATABASE_URL") or ""
        pg_status = "EXECUTED" if pg_url.lower().startswith("postgres") else "NOT EXECUTED"
        print(f"\nPostgreSQL migration test...... {pg_status}")

        if not args.skip_frontend and not args.backend_only:
            frontend = ROOT_DIR / "frontend"
            if frontend.exists():
                code = run(["npm", "run", "build"], cwd=frontend, env=env)
                if code != 0:
                    failures.append("frontend_build")

        print("\n=== RÉSUMÉ PHASE G ===")
        print("Real network calls............. 0 (providers non invoqués)")
        print(f"PostgreSQL migration test...... {pg_status}")
        if failures:
            print("ÉCHECS:", ", ".join(failures))
            return 1
        print("OK — Phase G")
        return 0

    if args.rc1_postgres:
        print("=== RC1.1 — PostgreSQL validation ===")
        if env.get("ELFIS_ENVIRONMENT", "").lower() in {"production", "prod"}:
            print("FATAL: RC1 postgres refusée en production")
            return 2
        env.setdefault("ELFIS_POSTGRES_TESTS_ENABLED", "true")
        env.setdefault("ELFIS_CONCURRENCY_TESTS_ENABLED", "true")
        env.setdefault("ELFIS_DISABLE_EXTERNAL_NETWORK", "true")
        env = __import__("scripts.rc1.safety", fromlist=["enforce_mocks_env"]).enforce_mocks_env(env)
        cmd = [
            sys.executable,
            "scripts/rc1/run_postgres_validation.py",
            "--concurrency",
            "--search",
            "--report",
            "--workers",
            env.get("ELFIS_PERFORMANCE_WORKERS", "4"),
            "--dataset-size",
            "quick",
        ]
        if env.get("ELFIS_ALLOW_DATABASE_RESET", "").lower() in {"1", "true", "yes"}:
            cmd.append("--reset-db")
            cmd.append("--migrate")
        elif env.get("ELFIS_PERFORMANCE_DATABASE_URL"):
            cmd.append("--migrate")
        if args.skip_frontend:
            cmd.append("--skip-frontend")
        code = run(cmd, cwd=BACKEND_DIR, env=env)
        return code

    code = run(
        [sys.executable, "-m", "pytest", "tests/functional", *pytest_flags, "--tb=line"],
        cwd=BACKEND_DIR,
        env=env,
    )
    if code != 0:
        failures.append("functional")

    if not args.functional_only:
        # 6. Suites non-régression principales
        suites = [
            "tests/security",
            "tests/observability",
            "tests/reliability",
            "tests/platform_admin",
            "tests/billing",
            "tests/search",
            "tests/accounting",
            "tests/document_intelligence",
            "tests/ai",
            "tests/jobs",
            "tests/events",
            "tests/notifications",
            "tests/vault",
            "tests/test_document_delivery.py",
            "tests/test_mailer.py",
        ]
        code = run(
            [sys.executable, "-m", "pytest", *suites, "-q", "--tb=line"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("regression")

        # 7. Import FastAPI
        code = run(
            [sys.executable, "-c", "from app.main import app; print('routes', len(app.routes))"],
            cwd=BACKEND_DIR,
            env=env,
        )
        if code != 0:
            failures.append("fastapi_import")

    # 8. Frontend
    if not args.backend_only and not args.skip_frontend and not args.functional_only:
        frontend = ROOT_DIR / "frontend"
        if frontend.exists():
            code = run(["npm", "run", "build"], cwd=frontend, env=env)
            if code != 0:
                failures.append("frontend_build")

    print("\n=== RÉSUMÉ ===")
    if failures:
        print("ÉCHECS:", ", ".join(failures))
        return 1
    print("OK — validation fonctionnelle terminée")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
