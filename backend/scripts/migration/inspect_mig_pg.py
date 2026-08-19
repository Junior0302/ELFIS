"""Inspect + certify Migration Center stage2 on PostgreSQL staging."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from tests.concurrency.postgres_helpers import (  # noqa: E402
    ensure_postgres_test_env,
    postgres_url,
)


def main() -> None:
    os.environ["ELFIS_POSTGRES_TESTS_ENABLED"] = "true"
    ensure_postgres_test_env()
    os.environ["ELFIS_ENVIRONMENT"] = "staging"
    os.environ["APP_ENV"] = "staging"
    os.environ["ELFIS_RC1_ALLOW_MANAGED_HOST"] = "true"

    from scripts.rc1.safety import assert_safe_postgres_url, assert_safe_rc1_environment

    url = postgres_url()
    assert_safe_rc1_environment()
    assert_safe_postgres_url(url)
    eng = create_engine(url, pool_pre_ping=True, connect_args={"prepare_threshold": None})
    with eng.connect() as c:
        v = c.execute(text("SHOW server_version")).scalar()
        tables = [
            r[0]
            for r in c.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name LIKE 'elfis_migration%' "
                    "ORDER BY 1"
                )
            ).fetchall()
        ]
        cols = []
        if "elfis_migration_sessions" in tables:
            cols = [
                r[0]
                for r in c.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema='public' AND table_name='elfis_migration_sessions' "
                        "ORDER BY ordinal_position"
                    )
                ).fetchall()
            ]
    print(json.dumps({"pg_version": v, "tables": tables, "session_cols": cols}, indent=2))


if __name__ == "__main__":
    main()
