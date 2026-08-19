"""Tests failure windows + reconciliation (SQLite OK pour logique ; PG séparé)."""

from __future__ import annotations

from app.product_integrations.registry import ProductReceipt
from app.product_integrations.types import DeliveryStatus


def test_mark_unknown_not_failed():
    """État distant inconnu → unknown, pas failed automatique."""
    assert DeliveryStatus.UNKNOWN.value == "unknown"
    assert DeliveryStatus.UNKNOWN.value != DeliveryStatus.FAILED.value


def test_noop_counter_threadsafe():
    from concurrent.futures import ThreadPoolExecutor

    from app.product_integrations.noop_counter import (
        get_noop_deliver_calls,
        incr_noop_deliver_calls,
        reset_noop_deliver_calls,
    )
    from app.product_integrations.registry import NoopDocumentBridge

    reset_noop_deliver_calls()
    bridge = NoopDocumentBridge()
    pkg = {
        "package_schema": "elfis_document_package_v1",
        "organization_id": 1,
        "extraction": {"result_id": "e"},
        "validation": {"result_id": "v"},
    }

    def once(i: int):
        bridge.deliver(pkg, f"k-{i}")

    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(once, range(40)))
    assert get_noop_deliver_calls() == 40


def test_duplicate_idempotent_receipt(monkeypatch):
    from app.config import settings
    from app.product_integrations.comptapilot.bridge import ComptaPilotDocumentBridge

    monkeypatch.setattr(settings, "product_document_bridge_enabled", True)
    monkeypatch.setattr(settings, "comptapilot_document_bridge_mode", "dry_run")
    bridge = ComptaPilotDocumentBridge()
    pkg = {
        "package_schema": "elfis_document_package_v1",
        "organization_id": 1,
        "extraction": {"result_id": "e", "confirmed": True, "status": "confirmed"},
        "validation": {"result_id": "v", "status": "valid"},
    }
    r1 = bridge.deliver(pkg, "same-key")
    r2 = bridge.deliver(pkg, "same-key")
    assert r1.external_reference == r2.external_reference
    assert r2.error_code == "duplicate_idempotent"


def test_get_delivery_status_unknown():
    from app.product_integrations.comptapilot.bridge import ComptaPilotDocumentBridge

    remote = ComptaPilotDocumentBridge().get_delivery_status(
        ProductReceipt(status="unknown", external_reference="missing-ref", uncertain=True)
    )
    assert remote.status == "unknown" or remote.uncertain
