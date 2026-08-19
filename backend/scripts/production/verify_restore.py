#!/usr/bin/env python
"""Garde-fou restauration — refuse les cibles production destructives.

Ce script ne restaure PAS automatiquement. Il valide les arguments et
rappelle la procédure du runbook database-restore.md.
"""

from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-database-url", required=True)
    parser.add_argument("--backup-path", required=True)
    parser.add_argument(
        "--i-understand-destructive",
        action="store_true",
        help="Requis pour toute URL non clairement test/staging/recette",
    )
    args = parser.parse_args()

    url = (args.target_database_url or "").lower()
    dangerous = any(x in url for x in ("prod", "production", "live"))
    safe_markers = any(x in url for x in ("test", "staging", "stage", "recette", "functional", "tmp", "temp"))

    if dangerous and not safe_markers:
        print(
            json.dumps(
                {
                    "ok": False,
                    "refused": True,
                    "reason": "URL cible ressemble à la production — restauration automatique interdite",
                }
            )
        )
        return 2

    if not safe_markers and not args.i_understand_destructive:
        print(
            json.dumps(
                {
                    "ok": False,
                    "refused": True,
                    "reason": "Cible ambiguë — ajouter --i-understand-destructive ou utiliser une base test/staging",
                }
            )
        )
        return 2

    print(
        json.dumps(
            {
                "ok": True,
                "executed": False,
                "backup_path": args.backup_path,
                "message": "Arguments acceptés. Exécuter manuellement pg_restore selon docs/runbooks/database-restore.md",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
