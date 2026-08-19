"""Tests contrat package ELFIS → transport ComptaPilot."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.product_integrations.comptapilot.mapper import ElfisToComptaPilotDocumentMapper
from app.product_integrations.types import PACKAGE_SCHEMA_V1


FIXTURE_V1 = {
    "package_schema": PACKAGE_SCHEMA_V1,
    "package_id": "pkg-1",
    "organization_id": 42,
    "document": {"id": "doc-1", "version_id": "ver-1", "effective_type": "supplier_invoice"},
    "classification": {"classification_id": "cls-1", "effective_type": "supplier_invoice"},
    "extraction": {
        "result_id": "ext-1",
        "schema_key": "invoice_basic_v1",
        "schema_version": "1",
        "status": "confirmed",
        "confirmed": True,
        "fields": {
            "invoice_number": {"normalized_value": "F-2026-001"},
            "issue_date": {"normalized_value": "2026-01-15"},
            "due_date": {"normalized_value": "2026-02-15"},
            "supplier_name": {"normalized_value": "ACME"},
            "currency": {"normalized_value": "EUR"},
            "subtotal": {"normalized_value": "100.00"},
            "tax_amount": {"normalized_value": "20.00"},
            "total_amount": {"normalized_value": "120.00"},
            "tax_rate": {"normalized_value": "20"},
        },
    },
    "validation": {"result_id": "bv-1", "status": "valid", "issue_codes": []},
    "provenance": {"ocr_result_id": "ocr-1", "provider_versions": {"extraction_provider": "rules"}},
}


def test_contract_transport_types_and_no_accounting():
    out = ElfisToComptaPilotDocumentMapper().map_transport(FIXTURE_V1)
    assert out["schema"] == "comptapilot_document_import_transport_v1"
    assert out["organization_id"] == 42
    assert out["fields"]["currency"] == "EUR"
    assert out["fields"]["invoice_number"] == "F-2026-001"
    # Decimal-compatible strings
    Decimal(str(out["fields"]["total_amount"]))
    assert "2026-01-15" == out["fields"]["issue_date"]
    forbidden = ("debit", "credit", "journal", "general_account", "accounting_entries", "compte")
    blob = str(out).lower()
    for f in forbidden:
        assert f not in out.get("fields", {})
        assert f"'{f}'" not in blob or f not in ("debit", "credit")


def test_contract_unknown_fields_ignored_in_transport():
    pkg = dict(FIXTURE_V1)
    fields = dict(pkg["extraction"]["fields"])
    fields["weird_future_field"] = {"normalized_value": "x"}
    fields["general_account"] = {"normalized_value": "401"}
    pkg["extraction"] = dict(pkg["extraction"], fields=fields)
    out = ElfisToComptaPilotDocumentMapper().map_transport(pkg)
    assert "weird_future_field" not in out["fields"]
    assert "general_account" not in out["fields"]


def test_contract_nullability():
    pkg = dict(FIXTURE_V1)
    pkg["extraction"] = dict(pkg["extraction"], fields={})
    out = ElfisToComptaPilotDocumentMapper().map_transport(pkg)
    assert out["fields"] == {}


def test_dry_run_not_published(monkeypatch):
    from app.config import settings
    from app.product_integrations.comptapilot.bridge import ComptaPilotDocumentBridge
    from app.product_integrations.registry import reset_bridge_registry_for_tests

    monkeypatch.setattr(settings, "product_document_bridge_enabled", True)
    monkeypatch.setattr(settings, "comptapilot_document_bridge_mode", "dry_run")
    monkeypatch.setattr(settings, "comptapilot_document_publish_enabled", False)
    reset_bridge_registry_for_tests()
    bridge = ComptaPilotDocumentBridge()
    receipt = bridge.deliver(FIXTURE_V1, "idem-dry-1")
    assert receipt.status == "validated_not_delivered"
    assert receipt.external_reference
    assert "Dry-run" in (receipt.message_sanitized or "")


def test_disabled_mode_blocks(monkeypatch):
    from app.config import settings
    from app.product_integrations.comptapilot.bridge import ComptaPilotDocumentBridge

    monkeypatch.setattr(settings, "comptapilot_document_bridge_mode", "disabled")
    monkeypatch.setattr(settings, "comptapilot_document_publish_enabled", False)
    receipt = ComptaPilotDocumentBridge().deliver(FIXTURE_V1, "idem-off")
    assert receipt.status == "blocked"
