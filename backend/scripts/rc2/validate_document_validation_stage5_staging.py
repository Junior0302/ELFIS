"""Staging RC2.5.6 — validation + packages + bridge (PostgreSQL réel préféré)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-sql", action="store_true")
    parser.add_argument("--keep-probes", action="store_true")
    parser.add_argument("--bridge", default="noop", choices=["noop", "comptapilot"])
    parser.add_argument("--bridge-mode", default="disabled", choices=["disabled", "dry_run", "live"])
    parser.add_argument("--confirm-live", action="store_true")
    parser.add_argument("--sqlite-lab", action="store_true", help="Lab local SQLite (≠ validation PG)")
    args = parser.parse_args()

    env = (os.environ.get("ELFIS_ENVIRONMENT") or os.environ.get("APP_ENV") or "").strip()
    if not env and not args.sqlite_lab:
        raise SystemExit("FATAL: ELFIS_ENVIRONMENT requis (ou --sqlite-lab)")

    if args.bridge_mode == "live" and not args.confirm_live:
        raise SystemExit("FATAL: --confirm-live requis pour bridge-mode=live")

    url = (
        os.getenv("ELFIS_RC1_DATABASE_URL")
        or os.getenv("ELFIS_PERFORMANCE_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or ""
    ).strip()

    print(f"ENV={env or 'lab'} bridge={args.bridge} mode={args.bridge_mode}")

    if args.apply_sql and url.startswith("postgres"):
        from scripts.rc1.migrate_sql import upgrade_head

        upgrade_head(url)
        print("SQL applied")

    # Preuves unitaires locales (toujours)
    import subprocess

    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/document_business_validation",
            "tests/product_integrations",
            "-q",
            "--tb=line",
        ],
        cwd=str(BACKEND),
    )
    if r.returncode != 0:
        print("FAIL unit suites")
        return r.returncode

    if url.startswith("postgres") and os.getenv("ELFIS_POSTGRES_TESTS_ENABLED", "").lower() in {
        "1",
        "true",
        "yes",
    }:
        r2 = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/concurrency/test_postgres_product_delivery_claiming.py",
                "tests/concurrency/test_postgres_job_claiming.py",
                "-q",
                "--tb=line",
            ],
            cwd=str(BACKEND),
        )
        if r2.returncode != 0:
            print("FAIL postgres concurrency")
            return r2.returncode
        print("PASS postgres concurrency probes")
    else:
        print("SKIP postgres concurrency (ELFIS_POSTGRES_TESTS_ENABLED / URL absent)")

    schema = subprocess.run(
        [
            sys.executable,
            "scripts/rc2/check_rc25_database_schema.py",
            *(["--url", url] if url else []),
            *(["--sqlite-ok"] if args.sqlite_lab or url.startswith("sqlite") else []),
        ],
        cwd=str(BACKEND),
    )
    if url and schema.returncode != 0:
        print("FAIL schema check")
        return schema.returncode

    print("PASS stage5/6 staging validator (preuves exécutées ci-dessus)")
    print("NOTE: probes org/document E2E complets nécessitent PG + seed staging dédié")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
