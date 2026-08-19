"""Politiques bridge ComptaPilot."""

from __future__ import annotations

from app.config import settings
from app.product_integrations.exceptions import ProductBridgeDisabledError, ProductIntegrationValidationError


class ComptaPilotBridgePolicy:
    def assert_publish_enabled(self) -> None:
        if not getattr(settings, "product_document_bridge_enabled", False):
            raise ProductBridgeDisabledError("bridge_disabled", "Bridge produit désactivé")
        if not getattr(settings, "comptapilot_document_publish_enabled", False):
            raise ProductBridgeDisabledError(
                "comptapilot_publish_disabled",
                "Publication ComptaPilot désactivée",
            )

    def assert_package_eligible(self, package: dict) -> None:
        validation = package.get("validation") or {}
        status = validation.get("status")
        if getattr(settings, "comptapilot_require_valid_business_validation", True):
            if status not in ("valid", "valid_with_warnings"):
                raise ProductIntegrationValidationError(
                    "validation_insufficient",
                    "Validation métier insuffisante",
                )
        extraction = package.get("extraction") or {}
        if getattr(settings, "comptapilot_require_confirmed_extraction", True):
            if extraction.get("status") not in ("confirmed",):
                # package may carry confirmed via validation path
                if not extraction.get("confirmed"):
                    raise ProductIntegrationValidationError(
                        "extraction_not_confirmed",
                        "Extraction confirmée requise",
                    )
