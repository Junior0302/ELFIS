"""System Health — Document Processing queue."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from app.config import settings
from app.database import SessionLocal
from app.document_processing.models import ElfisDocumentProcessingJob
from app.document_processing.types import ProcessingJobStatus
from app.system_health.health_provider import HealthProvider
from app.system_health.health_schemas import HealthCheckResult
from app.system_health.health_types import HealthCategory, HealthStatus
from app.system_health.health_utils import metric, run_with_timeout, safe_error_message, utcnow

logger = logging.getLogger(__name__)


class DocumentProcessingHealthProvider(HealthProvider):
    service_id = "document_processing"
    service_name = "Document Processing"
    category = HealthCategory.WORKERS.value

    def check_health(self) -> HealthCheckResult:
        try:
            return run_with_timeout(self._check, timeout_seconds=5.0, label=self.service_id)
        except Exception as exc:
            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=self.category,
                status=HealthStatus.UNHEALTHY,
                summary="Document processing inaccessible",
                latency_ms=None,
                checked_at=utcnow(),
                version="v1",
                metrics=[],
                metadata={"provider_mode": "real", "simulated": False},
                error_code="dp_check_failed",
                error_message=safe_error_message(exc),
            )

    def _check(self) -> HealthCheckResult:
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            queued = (
                db.query(ElfisDocumentProcessingJob)
                .filter(
                    ElfisDocumentProcessingJob.status.in_(
                        [ProcessingJobStatus.QUEUED.value, ProcessingJobStatus.RETRYING.value]
                    )
                )
                .count()
            )
            running = (
                db.query(ElfisDocumentProcessingJob)
                .filter(ElfisDocumentProcessingJob.status == ProcessingJobStatus.RUNNING.value)
                .count()
            )
            failed = (
                db.query(ElfisDocumentProcessingJob)
                .filter(ElfisDocumentProcessingJob.status == ProcessingJobStatus.FAILED.value)
                .filter(ElfisDocumentProcessingJob.failed_at >= now - timedelta(hours=1))
                .count()
            )
            expired_leases = (
                db.query(ElfisDocumentProcessingJob)
                .filter(
                    ElfisDocumentProcessingJob.status == ProcessingJobStatus.RUNNING.value,
                    ElfisDocumentProcessingJob.locked_until.isnot(None),
                    ElfisDocumentProcessingJob.locked_until < now,
                )
                .count()
            )
            oldest = (
                db.query(ElfisDocumentProcessingJob)
                .filter(
                    ElfisDocumentProcessingJob.status.in_(
                        [ProcessingJobStatus.QUEUED.value, ProcessingJobStatus.RETRYING.value]
                    )
                )
                .order_by(ElfisDocumentProcessingJob.scheduled_at.asc())
                .first()
            )
            oldest_age = None
            if oldest and oldest.scheduled_at:
                oldest_age = int((now - oldest.scheduled_at).total_seconds())

            degraded_age = int(
                getattr(settings, "document_processing_queue_degraded_age_seconds", 300) or 300
            )
            unhealthy_age = int(
                getattr(settings, "document_processing_queue_unhealthy_age_seconds", 1800) or 1800
            )

            status = HealthStatus.HEALTHY
            summary = "File processing nominale"
            error_code = None
            if expired_leases >= 5 or (oldest_age is not None and oldest_age >= unhealthy_age):
                status = HealthStatus.UNHEALTHY
                summary = "Queue processing bloquée"
                error_code = "dp_queue_blocked"
            elif expired_leases >= 1 or (oldest_age is not None and oldest_age >= degraded_age) or failed >= 5:
                status = HealthStatus.DEGRADED
                summary = "Queue processing dégradée"
                error_code = "dp_queue_degraded"

            # Qualité classification (n'altère pas healthy/degraded technique)
            class_review = 0
            class_failed = 0
            class_unknown = 0
            class_low = 0
            class_queued = 0
            try:
                from app.document_processing.classification.models import ElfisDocumentClassification
                from app.document_processing.classification.types import ClassificationStatus
                from app.document_processing.types import PIPELINE_CLASSIFICATION_V1

                class_review = (
                    db.query(ElfisDocumentClassification)
                    .filter(
                        ElfisDocumentClassification.requires_review.is_(True),
                        ElfisDocumentClassification.status == ClassificationStatus.PROPOSED.value,
                    )
                    .count()
                )
                class_failed = (
                    db.query(ElfisDocumentClassification)
                    .filter(ElfisDocumentClassification.status == ClassificationStatus.FAILED.value)
                    .filter(ElfisDocumentClassification.created_at >= now - timedelta(hours=24))
                    .count()
                )
                recent = (
                    db.query(ElfisDocumentClassification)
                    .filter(ElfisDocumentClassification.created_at >= now - timedelta(hours=24))
                    .count()
                )
                class_unknown = (
                    db.query(ElfisDocumentClassification)
                    .filter(ElfisDocumentClassification.predicted_type == "unknown")
                    .filter(ElfisDocumentClassification.created_at >= now - timedelta(hours=24))
                    .count()
                )
                class_low = (
                    db.query(ElfisDocumentClassification)
                    .filter(ElfisDocumentClassification.confidence_score < 0.55)
                    .filter(ElfisDocumentClassification.created_at >= now - timedelta(hours=24))
                    .count()
                )
                class_queued = (
                    db.query(ElfisDocumentProcessingJob)
                    .filter(
                        ElfisDocumentProcessingJob.pipeline_key == PIPELINE_CLASSIFICATION_V1,
                        ElfisDocumentProcessingJob.status.in_(
                            [ProcessingJobStatus.QUEUED.value, ProcessingJobStatus.RETRYING.value]
                        ),
                    )
                    .count()
                )
                _ = recent
            except Exception:
                class_queued = 0

            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=self.category,
                status=status,
                summary=summary,
                latency_ms=None,
                checked_at=utcnow(),
                version="v1",
                metrics=[
                    metric("queued", "Jobs queued", queued, unit="jobs"),
                    metric("running", "Jobs running", running, unit="jobs"),
                    metric("failed_1h", "Failed 1h", failed, unit="jobs"),
                    metric("expired_leases", "Leases expirées", expired_leases, unit="jobs"),
                    metric("oldest_queued_age", "Oldest queued age", oldest_age, unit="s"),
                    metric("classification_queued", "Classifications queued", class_queued, unit="jobs"),
                    metric("classification_review", "Revue classification", class_review, unit="items"),
                    metric("classification_failed_24h", "Classif. failed 24h", class_failed, unit="items"),
                    metric("classification_unknown_24h", "Unknown 24h", class_unknown, unit="items"),
                    metric("classification_low_conf_24h", "Faible confiance 24h", class_low, unit="items"),
                ],
                metadata={
                    "provider_mode": "real",
                    "simulated": False,
                    "note": "review_volume_is_not_technical_failure",
                },
                error_code=error_code,
                error_message=None,
            )
        finally:
            db.close()
