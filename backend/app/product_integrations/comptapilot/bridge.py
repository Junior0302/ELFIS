"""ComptaPilotDocumentBridge — modes disabled | dry_run | live."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.config import settings
from app.product_integrations.comptapilot.adapter import ComptaPilotServiceAdapter
from app.product_integrations.comptapilot.mapper import ElfisToComptaPilotDocumentMapper
from app.product_integrations.comptapilot.policies import ComptaPilotBridgePolicy
from app.product_integrations.exceptions import ProductBridgeDisabledError, ProductIntegrationValidationError
from app.product_integrations.registry import ProductReceipt
from app.product_integrations.types import (
    BRIDGE_COMPTAPILOT,
    BRIDGE_MODE_DISABLED,
    BRIDGE_MODE_DRY_RUN,
    BRIDGE_MODE_LIVE,
    PACKAGE_SCHEMA_V1,
    PRODUCT_COMPTAPILOT,
)


def resolve_comptapilot_bridge_mode() -> str:
    raw = (getattr(settings, "comptapilot_document_bridge_mode", None) or BRIDGE_MODE_DISABLED)
    mode = str(raw).strip().lower()
    if mode not in (BRIDGE_MODE_DISABLED, BRIDGE_MODE_DRY_RUN, BRIDGE_MODE_LIVE):
        return BRIDGE_MODE_DISABLED
    # publish flag off force disabled même si mode=live mal configuré
    if mode == BRIDGE_MODE_LIVE and not getattr(settings, "comptapilot_document_publish_enabled", False):
        return BRIDGE_MODE_DISABLED
    if not getattr(settings, "product_document_bridge_enabled", False) and mode == BRIDGE_MODE_LIVE:
        return BRIDGE_MODE_DISABLED
    return mode


class ComptaPilotDocumentBridge:
    product_key = PRODUCT_COMPTAPILOT
    bridge_version = "1"
    supported_package_schemas = frozenset({PACKAGE_SCHEMA_V1})
    capabilities = frozenset({"deliver", "health", "transport_map", "get_delivery_status", "dry_run"})

    def __init__(self) -> None:
        self._adapter = ComptaPilotServiceAdapter()
        self._policy = ComptaPilotBridgePolicy()
        self._mapper = ElfisToComptaPilotDocumentMapper()
        self._receipts: dict[str, ProductReceipt] = {}

    def validate_package(self, package: dict[str, Any]) -> None:
        if package.get("package_schema") != PACKAGE_SCHEMA_V1:
            raise ProductIntegrationValidationError("schema_unsupported", "Schéma package non supporté")
        if not package.get("organization_id"):
            raise ProductIntegrationValidationError("organization_required", "Organisation requise")
        if not (package.get("extraction") or {}).get("result_id"):
            raise ProductIntegrationValidationError("extraction_required", "Extraction requise")
        if not (package.get("validation") or {}).get("result_id"):
            raise ProductIntegrationValidationError("validation_required", "Validation requise")

    def deliver(self, package: dict[str, Any], idempotency_key: str) -> ProductReceipt:
        self.validate_package(package)
        mode = resolve_comptapilot_bridge_mode()
        if mode == BRIDGE_MODE_DISABLED:
            return ProductReceipt(
                status="blocked",
                error_code="comptapilot_bridge_disabled",
                retryable=False,
                message_sanitized="Bridge ComptaPilot désactivé",
            )
        if idempotency_key in self._receipts:
            prev = self._receipts[idempotency_key]
            return ProductReceipt(
                status=prev.status,
                external_reference=prev.external_reference,
                error_code="duplicate_idempotent",
                retryable=False,
                message_sanitized="Doublon idempotent contrôlé",
            )
        try:
            self._policy.assert_package_eligible(package)
        except ProductIntegrationValidationError as exc:
            return ProductReceipt(
                status="failed",
                error_code=exc.code,
                retryable=False,
                message_sanitized=exc.message,
            )

        if mode == BRIDGE_MODE_DRY_RUN:
            transport = self._mapper.map_transport(package)
            if any(k in transport for k in ("accounting_entries", "journal_code", "general_account")):
                return ProductReceipt(
                    status="failed",
                    error_code="accounting_forbidden",
                    retryable=False,
                    message_sanitized="Mapping comptable interdit",
                )
            ref = f"dry-run:{uuid4().hex[:16]}"
            receipt = ProductReceipt(
                status="validated_not_delivered",
                external_reference=ref,
                message_sanitized="Dry-run — aucun import métier",
            )
            self._receipts[idempotency_key] = receipt
            return receipt

        # live
        if not getattr(settings, "comptapilot_document_publish_enabled", False):
            return ProductReceipt(
                status="blocked",
                error_code="comptapilot_publish_disabled",
                retryable=False,
                message_sanitized="Publication ComptaPilot désactivée",
            )
        try:
            receipt = self._adapter.accept_transport(package, idempotency_key=idempotency_key)
            self._receipts[idempotency_key] = receipt
            return receipt
        except ProductBridgeDisabledError as exc:
            return ProductReceipt(
                status="blocked",
                error_code=exc.code,
                retryable=False,
                message_sanitized=exc.message,
            )
        except ProductIntegrationValidationError as exc:
            return ProductReceipt(
                status="failed",
                error_code=exc.code,
                retryable=False,
                message_sanitized=exc.message,
            )

    def get_delivery_status(self, receipt: ProductReceipt) -> ProductReceipt:
        if receipt.external_reference and receipt.external_reference in {
            r.external_reference for r in self._receipts.values()
        }:
            return receipt
        if receipt.external_reference and receipt.external_reference.startswith("dry-run:"):
            return ProductReceipt(
                status="validated_not_delivered",
                external_reference=receipt.external_reference,
                message_sanitized="Dry-run confirmé",
            )
        if receipt.external_reference and receipt.external_reference.startswith("cp-import:"):
            return ProductReceipt(
                status="delivered",
                external_reference=receipt.external_reference,
            )
        return ProductReceipt(
            status="unknown",
            external_reference=receipt.external_reference,
            uncertain=True,
            error_code="remote_status_unknown",
            message_sanitized="État distant inconnu",
        )

    def health_check(self) -> dict[str, Any]:
        mode = resolve_comptapilot_bridge_mode()
        bridge_on = bool(getattr(settings, "product_document_bridge_enabled", False))
        return {
            "status": "healthy",
            "bridge": BRIDGE_COMPTAPILOT,
            "bridge_enabled": bridge_on,
            "publish_enabled": bool(getattr(settings, "comptapilot_document_publish_enabled", False)),
            "mode": mode,
            "accounting_writes": False,
            "note": "disabled/dry_run ≠ panne",
        }
