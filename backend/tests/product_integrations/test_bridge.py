"""Tests product integrations / bridge RC2.5.5."""

from __future__ import annotations

from app.product_integrations.comptapilot.mapper import ElfisToComptaPilotDocumentMapper
from app.product_integrations.registry import (
    NoopDocumentBridge,
    get_bridge_registry,
    reset_bridge_registry_for_tests,
)
from app.product_integrations.service import build_idempotency_key
from app.product_integrations.types import PACKAGE_SCHEMA_V1, PRODUCT_COMPTAPILOT


def test_bridge_registry_noop_and_comptapilot():
    reset_bridge_registry_for_tests()
    reg = get_bridge_registry()
    keys = {b["product_key"] for b in reg.list_public()}
    assert "noop" in keys
    assert "comptapilot" in keys


def test_noop_deliver():
    bridge = NoopDocumentBridge()
    pkg = {
        "package_schema": PACKAGE_SCHEMA_V1,
        "organization_id": 1,
        "extraction": {"result_id": "e1"},
        "validation": {"result_id": "v1", "status": "valid"},
    }
    receipt = bridge.deliver(pkg, "idem-1")
    assert receipt.status == "delivered"
    assert receipt.external_reference


def test_comptapilot_disabled_by_default(monkeypatch):
    from app.config import settings
    from app.product_integrations.comptapilot.bridge import ComptaPilotDocumentBridge

    monkeypatch.setattr(settings, "comptapilot_document_publish_enabled", False)
    monkeypatch.setattr(settings, "comptapilot_document_bridge_mode", "disabled")
    bridge = ComptaPilotDocumentBridge()
    pkg = {
        "package_schema": PACKAGE_SCHEMA_V1,
        "organization_id": 1,
        "extraction": {"result_id": "e1", "confirmed": True, "status": "confirmed"},
        "validation": {"result_id": "v1", "status": "valid"},
    }
    receipt = bridge.deliver(pkg, "idem-cp-1")
    assert receipt.status == "blocked"
    assert receipt.error_code in ("comptapilot_publish_disabled", "comptapilot_bridge_disabled")


def test_mapper_no_accounting_keys():
    mapper = ElfisToComptaPilotDocumentMapper()
    out = mapper.map_transport(
        {
            "organization_id": 1,
            "document": {"id": "d1"},
            "extraction": {
                "fields": {
                    "invoice_number": "F-1",
                    "total_amount": "120",
                    "general_account": "401",
                }
            },
            "validation": {"result_id": "v1", "status": "valid", "issue_codes": []},
        }
    )
    assert "fields" in out
    assert "invoice_number" in out["fields"]
    assert "accounting_entries" not in out
    assert "journal" not in out
    assert "debit" not in out
    assert "credit" not in out
    # transport may copy total_amount but never invent accounts
    assert "401" not in str(out.get("fields", {}).get("general_account", ""))


def test_idempotency_key_deterministic():
    a = build_idempotency_key(
        product_key=PRODUCT_COMPTAPILOT,
        organization_id=1,
        document_version_id="v1",
        extraction_result_id="e1",
        business_validation_id="b1",
        package_schema_version="1",
    )
    b = build_idempotency_key(
        product_key=PRODUCT_COMPTAPILOT,
        organization_id=1,
        document_version_id="v1",
        extraction_result_id="e1",
        business_validation_id="b1",
        package_schema_version="1",
    )
    c = build_idempotency_key(
        product_key=PRODUCT_COMPTAPILOT,
        organization_id=2,
        document_version_id="v1",
        extraction_result_id="e1",
        business_validation_id="b1",
        package_schema_version="1",
    )
    assert a == b
    assert a != c


def test_comptapilot_health_not_failure_when_disabled(monkeypatch):
    from app.config import settings
    from app.product_integrations.comptapilot.bridge import ComptaPilotDocumentBridge

    monkeypatch.setattr(settings, "product_document_bridge_enabled", False)
    monkeypatch.setattr(settings, "comptapilot_document_publish_enabled", False)
    h = ComptaPilotDocumentBridge().health_check()
    assert h["status"] == "healthy"
    assert h["accounting_writes"] is False
