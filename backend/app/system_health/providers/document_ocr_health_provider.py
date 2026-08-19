"""System Health — OCR providers / backlog."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.config import settings
from app.database import SessionLocal
from app.document_processing.ocr.models import ElfisDocumentOCRResult
from app.document_processing.ocr.provider_registry import get_ocr_provider_registry
from app.document_processing.ocr.types import OCRResultStatus, PIPELINE_OCR_V1
from app.document_processing.models import ElfisDocumentProcessingJob
from app.document_processing.types import ProcessingJobStatus
from app.system_health.health_provider import HealthProvider
from app.system_health.health_schemas import HealthCheckResult
from app.system_health.health_types import HealthCategory, HealthStatus
from app.system_health.health_utils import metric, run_with_timeout, safe_error_message, utcnow


class DocumentOCRHealthProvider(HealthProvider):
    service_id = "document_ocr"
    service_name = "Document OCR"
    category = HealthCategory.OCR.value

    def check_health(self) -> HealthCheckResult:
        try:
            return run_with_timeout(self._check, timeout_seconds=5.0, label=self.service_id)
        except Exception as exc:
            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=self.category,
                status=HealthStatus.UNHEALTHY,
                summary="OCR inaccessible",
                latency_ms=None,
                checked_at=utcnow(),
                version="v1",
                metrics=[],
                metadata={"provider_mode": "real", "simulated": False},
                error_code="ocr_check_failed",
                error_message=safe_error_message(exc),
            )

    def _check(self) -> HealthCheckResult:
        enabled = bool(getattr(settings, "document_ocr_enabled", False))
        configured = (getattr(settings, "document_ocr_provider", None) or "noop").strip().lower()
        try:
            reg = get_ocr_provider_registry()
            if configured in ("tesseract", "external"):
                status = HealthStatus.UNHEALTHY
                summary = f"Provider {configured} non activé"
                error_code = "ocr_provider_unavailable"
                avail = False
            else:
                provider = reg.get(configured)
                health = provider.health()
                avail = bool(health.get("available"))
                status = HealthStatus.HEALTHY if avail else HealthStatus.UNHEALTHY
                summary = (
                    "OCR noop (pas d'OCR réel)"
                    if configured == "noop"
                    else ("OCR disponible" if avail else "OCR indisponible")
                )
                error_code = None if avail else "ocr_provider_down"
        except Exception as exc:
            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=self.category,
                status=HealthStatus.UNHEALTHY,
                summary="Configuration OCR invalide",
                latency_ms=None,
                checked_at=utcnow(),
                version="v1",
                metrics=[],
                metadata={"provider_mode": "real", "configured": configured, "enabled": enabled},
                error_code="ocr_config_invalid",
                error_message=safe_error_message(exc),
            )

        db = SessionLocal()
        try:
            now = datetime.utcnow()
            queued = (
                db.query(ElfisDocumentProcessingJob)
                .filter(
                    ElfisDocumentProcessingJob.pipeline_key == PIPELINE_OCR_V1,
                    ElfisDocumentProcessingJob.status.in_(
                        [ProcessingJobStatus.QUEUED.value, ProcessingJobStatus.RETRYING.value]
                    ),
                )
                .count()
            )
            failed = (
                db.query(ElfisDocumentOCRResult)
                .filter(ElfisDocumentOCRResult.status == OCRResultStatus.FAILED.value)
                .filter(ElfisDocumentOCRResult.created_at >= now - timedelta(hours=24))
                .count()
            )
            if failed >= 20 and status == HealthStatus.HEALTHY:
                status = HealthStatus.DEGRADED
                summary = "Taux d'échec OCR élevé"
                error_code = "ocr_failure_rate"
            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=self.category,
                status=status if enabled or configured == "noop" else HealthStatus.DISABLED,
                summary=summary if enabled else "OCR désactivé",
                latency_ms=None,
                checked_at=utcnow(),
                version="v1",
                metrics=[
                    metric("enabled", "OCR enabled", 1 if enabled else 0),
                    metric("queued", "OCR jobs queued", queued, unit="jobs"),
                    metric("failed_24h", "OCR failed 24h", failed, unit="results"),
                ],
                metadata={
                    "provider_mode": "real",
                    "configured_provider": configured,
                    "real_ocr": configured not in ("noop", "native_pdf"),
                    "simulated": False,
                },
                error_code=error_code if enabled else None,
                error_message=None,
            )
        finally:
            db.close()
