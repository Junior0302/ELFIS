"""System Health — Document Extraction."""

from __future__ import annotations

from datetime import timedelta

from app.config import settings
from app.database import SessionLocal
from app.document_processing.extraction.models import ElfisDocumentExtractionResult
from app.document_processing.extraction.provider_registry import get_extraction_provider_registry
from app.document_processing.extraction.types import ExtractionResultStatus, PIPELINE_EXTRACTION_V1
from app.document_processing.models import ElfisDocumentProcessingJob
from app.document_processing.types import ProcessingJobStatus
from app.system_health.health_provider import HealthProvider
from app.system_health.health_schemas import HealthCheckResult
from app.system_health.health_types import HealthCategory, HealthStatus
from app.system_health.health_utils import metric, run_with_timeout, safe_error_message, utcnow


class DocumentExtractionHealthProvider(HealthProvider):
    service_id = "document_extraction"
    service_name = "Document Extraction"
    category = HealthCategory.OCR.value

    def check_health(self) -> HealthCheckResult:
        try:
            return run_with_timeout(self._check, timeout_seconds=5.0, label=self.service_id)
        except Exception as exc:
            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=str(self.category),
                status=HealthStatus.UNHEALTHY,
                summary="Extraction inaccessible",
                latency_ms=None,
                checked_at=utcnow(),
                version="v1",
                metrics=[],
                metadata={"provider_mode": "real", "simulated": False},
                error_code="extraction_check_failed",
                error_message=safe_error_message(exc),
            )

    def _check(self) -> HealthCheckResult:
        enabled = bool(getattr(settings, "document_extraction_enabled", False))
        configured = (
            getattr(settings, "document_extraction_provider", None) or "noop"
        ).strip().lower()
        try:
            reg = get_extraction_provider_registry()
            if configured in ("external", "openai", "ai"):
                status = HealthStatus.UNHEALTHY
                summary = f"Provider {configured} non activé"
                error_code = "extraction_provider_unavailable"
            else:
                reg.get(configured)
                status = HealthStatus.HEALTHY
                summary = (
                    "Extraction noop (pas d'extraction réelle)"
                    if configured == "noop"
                    else f"Extraction provider {configured} disponible"
                )
                error_code = None
        except Exception as exc:
            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=str(self.category),
                status=HealthStatus.UNHEALTHY,
                summary="Configuration extraction invalide",
                latency_ms=None,
                checked_at=utcnow(),
                version="v1",
                metrics=[],
                metadata={"configured": configured, "enabled": enabled},
                error_code="extraction_config_invalid",
                error_message=safe_error_message(exc),
            )

        db = SessionLocal()
        try:
            now = utcnow()
            since = now - timedelta(hours=1)
            review = (
                db.query(ElfisDocumentExtractionResult)
                .filter(ElfisDocumentExtractionResult.requires_review.is_(True))
                .filter(
                    ElfisDocumentExtractionResult.status.in_(
                        [
                            ExtractionResultStatus.COMPLETED.value,
                            ExtractionResultStatus.PARTIALLY_COMPLETED.value,
                            ExtractionResultStatus.INVALID.value,
                        ]
                    )
                )
                .count()
            )
            failed = (
                db.query(ElfisDocumentExtractionResult)
                .filter(ElfisDocumentExtractionResult.status == ExtractionResultStatus.FAILED.value)
                .filter(ElfisDocumentExtractionResult.created_at >= since)
                .count()
            )
            invalid = (
                db.query(ElfisDocumentExtractionResult)
                .filter(ElfisDocumentExtractionResult.status == ExtractionResultStatus.INVALID.value)
                .filter(ElfisDocumentExtractionResult.created_at >= since)
                .count()
            )
            queued = (
                db.query(ElfisDocumentProcessingJob)
                .filter(ElfisDocumentProcessingJob.pipeline_key == PIPELINE_EXTRACTION_V1)
                .filter(
                    ElfisDocumentProcessingJob.status.in_(
                        [ProcessingJobStatus.QUEUED.value, ProcessingJobStatus.PENDING.value]
                    )
                )
                .count()
            )
            # invalid élevé = qualité données, pas forcément panne infra
            if failed > 20:
                status = HealthStatus.DEGRADED
                summary = "Taux d'échec extraction élevé"
            metrics = [
                metric("enabled", 1 if enabled else 0),
                metric("requires_review", review),
                metric("failed_1h", failed),
                metric("invalid_1h", invalid),
                metric("queued_jobs", queued),
            ]
            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=str(self.category),
                status=status,
                summary=summary,
                latency_ms=None,
                checked_at=now,
                version="v1",
                metrics=metrics,
                metadata={
                    "provider_mode": "real",
                    "configured": configured,
                    "enabled": enabled,
                    "note": "invalid/review élevés ≠ panne infrastructure",
                },
                error_code=error_code,
                error_message=None,
            )
        finally:
            db.close()
