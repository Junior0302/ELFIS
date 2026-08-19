"""System Health — Product Integrations / bridge."""

from __future__ import annotations

from datetime import timedelta

from app.config import settings
from app.database import SessionLocal
from app.product_integrations.models import ElfisProductDocumentDelivery
from app.product_integrations.registry import get_bridge_registry
from app.product_integrations.types import DeliveryStatus
from app.system_health.health_provider import HealthProvider
from app.system_health.health_schemas import HealthCheckResult
from app.system_health.health_types import HealthCategory, HealthStatus
from app.system_health.health_utils import metric, run_with_timeout, safe_error_message, utcnow


class ProductIntegrationsHealthProvider(HealthProvider):
    service_id = "product_integrations"
    service_name = "Product Integrations"
    category = HealthCategory.WORKERS.value

    def check_health(self) -> HealthCheckResult:
        try:
            return run_with_timeout(self._check, timeout_seconds=5.0, label=self.service_id)
        except Exception as exc:
            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=str(self.category),
                status=HealthStatus.UNHEALTHY,
                summary="Product integrations inaccessible",
                latency_ms=None,
                checked_at=utcnow(),
                version="v1",
                metrics=[],
                metadata={"provider_mode": "real"},
                error_code="product_integrations_check_failed",
                error_message=safe_error_message(exc),
            )

    def _check(self) -> HealthCheckResult:
        bridge_enabled = bool(getattr(settings, "product_document_bridge_enabled", False))
        publish_enabled = bool(getattr(settings, "comptapilot_document_publish_enabled", False))
        mode = (
            getattr(settings, "comptapilot_document_bridge_mode", None) or "disabled"
        ).strip().lower()
        default_bridge = (getattr(settings, "product_document_bridge_default", None) or "noop").strip()
        reg = get_bridge_registry()
        try:
            reg.get(default_bridge)
        except Exception:
            pass
        status = HealthStatus.HEALTHY
        if mode == "disabled" or not bridge_enabled:
            summary = f"Bridge produit mode={mode} (pas une panne)"
        elif mode == "dry_run":
            summary = "Bridge ComptaPilot dry-run (pas live)"
        else:
            summary = f"Bridge {default_bridge} mode={mode}"
        db = SessionLocal()
        try:
            now = utcnow()
            since = now - timedelta(hours=1)
            queued = (
                db.query(ElfisProductDocumentDelivery)
                .filter(
                    ElfisProductDocumentDelivery.status.in_(
                        [
                            DeliveryStatus.QUEUED.value,
                            DeliveryStatus.PENDING.value,
                            DeliveryStatus.RETRYING.value,
                        ]
                    )
                )
                .count()
            )
            unknown = (
                db.query(ElfisProductDocumentDelivery)
                .filter(
                    ElfisProductDocumentDelivery.status.in_(
                        [
                            DeliveryStatus.UNKNOWN.value,
                            DeliveryStatus.MANUAL_REVIEW.value,
                        ]
                    )
                )
                .count()
            )
            failed = (
                db.query(ElfisProductDocumentDelivery)
                .filter(ElfisProductDocumentDelivery.status == DeliveryStatus.FAILED.value)
                .filter(ElfisProductDocumentDelivery.created_at >= since)
                .count()
            )
            if bridge_enabled and mode == "live" and failed > 20:
                status = HealthStatus.DEGRADED
                summary = "Taux d'échec livraisons élevé"
            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=str(self.category),
                status=status,
                summary=summary,
                latency_ms=None,
                checked_at=now,
                version="v1",
                metrics=[
                    metric("bridge_enabled", 1 if bridge_enabled else 0),
                    metric("comptapilot_publish_enabled", 1 if publish_enabled else 0),
                    metric("queued_deliveries", queued),
                    metric("unknown_deliveries", unknown),
                    metric("failed_1h", failed),
                ],
                metadata={
                    "provider_mode": "real",
                    "default_bridge": default_bridge,
                    "bridge_enabled": bridge_enabled,
                    "publish_enabled": publish_enabled,
                    "bridge_mode": mode,
                    "note": "disabled/dry_run ≠ panne ; dry_run ≠ live",
                },
                error_code=None,
                error_message=None,
            )
        finally:
            db.close()
