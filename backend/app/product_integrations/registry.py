"""Registre bridges produit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.config import settings
from app.product_integrations.exceptions import ProductIntegrationValidationError
from app.product_integrations.noop_counter import incr_noop_deliver_calls
from app.product_integrations.types import (
    BRIDGE_MODE_DISABLED,
    BRIDGE_NOOP,
    PACKAGE_SCHEMA_V1,
)


@dataclass(frozen=True)
class ProductReceipt:
    status: str
    external_reference: str | None = None
    error_code: str | None = None
    retryable: bool = False
    message_sanitized: str | None = None
    uncertain: bool = False


class ProductDocumentBridge(Protocol):
    product_key: str
    bridge_version: str
    supported_package_schemas: frozenset[str]
    capabilities: frozenset[str]

    def validate_package(self, package: dict[str, Any]) -> None: ...

    def deliver(self, package: dict[str, Any], idempotency_key: str) -> ProductReceipt: ...

    def get_delivery_status(self, receipt: ProductReceipt) -> ProductReceipt: ...

    def health_check(self) -> dict[str, Any]: ...


class NoopDocumentBridge:
    product_key = BRIDGE_NOOP
    bridge_version = "1"
    supported_package_schemas = frozenset({PACKAGE_SCHEMA_V1})
    capabilities = frozenset({"deliver", "health", "get_delivery_status"})

    def validate_package(self, package: dict[str, Any]) -> None:
        if package.get("package_schema") != PACKAGE_SCHEMA_V1:
            raise ProductIntegrationValidationError("schema_unsupported", "Schéma package non supporté")

    def deliver(self, package: dict[str, Any], idempotency_key: str) -> ProductReceipt:
        self.validate_package(package)
        incr_noop_deliver_calls()
        ref = f"noop:{idempotency_key[:32]}"
        return ProductReceipt(status="delivered", external_reference=ref)

    def get_delivery_status(self, receipt: ProductReceipt) -> ProductReceipt:
        return receipt

    def health_check(self) -> dict[str, Any]:
        return {"status": "healthy", "bridge": self.product_key, "enabled": True, "mode": "noop"}


class ProductBridgeRegistry:
    def __init__(self) -> None:
        self._bridges: dict[str, ProductDocumentBridge] = {}

    def register(self, bridge: ProductDocumentBridge) -> None:
        self._bridges[bridge.product_key] = bridge

    def get(self, key: str) -> ProductDocumentBridge:
        b = self._bridges.get(key)
        if not b:
            raise ProductIntegrationValidationError("bridge_unknown", f"Bridge inconnu: {key}")
        return b

    def list_public(self) -> list[dict[str, Any]]:
        enabled = bool(getattr(settings, "product_document_bridge_enabled", False))
        default = (getattr(settings, "product_document_bridge_default", None) or BRIDGE_NOOP).strip()
        mode = (
            getattr(settings, "comptapilot_document_bridge_mode", None) or BRIDGE_MODE_DISABLED
        ).strip().lower()
        items = []
        for key, b in sorted(self._bridges.items()):
            health = b.health_check()
            items.append(
                {
                    "product_key": b.product_key,
                    "bridge_version": b.bridge_version,
                    "supported_package_schemas": sorted(b.supported_package_schemas),
                    "capabilities": sorted(b.capabilities),
                    "is_default": key == default,
                    "bridge_enabled_globally": enabled,
                    "bridge_mode": mode if key == "comptapilot" else "noop",
                    "health": health,
                }
            )
        return items


_DEFAULT: ProductBridgeRegistry | None = None


def build_default_bridge_registry() -> ProductBridgeRegistry:
    from app.product_integrations.comptapilot.bridge import ComptaPilotDocumentBridge

    reg = ProductBridgeRegistry()
    reg.register(NoopDocumentBridge())
    reg.register(ComptaPilotDocumentBridge())
    return reg


def get_bridge_registry() -> ProductBridgeRegistry:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = build_default_bridge_registry()
    return _DEFAULT


def reset_bridge_registry_for_tests() -> None:
    global _DEFAULT
    _DEFAULT = None
