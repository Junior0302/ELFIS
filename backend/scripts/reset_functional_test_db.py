#!/usr/bin/env python
"""Réinitialise la base de recette fonctionnelle et réinjecte les fixtures.

Usage (PowerShell) :
  cd backend
  $env:ELFIS_ENVIRONMENT='test'
  $env:DATABASE_URL='sqlite:///./elfis_functional_recette.db'
  python scripts/reset_functional_test_db.py

Refuse production et bases dont le nom ne contient pas test/functional/recette
(sauf SQLite).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset DB recette fonctionnelle ELFIS")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", "sqlite:///./elfis_functional_recette.db"),
    )
    parser.add_argument(
        "--environment",
        default=os.environ.get("ELFIS_ENVIRONMENT") or os.environ.get("APP_ENV") or "test",
    )
    parser.add_argument("--json", action="store_true", help="Sortie JSON")
    args = parser.parse_args()

    os.environ["DATABASE_URL"] = args.database_url
    os.environ["APP_ENV"] = args.environment
    os.environ["ELFIS_ENVIRONMENT"] = args.environment
    os.environ.setdefault("PLATFORM_ADMIN_EMAILS", "platform.admin@test.elfis.local")

    from app.config import settings

    settings.database_url = args.database_url
    settings.app_env = args.environment
    settings.elfis_environment = args.environment

    from tests.functional.seed import assert_safe_environment, seed_functional_fixtures

    try:
        assert_safe_environment(database_url=args.database_url, environment=args.environment)
    except RuntimeError as exc:
        print(f"ERREUR: {exc}", file=sys.stderr)
        return 2

    # Recréer engine lié à l'URL de recette
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import Base, init_db

    connect_args = {"check_same_thread": False} if args.database_url.startswith("sqlite") else {}
    engine = create_engine(args.database_url, connect_args=connect_args)
    # Rébind SessionLocal / metadata
    import app.database as database_module

    database_module.engine = engine
    database_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    settings.database_url = args.database_url

    Base.metadata.create_all(bind=engine)
    init_db()

    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()
    try:
        summary = seed_functional_fixtures(db)
    finally:
        db.close()

    # Générer documents
    try:
        from tests.functional.fixtures.generate_documents import ensure_document_fixtures

        docs = ensure_document_fixtures()
        summary["documents_generated"] = len(docs)
    except Exception as exc:
        summary["documents_generated"] = 0
        summary["documents_error"] = str(exc)

    if args.json:
        # Ne pas afficher le mot de passe en CI verbose si souhaité — utile en recette locale
        print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    else:
        print("=== ELFIS Functional Recette — reset OK ===")
        print(f"Environment : {args.environment}")
        print(f"Database    : {args.database_url}")
        print(f"Organisations: {len(summary.get('organizations', {}))}")
        print(f"Utilisateurs : {len(summary.get('users', {}))}")
        print(f"Documents    : {summary.get('documents_generated', 0)}")
        print(f"Password     : {summary.get('password')}")
        print(summary.get("note_auth"))
        print("Comptes clés :")
        for row in summary.get("scenarios", [])[:8]:
            print(f"  - {row['email']} / {row['org_key']} / {row['subscription']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
