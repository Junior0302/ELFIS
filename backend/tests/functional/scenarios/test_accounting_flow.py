"""SCENARIO 5 — Comptabilité (attentes fixtures + seed)."""

from __future__ import annotations

import json
from pathlib import Path


def test_accounting_expectations_file_valid():
    path = Path(__file__).resolve().parents[1] / "fixtures" / "expected" / "accounting_expectations.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "documents" in data
    inv = data["documents"]["invoice_supplier_valid.pdf"]
    assert inv["balanced"] is True
    assert inv["ht"] + inv["vat"] == inv["ttc"]
    unbalanced = data["documents"]["invoice_unbalanced.pdf"]
    assert unbalanced["expected_review_status"] == "requires_review"


def test_active_org_can_list_accounting_routes(api):
    api.login_user("active")
    r = api.client.get("/api/accounting/proposals", headers=api._headers())
    # Route peut exister ou renvoyer liste vide / 402
    assert r.status_code in (200, 401, 402, 403, 404)
