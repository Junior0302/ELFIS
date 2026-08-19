#!/usr/bin/env python
"""Smoke test SalesPilot — lecture seule (sauf sync intelligence optionnelle).

Usage (depuis backend/) :
  python -m scripts.smoke_salespilot
  python -m scripts.smoke_salespilot --base-url http://127.0.0.1:8000 --token $ELFIS_SMOKE_TOKEN

Exit code ≠ 0 si une route critique échoue.
Ne crée / ne modifie pas de données (GET only), sauf --allow-sync.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any


CRITICAL_GETS: list[tuple[str, str]] = [
    ("health", "/api/health"),
    ("dashboard", "/api/sales/dashboard"),
    ("leads", "/api/sales/leads?page=1&page_size=5"),
    ("companies", "/api/sales/companies?page=1&page_size=5"),
    ("contacts", "/api/sales/people?page=1&page_size=5"),
    ("pipeline", "/api/sales/pipeline"),
    ("intelligence", "/api/sales/intelligence"),
    ("proposals", "/api/sales/proposals?page=1&page_size=5"),
    ("calendar", "/api/sales/ops/calendar?from_date=2026-01-01&to_date=2026-12-31"),
    ("journal", "/api/sales/ops/journal"),
    ("team", "/api/sales/collab/team-dashboard"),
    ("tasks", "/api/sales/tasks?page=1&page_size=5"),
    ("activities", "/api/sales/activities?page=1&page_size=5"),
]


def _request(
    method: str,
    url: str,
    *,
    token: str = "",
    timeout: float = 20.0,
) -> tuple[int, Any, float]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method=method)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            elapsed = time.perf_counter() - started
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {"raw": body[:240]}
            return int(resp.status), data, elapsed
    except urllib.error.HTTPError as exc:
        elapsed = time.perf_counter() - started
        body = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {"raw": body[:240]}
        return int(exc.code), data, elapsed
    except Exception as exc:  # noqa: BLE001
        elapsed = time.perf_counter() - started
        return 0, {"error": str(exc)}, elapsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("ELFIS_API_BASE", "http://127.0.0.1:8000"))
    parser.add_argument("--token", default=os.getenv("ELFIS_SMOKE_TOKEN", ""))
    parser.add_argument(
        "--allow-sync",
        action="store_true",
        help="POST /api/sales/intelligence/sync (modifie insights)",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    rows: list[dict[str, Any]] = []
    failures: list[str] = []

    for name, path in CRITICAL_GETS:
        needs_auth = name != "health"
        if needs_auth and not args.token:
            rows.append(
                {
                    "name": name,
                    "path": path,
                    "status": "SKIP",
                    "reason": "no token",
                }
            )
            continue
        code, data, elapsed = _request("GET", base + path, token=args.token if needs_auth else "")
        ok = code == 200
        # Auth endpoints without token → 401 expected if skipped above
        if needs_auth and code in (401, 403):
            ok = False
            failures.append(f"{name}:{code}")
        elif not ok and name == "health":
            failures.append(f"{name}:{code}")
        elif not ok:
            failures.append(f"{name}:{code}")
        rows.append(
            {
                "name": name,
                "path": path,
                "status_code": code,
                "ms": round(elapsed * 1000),
                "ok": ok,
                "request_id": (data or {}).get("request_id") if isinstance(data, dict) else None,
            }
        )

    # conversion-state: best-effort on first proposal if list available
    if args.token:
        code, data, _ = _request("GET", base + "/api/sales/proposals?page=1&page_size=1", token=args.token)
        if code == 200 and isinstance(data, dict):
            items = data.get("items") or data.get("results") or []
            if items:
                pid = items[0].get("id")
                ccode, _, celapsed = _request(
                    "GET",
                    f"{base}/api/sales/proposals/{pid}/conversion-state",
                    token=args.token,
                )
                ok = ccode == 200
                if not ok:
                    failures.append(f"conversion_state:{ccode}")
                rows.append(
                    {
                        "name": "conversion_state",
                        "path": f"/api/sales/proposals/{pid}/conversion-state",
                        "status_code": ccode,
                        "ms": round(celapsed * 1000),
                        "ok": ok,
                    }
                )

        if args.allow_sync:
            scode, _, selapsed = _request(
                "POST",
                base + "/api/sales/intelligence/sync",
                token=args.token,
            )
            ok = scode == 200
            if not ok:
                failures.append(f"intelligence_sync:{scode}")
            rows.append(
                {
                    "name": "intelligence_sync",
                    "path": "/api/sales/intelligence/sync",
                    "status_code": scode,
                    "ms": round(selapsed * 1000),
                    "ok": ok,
                }
            )

    print("=== SalesPilot smoke ===")
    print(f"base={base}")
    for r in rows:
        if r.get("status") == "SKIP":
            print(f"  SKIP {r['name']} ({r['reason']})")
            continue
        mark = "OK" if r.get("ok") else "FAIL"
        print(f"  [{mark}] {r['name']} {r.get('status_code')} {r.get('ms')}ms {r['path']}")

    skipped_auth = [r for r in rows if r.get("status") == "SKIP"]
    if skipped_auth and not args.token:
        print("NOTE: fournir --token ou ELFIS_SMOKE_TOKEN pour les routes authentifiées")

    # Health is always required
    health = next((r for r in rows if r.get("name") == "health"), None)
    if not health or not health.get("ok"):
        print("FAIL: health critique")
        return 1

    if failures:
        print("FAIL:", ", ".join(failures))
        return 1

    if skipped_auth:
        print("OK health ; routes auth non testées (pas de token)")
        return 0

    print("OK smoke SalesPilot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
