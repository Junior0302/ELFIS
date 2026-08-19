#!/usr/bin/env python
"""Campagne Phase F — performance / concurrence (rapide par défaut).

Usage:
  python scripts/performance/run_phase_f.py --quick
  python scripts/performance/run_phase_f.py --concurrency
  python scripts/performance/run_phase_f.py --postgres   # exige ELFIS_PERFORMANCE_DATABASE_URL

Refuse les URL de production sauf ELFIS_PERFORMANCE_ALLOW_REMOTE=true.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", default=True)
    parser.add_argument("--concurrency", action="store_true")
    parser.add_argument("--postgres", action="store_true")
    parser.add_argument("--soak", action="store_true", help="Non implémenté en V1 — skip")
    args = parser.parse_args()

    env = os.environ.copy()
    env.setdefault("ELFIS_ENVIRONMENT", "test")
    env.setdefault("APP_ENV", "test")
    env.setdefault("ELFIS_RATE_LIMIT_ENABLED", "false")
    env.setdefault("OPENAI_API_KEY", "")
    env.setdefault("STRIPE_SECRET_KEY", "")
    env.setdefault("BREVO_API_KEY", "")
    env["ELFIS_PERFORMANCE_TESTS_ENABLED"] = "true"

    db_url = env.get("ELFIS_PERFORMANCE_DATABASE_URL") or env.get("DATABASE_URL", "")
    if db_url:
        from tests.performance.helpers import refuse_production_url

        refuse_production_url(db_url)
        env["DATABASE_URL"] = db_url

    paths = [
        "tests/performance",
        "tests/concurrency/test_job_claiming.py",
        "tests/concurrency/test_event_claiming.py",
        "tests/concurrency/test_quota_atomicity.py",
        "tests/concurrency/test_accounting_validation_concurrency.py",
        "tests/concurrency/test_worker_recovery.py",
    ]
    if args.concurrency:
        env["ELFIS_CONCURRENCY_TESTS_ENABLED"] = "true"
        paths = ["tests/performance", "tests/concurrency"]

    if args.postgres:
        if not (env.get("ELFIS_PERFORMANCE_DATABASE_URL") or "").lower().startswith("postgres"):
            print("FATAL: --postgres exige ELFIS_PERFORMANCE_DATABASE_URL PostgreSQL")
            return 2
        env["ELFIS_CONCURRENCY_TESTS_ENABLED"] = "true"
        paths = ["tests/performance", "tests/concurrency"]

    if args.soak:
        print("INFO: soak V1 non exécuté (documenté dans le rapport Phase F)")

    cmd = [sys.executable, "-m", "pytest", *paths, "-q", "--tb=line", "-p", "no:warnings"]
    print(">>", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(BACKEND_DIR), env=env)


if __name__ == "__main__":
    raise SystemExit(main())
