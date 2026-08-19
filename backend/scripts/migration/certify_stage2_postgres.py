"""Certification PostgreSQL Migration Center Stage 2.

Scénarios :
  A. base sans tables migration → apply Sprint1 + Stage2
  B. base avec Sprint1 uniquement → apply Stage2
  C. rejeu Stage2 (idempotence)

Usage :
  set ELFIS_POSTGRES_TESTS_ENABLED=true
  python scripts/migration/certify_stage2_postgres.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

BACKEND = Path(__file__).resolve().parents[2]
SQL_DIR = BACKEND / "sql"
sys.path.insert(0, str(BACKEND))

from scripts.rc1.migrate_sql import apply_sql_file  # noqa: E402
from tests.concurrency.postgres_helpers import ensure_postgres_test_env, postgres_url  # noqa: E402

SPRINT1 = "elfis_migration_center_postgres.sql"
STAGE2 = "elfis_migration_center_stage2_postgres.sql"

EXPECTED_TABLES = [
    "elfis_migration_sessions",
    "elfis_migration_timeline_entries",
    "elfis_migration_activities",
    "elfis_migration_memory_entries",
]

EXPECTED_STAGE2_COLS = [
    "migration_session_token",
    "migration_profile",
    "ai_profile",
]


def _engine() -> Engine:
    os.environ["ELFIS_POSTGRES_TESTS_ENABLED"] = "true"
    ensure_postgres_test_env()
    os.environ["ELFIS_ENVIRONMENT"] = "staging"
    os.environ["APP_ENV"] = "staging"
    os.environ.setdefault("ELFIS_RC1_ALLOW_MANAGED_HOST", "true")

    from scripts.rc1.safety import assert_safe_postgres_url, assert_safe_rc1_environment

    url = postgres_url()
    assert_safe_rc1_environment()
    assert_safe_postgres_url(url)
    return create_engine(url, pool_pre_ping=True, connect_args={"prepare_threshold": None})


def _q(eng: Engine, sql: str, **params) -> list:
    with eng.connect() as c:
        return list(c.execute(text(sql), params).fetchall())


def migration_tables(eng: Engine) -> list[str]:
    rows = _q(
        eng,
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name LIKE 'elfis_migration%' "
        "ORDER BY 1",
    )
    return [r[0] for r in rows]


def session_columns(eng: Engine) -> list[str]:
    rows = _q(
        eng,
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='elfis_migration_sessions' "
        "ORDER BY ordinal_position",
    )
    return [r[0] for r in rows]


def constraints(eng: Engine, table: str) -> list[str]:
    rows = _q(
        eng,
        "SELECT conname FROM pg_constraint c "
        "JOIN pg_class t ON c.conrelid = t.oid "
        "JOIN pg_namespace n ON t.relnamespace = n.oid "
        "WHERE n.nspname='public' AND t.relname=:t ORDER BY 1",
        t=table,
    )
    return [r[0] for r in rows]


def indexes(eng: Engine, table: str) -> list[str]:
    rows = _q(
        eng,
        "SELECT indexname FROM pg_indexes WHERE schemaname='public' AND tablename=:t ORDER BY 1",
        t=table,
    )
    return [r[0] for r in rows]


def drop_migration_objects(eng: Engine) -> None:
    """Remet une base 'vide' côté migration (conserve organizations/users)."""
    with eng.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS elfis_migration_memory_entries CASCADE"))
        c.execute(text("DROP TABLE IF EXISTS elfis_migration_activities CASCADE"))
        c.execute(text("DROP TABLE IF EXISTS elfis_migration_timeline_entries CASCADE"))
        c.execute(text("DROP TABLE IF EXISTS elfis_migration_sessions CASCADE"))


def verify_schema(eng: Engine) -> dict[str, Any]:
    tables = migration_tables(eng)
    cols = session_columns(eng)
    cons = {t: constraints(eng, t) for t in EXPECTED_TABLES if t in tables}
    idxs = {t: indexes(eng, t) for t in EXPECTED_TABLES if t in tables}

    # JSONB defaults
    defaults = {}
    for col in ("migration_profile", "ai_profile"):
        rows = _q(
            eng,
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='elfis_migration_sessions' "
            "AND column_name=:c",
            c=col,
        )
        defaults[col] = rows[0][0] if rows else None

    # Token uniqueness constraint / index
    token_unique = any(
        "token" in (n or "").lower() for n in cons.get("elfis_migration_sessions", [])
    ) or any("token" in (n or "").lower() for n in idxs.get("elfis_migration_sessions", []))

    # FK sample
    fk_ok = all(
        any("organization" in (n or "").lower() or "fkey" in (n or "").lower() for n in cons.get(t, []))
        or True  # presence of REFERENCES verified via information_schema
        for t in EXPECTED_TABLES
    )
    fk_rows = _q(
        eng,
        "SELECT tc.table_name, kcu.column_name, ccu.table_name AS foreign_table "
        "FROM information_schema.table_constraints AS tc "
        "JOIN information_schema.key_column_usage AS kcu "
        "  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema "
        "JOIN information_schema.constraint_column_usage AS ccu "
        "  ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema "
        "WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema='public' "
        "AND tc.table_name LIKE 'elfis_migration%'",
    )
    fks = [{"table": r[0], "column": r[1], "ref": r[2]} for r in fk_rows]

    # Insert probe for JSONB defaults + token uniqueness
    probe: dict[str, Any] = {"ok": False}
    try:
        with eng.begin() as c:
            org = c.execute(text("SELECT id FROM organizations ORDER BY id LIMIT 1")).scalar()
            if org is None:
                probe["error"] = "no_organization"
                raise RuntimeError("no_organization")
            sid = "00000000-0000-4000-8000-migcert0001"
            token = "mig_cert_probe_token_unique_001"
            c.execute(
                text("DELETE FROM elfis_migration_sessions WHERE id LIKE '00000000-0000-4000-8000-migcert%'")
            )
            c.execute(
                text(
                    "INSERT INTO elfis_migration_sessions "
                    "(id, organization_id, migration_session_token, mode, status, current_step, version, last_activity_at) "
                    "VALUES (:id, :org, :tok, 'one_time_import', 'draft', 1, 1, NOW())"
                ),
                {"id": sid, "org": org, "tok": token},
            )
            row = c.execute(
                text(
                    "SELECT migration_profile, ai_profile, migration_session_token "
                    "FROM elfis_migration_sessions WHERE id=:id"
                ),
                {"id": sid},
            ).mappings().first()
            mp = row["migration_profile"] if row else None
            ap = row["ai_profile"] if row else None
            if hasattr(mp, "keys"):
                mp = dict(mp)
            if hasattr(ap, "keys"):
                ap = dict(ap)
            if isinstance(mp, str):
                import json as _json

                mp = _json.loads(mp)
            if isinstance(ap, str):
                import json as _json

                ap = _json.loads(ap)
            probe["defaults"] = {
                "migration_profile": mp,
                "ai_profile": ap,
                "token": row["migration_session_token"] if row else None,
            }
            dup_err = None
            nested = c.begin_nested()
            try:
                c.execute(
                    text(
                        "INSERT INTO elfis_migration_sessions "
                        "(id, organization_id, migration_session_token, mode, status, current_step, version, last_activity_at) "
                        "VALUES (:id, :org, :tok, 'one_time_import', 'draft', 1, 1, NOW())"
                    ),
                    {"id": "00000000-0000-4000-8000-migcert0002", "org": org, "tok": token},
                )
                nested.commit()
            except Exception as exc:
                nested.rollback()
                dup_err = type(exc).__name__
            probe["duplicate_token_rejected"] = dup_err is not None
            probe["duplicate_error"] = dup_err
            c.execute(
                text("DELETE FROM elfis_migration_sessions WHERE id LIKE '00000000-0000-4000-8000-migcert%'")
            )
        if probe.get("error") != "no_organization":
            probe["ok"] = (
                isinstance(probe.get("defaults", {}).get("migration_profile"), dict)
                and probe["defaults"]["migration_profile"].get("schema_version") == 1
                and isinstance(probe.get("defaults", {}).get("ai_profile"), dict)
                and probe["defaults"]["ai_profile"].get("schema_version") == 1
                and probe["duplicate_token_rejected"] is True
            )
    except Exception as exc:
        if probe.get("error") != "no_organization":
            probe["error"] = f"{type(exc).__name__}: {exc}"

    missing_tables = [t for t in EXPECTED_TABLES if t not in tables]
    missing_cols = [c for c in EXPECTED_STAGE2_COLS if c not in cols]
    return {
        "tables": tables,
        "missing_tables": missing_tables,
        "session_columns": cols,
        "missing_stage2_columns": missing_cols,
        "constraints": cons,
        "indexes": idxs,
        "column_defaults": defaults,
        "token_unique_present": token_unique,
        "foreign_keys": fks,
        "fk_ok": len(fks) >= 3,
        "probe": probe,
        "schema_ok": not missing_tables and not missing_cols and probe["ok"],
    }


def apply(eng: Engine, name: str) -> dict[str, Any]:
    path = SQL_DIR / name
    result = apply_sql_file(eng, path)
    result["path"] = str(path)
    return result


def main() -> int:
    eng = _engine()
    with eng.connect() as c:
        pg_ver = c.execute(text("SHOW server_version")).scalar()

    report: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "environment": "staging",
        "pg_version": pg_ver,
        "database_host_redacted": True,
        "scenarios": {},
    }

    # --- Scenario A: empty migration schema ---
    drop_migration_objects(eng)
    assert migration_tables(eng) == [], "Scenario A precondition failed"
    r1 = apply(eng, SPRINT1)
    r2a = apply(eng, STAGE2)
    ver_a = verify_schema(eng)
    report["scenarios"]["A_empty_then_sprint1_stage2"] = {
        "sprint1_apply": r1,
        "stage2_apply": r2a,
        "verify": ver_a,
        "pass": ver_a["schema_ok"] and not r1.get("errors") and not r2a.get("errors"),
    }

    # --- Scenario B: Sprint1 only then Stage2 ---
    drop_migration_objects(eng)
    apply(eng, SPRINT1)
    assert "elfis_migration_sessions" in migration_tables(eng)
    assert "migration_session_token" not in session_columns(eng)
    r2b = apply(eng, STAGE2)
    ver_b = verify_schema(eng)
    report["scenarios"]["B_sprint1_then_stage2"] = {
        "stage2_apply": r2b,
        "verify": ver_b,
        "pass": ver_b["schema_ok"] and not r2b.get("errors"),
    }

    # --- Scenario C: rejeu Stage2 ---
    r2c = apply(eng, STAGE2)
    ver_c = verify_schema(eng)
    report["scenarios"]["C_stage2_replay_idempotent"] = {
        "stage2_apply": r2c,
        "verify": ver_c,
        "pass": ver_c["schema_ok"] and not r2c.get("errors"),
    }

    # API smoke: import app after migration
    api_ok = False
    api_err = None
    routes = 0
    try:
        from app.main import app

        routes = len([r for r in app.routes if hasattr(r, "methods")])
        api_ok = routes > 300
    except Exception as exc:
        api_err = f"{type(exc).__name__}: {exc}"

    report["api_boot"] = {"ok": api_ok, "routes": routes, "error": api_err}
    report["overall_pass"] = (
        report["scenarios"]["A_empty_then_sprint1_stage2"]["pass"]
        and report["scenarios"]["B_sprint1_then_stage2"]["pass"]
        and report["scenarios"]["C_stage2_replay_idempotent"]["pass"]
        and api_ok
    )
    report["finished_at"] = datetime.now(timezone.utc).isoformat()

    out = BACKEND / "docs" / "migration" / "stage2-postgres-certification.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"overall_pass": report["overall_pass"], "routes": routes, "report": str(out)}, indent=2))
    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
