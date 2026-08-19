#!/usr/bin/env python
"""Valide la configuration production sans démarrer le serveur HTTP.

Usage:
  ELFIS_ENVIRONMENT=production python scripts/production/validate_production_config.py

Ne charge aucun secret depuis le dépôt. Lit uniquement l'environnement courant.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))


def main() -> int:
    from app.security.security_config import environment_name, is_production
    from app.security.security_startup import validate_runtime_configuration

    env = environment_name()
    issues = validate_runtime_configuration()
    fatals = [i for i in issues if i.level == "fatal"]
    payload = {
        "environment": env,
        "is_production": is_production(),
        "ok": not fatals,
        "issues": [{"level": i.level, "code": i.code, "message": i.message} for i in issues],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if fatals and is_production():
        print("FATAL: configuration production invalide", file=sys.stderr)
        return 1
    if fatals:
        print("WARN: fatals détectés hors production (simulation)", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
