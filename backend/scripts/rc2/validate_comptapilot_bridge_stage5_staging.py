"""Staging bridge ComptaPilot — dry-run par défaut. Live = --confirm-live."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-mode", default="dry_run", choices=["disabled", "dry_run", "live"])
    parser.add_argument("--confirm-live", action="store_true")
    args = parser.parse_args()

    if args.bridge_mode == "live" and not args.confirm_live:
        raise SystemExit("FATAL: live nécessite --confirm-live")

    env = (os.environ.get("ELFIS_ENVIRONMENT") or "").strip().lower()
    if args.bridge_mode == "live" and env in {"production", "prod"}:
        raise SystemExit("FATAL: live interdit en production")

    from app.config import settings
    from app.product_integrations.comptapilot.bridge import ComptaPilotDocumentBridge
    from app.product_integrations.comptapilot.mapper import ElfisToComptaPilotDocumentMapper
    from app.product_integrations.types import PACKAGE_SCHEMA_V1

    settings.product_document_bridge_enabled = True
    settings.comptapilot_document_bridge_mode = args.bridge_mode
    settings.comptapilot_document_publish_enabled = args.bridge_mode == "live"

    pkg = {
        "package_schema": PACKAGE_SCHEMA_V1,
        "package_id": "probe-pkg",
        "organization_id": 1,
        "document": {"id": "probe-doc", "version_id": "probe-ver"},
        "extraction": {
            "result_id": "probe-ext",
            "confirmed": True,
            "status": "confirmed",
            "fields": {
                "invoice_number": {"normalized_value": "PROBE-1"},
                "currency": {"normalized_value": "EUR"},
                "total_amount": {"normalized_value": "10.00"},
            },
        },
        "validation": {"result_id": "probe-bv", "status": "valid", "issue_codes": []},
    }
    transport = ElfisToComptaPilotDocumentMapper().map_transport(pkg)
    assert "accounting_entries" not in transport
    assert "general_account" not in transport.get("fields", {})

    bridge = ComptaPilotDocumentBridge()
    receipt = bridge.deliver(pkg, "probe-idempotency-key")
    print("mode", args.bridge_mode, "receipt", receipt.status, "ref", receipt.external_reference)
    if args.bridge_mode == "dry_run":
        assert receipt.status == "validated_not_delivered"
        print("PASS dry-run — aucun import métier")
    elif args.bridge_mode == "disabled":
        assert receipt.status == "blocked"
        print("PASS disabled")
    else:
        print("PASS live probe (environnement non-prod + confirm)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
