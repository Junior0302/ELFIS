"""System Health — Business Validation (métier documentaire, pas comptable)."""

from __future__ import annotations

from datetime import timedelta

from app.config import settings
from app.database import SessionLocal
from app.document_processing.models import ElfisDocumentProcessingJob
from app.document_processing.types import ProcessingJobStatus
from app.document_processing.validation.models import ElfisDocumentBusinessValidation
from app.document_processing.validation.types import BusinessValidationStatus, PIPELINE_BUSINESS_VALIDATION_V1
from app.system_health.health_provider import HealthProvider
from app.system_health.health_schemas import HealthCheckResult
from app.system_health.health_types import HealthCategory, HealthStatus
from app.system_health.health_utils import metric, run_with_timeout, safe_error_message, utcnow


class BusinessValidationHealthProvider(HealthProvider):
    service_id = "business_validation"
    service_name = "Business Validation"
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
                summary="Validation métier inaccessible",
                latency_ms=None,
                checked_at=utcnow(),
                version="v1",
                metrics=[],
                metadata={"provider_mode": "real", "simulated": False},
                error_code="business_validation_check_failed",
                error_message=safe_error_message(exc),
            )

    def _check(self) -> HealthCheckResult:
        enabled = bool(getattr(settings, "document_business_validation_enabled", False))
        status = HealthStatus.HEALTHY
        summary = (
            "Validation métier documentaire désactivée (pas une panne)"
            if not enabled
            else "Validation métier documentaire disponible"
        )
        db = SessionLocal()
        try:
            now = utcnow()
            since = now - timedelta(hours=1)
            invalid = (
                db.query(ElfisDocumentBusinessValidation)
                .filter(ElfisDocumentBusinessValidation.status == BusinessValidationStatus.INVALID.value)
                .filter(ElfisDocumentBusinessValidation.created_at >= since)
                .count()
            )
            failed = (
                db.query(ElfisDocumentBusinessValidation)
                .filter(ElfisDocumentBusinessValidation.status == BusinessValidationStatus.FAILED.value)
                .filter(ElfisDocumentBusinessValidation.created_at >= since)
                .count()
            )
            review = (
                db.query(ElfisDocumentBusinessValidation)
                .filter(ElfisDocumentBusinessValidation.requires_review.is_(True))
                .count()
            )
            queued = (
                db.query(ElfisDocumentProcessingJob)
                .filter(ElfisDocumentProcessingJob.pipeline_key == PIPELINE_BUSINESS_VALIDATION_V1)
                .filter(
                    ElfisDocumentProcessingJob.status.in_(
                        [ProcessingJobStatus.QUEUED.value, ProcessingJobStatus.PENDING.value]
                    )
                )
                .count()
            )
            if failed > 20:
                status = HealthStatus.DEGRADED
                summary = "Échecs validation métier élevés"
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
                    metric("enabled", 1 if enabled else 0),
                    metric("invalid_1h", invalid),
                    metric("failed_1h", failed),
                    metric("requires_review", review),
                    metric("queued_jobs", queued),
                ],
                metadata={
                    "provider_mode": "real",
                    "enabled": enabled,
                    "note": "document invalide ≠ panne infrastructure",
                },
                error_code=None,
                error_message=None,
            )
        finally:
            db.close()
