#!/usr/bin/env python
"""Smoke tests staging / production read-only.

Staging :
  python scripts/production/smoke_test.py --environment staging --base-url https://staging… --allow-staging

Production read-only :
  python scripts/production/smoke_test.py --base-url https://api… --allow-production-readonly

Aucun secret codé en dur. Staging : pas d'appel live Stripe/OpenAI/SMTP.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


def _get(url: str, *, timeout: float = 15.0, headers: dict[str, str] | None = None) -> tuple[int, Any]:
    req = urllib.request.Request(url, headers=headers or {"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {"raw": body[:200]}
            return int(resp.status), data
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {"raw": body[:200]}
        return int(exc.code), data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True, help="URL API (sans slash final)")
    parser.add_argument(
        "--environment",
        choices=("staging", "production", "test"),
        default="staging",
        help="Environnement cible déclaré",
    )
    parser.add_argument(
        "--allow-staging",
        action="store_true",
        help="Autorise le smoke staging (requis si --environment staging)",
    )
    parser.add_argument(
        "--allow-production-readonly",
        action="store_true",
        help="Autorise un smoke strictement read-only contre une URL production",
    )
    parser.add_argument("--token", default=os.getenv("ELFIS_SMOKE_TOKEN", ""), help="Bearer optionnel")
    parser.add_argument(
        "--production",
        action="store_true",
        help="Alias : cible production (exige --allow-production-readonly)",
    )
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    low = base.lower()
    looks_prod = (
        args.production
        or args.environment == "production"
        or any(x in low for x in ("prod.", "production", "api.elfis", "elfis-core.com"))
    )

    if args.environment == "staging" and not args.allow_staging and not looks_prod:
        # Exiger allow-staging pour toute cible staging déclarée
        print("REFUS: --environment staging exige --allow-staging")
        return 2

    if looks_prod and not args.allow_production_readonly:
        print("REFUS: cible production sans --allow-production-readonly")
        return 2

    results: dict[str, Any] = {
        "base_url": base,
        "environment": args.environment,
        "mode": "production_readonly" if looks_prod else "staging",
    }
    failures: list[str] = []

    for path in ("/api/health/live", "/api/health/ready", "/api/health"):
        code, data = _get(base + path)
        results[path] = {"status_code": code, "body": data}
        if code >= 500:
            failures.append(path)

    if looks_prod:
        results["mutations"] = "forbidden"
    else:
        if args.token:
            code, _data = _get(
                base + "/api/billing/plans",
                headers={"Authorization": f"Bearer {args.token}", "Accept": "application/json"},
            )
            results["/api/billing/plans"] = {"status_code": code}
            if code >= 500:
                failures.append("plans")
        results["note"] = (
            "Staging smoke V1 = health (+ plans si token). "
            "Upload/archive/validation : parcours manuel checklist RC1."
        )

    print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    if failures:
        print("FAIL:", ", ".join(failures), file=sys.stderr)
        return 1
    print("OK smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
