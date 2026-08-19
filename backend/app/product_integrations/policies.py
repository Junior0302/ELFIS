"""Politiques d'accès packages / livraisons / features."""

from __future__ import annotations

from app.config import settings
from app.product_integrations.exceptions import (
    ProductBridgeDisabledError,
    ProductIntegrationAccessDeniedError,
    ProductIntegrationValidationError,
)
from app.product_integrations.types import BRIDGE_MODE_DISABLED, BRIDGE_MODE_DRY_RUN, BRIDGE_MODE_LIVE
from app.storage.storage_models import ElfisDocumentRecord
from app.storage.storage_types import DocumentStatus


class ProductFeatureAccessPolicy:
    """Entitlements abstraits — pas de logique Stripe parallèle.

    En cas d'incertitude : refuser la publication (codes explicites).
    Platform admin ne contourne pas ces flags.
    """

    def resolve_mode(self) -> str:
        from app.product_integrations.comptapilot.bridge import resolve_comptapilot_bridge_mode

        return resolve_comptapilot_bridge_mode()

    def assert_comptapilot_publish_allowed(self, *, organization_id: int, db=None) -> None:
        if not getattr(settings, "product_document_bridge_enabled", False):
            raise ProductBridgeDisabledError("bridge_disabled", "Bridge produit désactivé")
        mode = self.resolve_mode()
        if mode == BRIDGE_MODE_DISABLED:
            raise ProductBridgeDisabledError("comptapilot_bridge_disabled", "Bridge ComptaPilot désactivé")
        if mode == BRIDGE_MODE_LIVE and not getattr(settings, "comptapilot_document_publish_enabled", False):
            raise ProductBridgeDisabledError(
                "comptapilot_publish_disabled",
                "Publication ComptaPilot désactivée",
            )
        if organization_id and db is not None:
            self._assert_org_entitlement(db, organization_id)

    def assert_live_publish_allowed(self, *, organization_id: int, db=None) -> None:
        self.assert_comptapilot_publish_allowed(organization_id=organization_id, db=db)
        if self.resolve_mode() != BRIDGE_MODE_LIVE:
            raise ProductBridgeDisabledError(
                "live_not_enabled",
                "Mode live non activé (disabled/dry_run)",
            )

    def _assert_org_entitlement(self, db, organization_id: int) -> None:
        try:
            from app.models_saas import Organization

            org = db.get(Organization, organization_id)
            if not org:
                raise ProductIntegrationAccessDeniedError("organization_missing", "Organisation introuvable")
            if getattr(org, "platform_suspended_at", None):
                raise ProductIntegrationAccessDeniedError(
                    "organization_suspended",
                    "Organisation suspendue",
                )
            status = getattr(org, "status", None)
            if status and str(status).lower() in {"disabled", "inactive", "closed"}:
                raise ProductIntegrationAccessDeniedError(
                    "organization_inactive",
                    "Organisation inactive",
                )
        except (ProductIntegrationAccessDeniedError, ProductBridgeDisabledError):
            raise
        except Exception:
            # incertitude → refus explicite, pas de contournement
            raise ProductIntegrationAccessDeniedError(
                "entitlement_uncertain",
                "Entitlement organisation non vérifiable",
            ) from None

        # abonnement : lecture via get_subscription_access — incertitude = refus
        try:
            from app.subscriptions.access import get_subscription_access

            access = get_subscription_access(db, organization_id)
            if not getattr(access, "has_access", False):
                raise ProductIntegrationAccessDeniedError(
                    "subscription_inactive",
                    "Abonnement ou essai inactif",
                )
        except ProductIntegrationAccessDeniedError:
            raise
        except ImportError:
            pass
        except Exception:
            raise ProductIntegrationAccessDeniedError(
                "subscription_uncertain",
                "Statut abonnement non vérifiable",
            ) from None


class ProductPackageAccessPolicy:
    def assert_document_ok(self, document: ElfisDocumentRecord, *, for_mutate: bool = False) -> None:
        if document.status == DocumentStatus.PURGED.value:
            raise ProductIntegrationAccessDeniedError("document_purged", "Document purgé")
        if document.status == DocumentStatus.DELETED.value and for_mutate:
            raise ProductIntegrationAccessDeniedError("document_deleted", "Document inaccessible")

    def assert_can_package(self, document: ElfisDocumentRecord, *, quarantined: bool) -> None:
        if quarantined:
            raise ProductIntegrationValidationError("object_quarantined", "Document en quarantaine")
        if document.status in (DocumentStatus.PURGED.value, DocumentStatus.DELETED.value):
            raise ProductIntegrationValidationError("document_unavailable", "Document indisponible")


class ProductDeliveryAccessPolicy:
    def assert_can_deliver_package_status(self, status: str) -> None:
        if status in ("revoked", "superseded", "rejected"):
            raise ProductIntegrationValidationError("package_not_deliverable", "Package non livrable")
