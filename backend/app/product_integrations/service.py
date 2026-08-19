"""ProductIntegrationService — packages + livraisons (pas d'écritures comptables)."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.document_processing.extraction.models import ElfisDocumentExtractionResult
from app.document_processing.extraction.service import DocumentExtractionService
from app.document_processing.extraction.types import ExtractionResultStatus
from app.document_processing.validation.models import ElfisDocumentBusinessValidation
from app.document_processing.validation.service import DocumentBusinessValidationService
from app.document_processing.validation.types import BusinessValidationStatus
from app.product_integrations import metrics as pi_metrics
from app.product_integrations.exceptions import (
    ProductIntegrationAccessDeniedError,
    ProductIntegrationNotFoundError,
    ProductIntegrationValidationError,
)
from app.product_integrations.models import (
    ElfisProductDocumentDelivery,
    ElfisProductDocumentDeliveryAttempt,
    ElfisProductProcessingPackage,
)
from app.product_integrations.policies import (
    ProductDeliveryAccessPolicy,
    ProductFeatureAccessPolicy,
    ProductPackageAccessPolicy,
)
from app.product_integrations.registry import get_bridge_registry
from app.product_integrations.repository import ProductIntegrationRepository
from app.product_integrations.sanitization import sanitize_error_message, sanitize_metadata
from app.product_integrations.types import (
    AttemptStatus,
    DeliveryStatus,
    PACKAGE_SCHEMA_V1,
    PACKAGE_SCHEMA_VERSION,
    PRODUCT_COMPTAPILOT,
    PackageStatus,
)
from app.storage.storage_models import ElfisDocumentRecord, ElfisDocumentVersion, ElfisStorageObject

logger = logging.getLogger(__name__)


def build_idempotency_key(
    *,
    product_key: str,
    organization_id: int,
    document_version_id: str,
    extraction_result_id: str,
    business_validation_id: str,
    package_schema_version: str,
) -> str:
    raw = "|".join(
        [
            product_key,
            str(organization_id),
            document_version_id,
            extraction_result_id,
            business_validation_id,
            package_schema_version,
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ProductIntegrationService:
    def __init__(self, db: Session, *, audit_logger: Any | None = None) -> None:
        self._db = db
        self._repo = ProductIntegrationRepository(db)
        self._audit = audit_logger
        self._features = ProductFeatureAccessPolicy()
        self._pkg_policy = ProductPackageAccessPolicy()
        self._del_policy = ProductDeliveryAccessPolicy()
        self._bridges = get_bridge_registry()

    def list_bridges_public(self) -> list[dict]:
        return self._bridges.list_public()

    def get_package_for_org(self, package_id: str, organization_id: int) -> ElfisProductProcessingPackage:
        row = self._repo.get_package(package_id)
        if not row or row.organization_id != organization_id:
            raise ProductIntegrationNotFoundError("not_found", "Package introuvable")
        return row

    def get_package_platform(self, package_id: str) -> ElfisProductProcessingPackage:
        row = self._repo.get_package(package_id)
        if not row:
            raise ProductIntegrationNotFoundError("not_found", "Package introuvable")
        return row

    def list_packages(self, **kwargs):
        return self._repo.list_packages(**kwargs)

    def get_delivery_for_org(self, delivery_id: str, organization_id: int) -> ElfisProductDocumentDelivery:
        row = self._repo.get_delivery(delivery_id)
        if not row or row.organization_id != organization_id:
            raise ProductIntegrationNotFoundError("not_found", "Livraison introuvable")
        return row

    def get_delivery_platform(self, delivery_id: str) -> ElfisProductDocumentDelivery:
        row = self._repo.get_delivery(delivery_id)
        if not row:
            raise ProductIntegrationNotFoundError("not_found", "Livraison introuvable")
        return row

    def list_deliveries(self, **kwargs):
        return self._repo.list_deliveries(**kwargs)

    def create_comptapilot_package(
        self,
        *,
        organization_id: int,
        document_id: str,
        document_version_id: str | None = None,
        business_validation_id: str | None = None,
        actor_user_id: int | None = None,
        force_feature: bool = False,
    ) -> ElfisProductProcessingPackage:
        if not force_feature:
            self._features.assert_comptapilot_publish_allowed(
                organization_id=organization_id, db=self._db
            )

        doc = self._db.get(ElfisDocumentRecord, document_id)
        if not doc or doc.organization_id != organization_id:
            raise ProductIntegrationNotFoundError("document_not_found", "Document introuvable")
        self._pkg_policy.assert_document_ok(doc, for_mutate=True)

        version_id = document_version_id or doc.current_version_id
        if not version_id:
            raise ProductIntegrationValidationError("version_missing", "Version absente")
        version = self._db.get(ElfisDocumentVersion, version_id)
        if not version or version.document_id != doc.id:
            raise ProductIntegrationValidationError("version_invalid", "Version invalide")

        storage = self._db.get(ElfisStorageObject, version.storage_object_id) if version.storage_object_id else None
        quarantined = bool(storage and storage.status == "quarantined")
        self._pkg_policy.assert_can_package(doc, quarantined=quarantined)

        bv_svc = DocumentBusinessValidationService(self._db, audit_logger=self._audit)
        if business_validation_id:
            validation = bv_svc.get_for_org(business_validation_id, organization_id)
        else:
            items, _ = bv_svc.list_results(
                organization_id=organization_id,
                document_id=document_id,
                version_id=version_id,
                limit=1,
                offset=0,
            )
            if not items:
                raise ProductIntegrationValidationError("validation_missing", "Validation métier absente")
            validation = items[0]

        if validation.document_version_id != version_id:
            raise ProductIntegrationValidationError("validation_version_mismatch", "Mauvaise version")
        if getattr(settings, "comptapilot_require_valid_business_validation", True):
            if validation.status not in (
                BusinessValidationStatus.VALID.value,
                BusinessValidationStatus.VALID_WITH_WARNINGS.value,
            ) or not validation.valid:
                # confirmation humaine → status valid
                if validation.status != BusinessValidationStatus.VALID.value:
                    raise ProductIntegrationValidationError(
                        "validation_insufficient",
                        "Validation métier insuffisante",
                    )

        extr = self._db.get(ElfisDocumentExtractionResult, validation.extraction_result_id)
        if not extr or extr.organization_id != organization_id:
            raise ProductIntegrationValidationError("extraction_missing", "Extraction absente")
        if extr.document_version_id != version_id:
            raise ProductIntegrationValidationError("extraction_version_mismatch", "Mauvaise version")
        if getattr(settings, "comptapilot_require_confirmed_extraction", True):
            if extr.status != ExtractionResultStatus.CONFIRMED.value:
                raise ProductIntegrationValidationError(
                    "extraction_not_confirmed",
                    "Extraction confirmée requise",
                )

        idem = build_idempotency_key(
            product_key=PRODUCT_COMPTAPILOT,
            organization_id=organization_id,
            document_version_id=version_id,
            extraction_result_id=extr.id,
            business_validation_id=validation.id,
            package_schema_version=PACKAGE_SCHEMA_VERSION,
        )
        existing = self._repo.get_package_by_idempotency(idem)
        if existing:
            pi_metrics.incr("package_duplicate_prevented_total")
            return existing

        fields_payload: dict[str, Any] = {}
        try:
            data, _ = DocumentExtractionService(self._db, audit_logger=self._audit).open_content(
                extr.id, organization_id, platform=False
            )
            payload = json.loads(data.decode("utf-8"))
            fields_payload = dict(payload.get("fields") or {})
        except Exception as exc:
            raise ProductIntegrationValidationError("extraction_content_unavailable", "Contenu extraction indisponible") from exc

        issues = bv_svc.list_issues(validation.id)
        issue_codes = [i.issue_code for i in issues][:50]
        package_body = {
            "package_schema": PACKAGE_SCHEMA_V1,
            "package_id": None,  # rempli après
            "organization_id": organization_id,
            "document": {
                "id": doc.id,
                "version_id": version_id,
                "effective_type": extr.effective_document_type or doc.document_type,
            },
            "classification": {
                "classification_id": validation.classification_id or extr.classification_id,
                "effective_type": extr.effective_document_type,
            },
            "extraction": {
                "result_id": extr.id,
                "schema_key": extr.schema_key,
                "schema_version": extr.schema_version,
                "status": extr.status,
                "confirmed": extr.status == ExtractionResultStatus.CONFIRMED.value,
                "fields": fields_payload,
            },
            "validation": {
                "result_id": validation.id,
                "status": validation.status,
                "issue_codes": issue_codes,
            },
            "provenance": {
                "ocr_result_id": extr.ocr_result_id,
                "provider_versions": {
                    "extraction_provider": extr.provider_key,
                    "extraction_provider_version": extr.provider_version,
                },
            },
        }

        pkg_id = str(uuid4())
        package_body["package_id"] = pkg_id
        raw = json.dumps(package_body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        checksum = hashlib.sha256(raw).hexdigest()
        artifact = self._store_package_artifact(
            organization_id=organization_id,
            package_id=pkg_id,
            content=raw,
            checksum=checksum,
        )
        row = ElfisProductProcessingPackage(
            id=pkg_id,
            organization_id=organization_id,
            product_key=PRODUCT_COMPTAPILOT,
            document_id=doc.id,
            document_version_id=version_id,
            classification_id=validation.classification_id or extr.classification_id,
            ocr_result_id=extr.ocr_result_id,
            extraction_result_id=extr.id,
            business_validation_id=validation.id,
            package_schema_key=PACKAGE_SCHEMA_V1,
            package_schema_version=PACKAGE_SCHEMA_VERSION,
            status=PackageStatus.READY.value,
            content_artifact_storage_object_id=artifact.id,
            checksum_sha256=checksum,
            idempotency_key=idem,
            created_by_user_id=actor_user_id,
        )
        try:
            self._repo.add_package(row, commit=True)
        except IntegrityError:
            self._db.rollback()
            raced = self._repo.get_package_by_idempotency(idem)
            if raced:
                pi_metrics.incr("package_duplicate_prevented_total")
                return raced
            raise
        pi_metrics.incr("packages_created")
        self._safe_audit(
            "record_product_document_package_created",
            package_id=row.id,
            document_id=doc.id,
            version_id=version_id,
            extraction_result_id=extr.id,
            validation_id=validation.id,
            organization_id=organization_id,
            product_key=PRODUCT_COMPTAPILOT,
            status=row.status,
            actor_user_id=actor_user_id,
        )
        self._safe_audit(
            "record_product_document_package_ready",
            package_id=row.id,
            organization_id=organization_id,
            product_key=PRODUCT_COMPTAPILOT,
            status=row.status,
        )
        return row

    def queue_delivery(
        self,
        package_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        platform: bool = False,
        force_feature: bool = False,
    ) -> ElfisProductDocumentDelivery:
        pkg = self.get_package_platform(package_id) if platform else self.get_package_for_org(package_id, organization_id)
        if pkg.organization_id != organization_id and not platform:
            raise ProductIntegrationAccessDeniedError("forbidden", "Accès refusé")
        if not force_feature:
            self._features.assert_comptapilot_publish_allowed(
                organization_id=pkg.organization_id, db=self._db
            )
        self._del_policy.assert_can_deliver_package_status(pkg.status)
        if pkg.status not in (PackageStatus.READY.value, PackageStatus.DELIVERY_FAILED.value, PackageStatus.DELIVERY_PENDING.value):
            if pkg.status == PackageStatus.DELIVERED.value:
                existing = (
                    self._db.query(ElfisProductDocumentDelivery)
                    .filter(ElfisProductDocumentDelivery.package_id == pkg.id)
                    .filter(ElfisProductDocumentDelivery.status == DeliveryStatus.DELIVERED.value)
                    .first()
                )
                if existing:
                    return existing
            raise ProductIntegrationValidationError("package_not_ready", "Package non prêt")

        delivery_idem = f"del:{pkg.idempotency_key}"
        existing = self._repo.get_delivery_by_idempotency(delivery_idem)
        if existing:
            pi_metrics.incr("package_duplicate_prevented_total")
            return existing

        bridge = self._bridges.get(pkg.product_key)
        max_attempts = int(getattr(settings, "product_delivery_max_attempts", 3) or 3)
        row = ElfisProductDocumentDelivery(
            id=str(uuid4()),
            organization_id=pkg.organization_id,
            package_id=pkg.id,
            product_key=pkg.product_key,
            bridge_key=bridge.product_key,
            bridge_version=bridge.bridge_version,
            status=DeliveryStatus.QUEUED.value,
            attempt_count=0,
            max_attempts=max_attempts,
            idempotency_key=delivery_idem,
        )
        pkg.status = PackageStatus.DELIVERY_PENDING.value
        pkg.updated_at = datetime.utcnow()
        try:
            self._repo.add_delivery(row, commit=True)
        except IntegrityError:
            self._db.rollback()
            raced = self._repo.get_delivery_by_idempotency(delivery_idem)
            if raced:
                pi_metrics.incr("package_duplicate_prevented_total")
                return raced
            raise
        self._safe_audit(
            "record_product_document_delivery_queued",
            package_id=pkg.id,
            delivery_id=row.id,
            organization_id=pkg.organization_id,
            product_key=pkg.product_key,
            bridge_version=bridge.bridge_version,
            status=row.status,
            actor_user_id=actor_user_id,
        )
        self._safe_audit(
            "record_comptapilot_document_publish_requested",
            package_id=pkg.id,
            delivery_id=row.id,
            organization_id=pkg.organization_id,
            product_key=pkg.product_key,
            status=row.status,
        )
        return row

    def retry_delivery(
        self,
        delivery_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        platform: bool = False,
    ) -> ElfisProductDocumentDelivery:
        row = self.get_delivery_platform(delivery_id) if platform else self.get_delivery_for_org(delivery_id, organization_id)
        if row.status not in (DeliveryStatus.FAILED.value, DeliveryStatus.BLOCKED.value):
            raise ProductIntegrationValidationError("not_retryable", "Livraison non relançable")
        if row.attempt_count >= row.max_attempts:
            raise ProductIntegrationValidationError("max_attempts", "Tentatives épuisées")
        row.status = DeliveryStatus.QUEUED.value
        row.next_retry_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        self._db.commit()
        self._db.refresh(row)
        self._safe_audit(
            "record_product_document_delivery_retry_requested",
            delivery_id=row.id,
            package_id=row.package_id,
            organization_id=row.organization_id,
            product_key=row.product_key,
            attempt_number=row.attempt_count,
            actor_user_id=actor_user_id,
        )
        return row

    def process_delivery(self, delivery: ElfisProductDocumentDelivery, *, worker_id: str) -> ElfisProductDocumentDelivery:
        started = datetime.utcnow()
        attempt_n = delivery.attempt_count + 1
        attempt = ElfisProductDocumentDeliveryAttempt(
            id=str(uuid4()),
            delivery_id=delivery.id,
            attempt_number=attempt_n,
            worker_id=worker_id,
            status=AttemptStatus.STARTED.value,
            started_at=started,
        )
        self._repo.add_attempt(attempt, commit=False)
        delivery.attempt_count = attempt_n
        delivery.updated_at = started
        self._db.commit()

        self._safe_audit(
            "record_product_document_delivery_started",
            delivery_id=delivery.id,
            package_id=delivery.package_id,
            organization_id=delivery.organization_id,
            product_key=delivery.product_key,
            attempt_number=attempt_n,
        )

        pkg = self._repo.get_package(delivery.package_id)
        if not pkg or not pkg.content_artifact_storage_object_id:
            return self._fail_delivery(
                delivery,
                attempt,
                error_code="package_missing",
                message="Package absent",
                retryable=False,
                started=started,
            )

        obj = self._db.get(ElfisStorageObject, pkg.content_artifact_storage_object_id)
        if not obj:
            return self._fail_delivery(
                delivery,
                attempt,
                error_code="artifact_missing",
                message="Artefact package absent",
                retryable=False,
                started=started,
            )

        from app.document_processing.validation.pipeline import read_json_artifact

        package_body = read_json_artifact(obj)
        bridge = self._bridges.get(delivery.bridge_key)
        pi_metrics.incr("product_delivery_claim_total")
        try:
            receipt = bridge.deliver(package_body, delivery.idempotency_key)
        except Exception:
            # Timeout / crash côté bridge après appel potentiel → unknown, pas failed
            return self._mark_unknown(
                delivery,
                attempt,
                error_code="bridge_uncertain",
                message="État distant incertain après erreur bridge",
                started=started,
                pkg=pkg,
                external_reference=None,
            )

        duration = int((datetime.utcnow() - started).total_seconds() * 1000)

        if receipt.status == "delivered":
            try:
                attempt.status = AttemptStatus.SUCCEEDED.value
                attempt.completed_at = datetime.utcnow()
                attempt.duration_ms = duration
                attempt.response_code = "ok"
                attempt.metadata_json = sanitize_metadata({"bridge_key": delivery.bridge_key})
                delivery.status = DeliveryStatus.DELIVERED.value
                delivery.external_reference = receipt.external_reference
                delivery.delivered_at = datetime.utcnow()
                delivery.locked_by = None
                delivery.locked_until = None
                pkg.status = PackageStatus.DELIVERED.value
                pkg.updated_at = datetime.utcnow()
                self._db.commit()
            except Exception:
                # Accusé reçu mais commit local échoue → unknown + ref
                return self._mark_unknown(
                    delivery,
                    attempt,
                    error_code="local_commit_failed",
                    message="Accusé distant reçu, commit local échoué",
                    started=started,
                    pkg=pkg,
                    external_reference=receipt.external_reference,
                )
            pi_metrics.incr("product_delivery_completed_total")
            pi_metrics.incr("deliveries_completed")
            self._safe_audit(
                "record_product_document_delivery_completed",
                delivery_id=delivery.id,
                package_id=pkg.id,
                organization_id=delivery.organization_id,
                product_key=delivery.product_key,
                bridge_version=delivery.bridge_version,
                status=delivery.status,
                attempt_number=attempt_n,
                duration_ms=duration,
                external_reference=receipt.external_reference,
            )
            if delivery.product_key == PRODUCT_COMPTAPILOT:
                self._safe_audit(
                    "record_comptapilot_document_published",
                    delivery_id=delivery.id,
                    package_id=pkg.id,
                    organization_id=delivery.organization_id,
                    product_key=delivery.product_key,
                    external_reference=receipt.external_reference,
                )
            return delivery

        if receipt.status == "validated_not_delivered":
            attempt.status = AttemptStatus.SUCCEEDED.value
            attempt.completed_at = datetime.utcnow()
            attempt.duration_ms = duration
            attempt.response_code = "dry_run"
            delivery.status = DeliveryStatus.VALIDATED_NOT_DELIVERED.value
            delivery.external_reference = receipt.external_reference
            delivery.locked_by = None
            delivery.locked_until = None
            delivery.last_error_code = None
            delivery.last_error_message_sanitized = sanitize_error_message(
                receipt.message_sanitized or "Dry-run — non publié"
            )
            pkg.status = PackageStatus.READY.value
            self._db.commit()
            self._safe_audit(
                "record_product_document_delivery_completed",
                delivery_id=delivery.id,
                package_id=pkg.id,
                organization_id=delivery.organization_id,
                product_key=delivery.product_key,
                status=delivery.status,
                attempt_number=attempt_n,
                duration_ms=duration,
                external_reference=receipt.external_reference,
            )
            return delivery

        if receipt.error_code == "duplicate_idempotent" and receipt.external_reference:
            # doublon contrôlé → aligner sur delivered / dry-run existant
            if receipt.status in ("delivered", "validated_not_delivered"):
                delivery.status = (
                    DeliveryStatus.DELIVERED.value
                    if receipt.status == "delivered"
                    else DeliveryStatus.VALIDATED_NOT_DELIVERED.value
                )
                delivery.external_reference = receipt.external_reference
                delivery.locked_by = None
                delivery.locked_until = None
                attempt.status = AttemptStatus.SUCCEEDED.value
                attempt.completed_at = datetime.utcnow()
                attempt.response_code = "duplicate_ok"
                if receipt.status == "delivered":
                    pkg.status = PackageStatus.DELIVERED.value
                self._db.commit()
                pi_metrics.incr("package_duplicate_prevented_total")
                return delivery

        if receipt.status == "blocked":
            attempt.status = AttemptStatus.FAILED.value
            attempt.completed_at = datetime.utcnow()
            attempt.duration_ms = duration
            attempt.error_code = receipt.error_code
            attempt.retryable = False
            delivery.status = DeliveryStatus.BLOCKED.value
            delivery.last_error_code = receipt.error_code
            delivery.last_error_message_sanitized = sanitize_error_message(receipt.message_sanitized)
            delivery.failed_at = datetime.utcnow()
            delivery.locked_by = None
            delivery.locked_until = None
            pkg.status = PackageStatus.DELIVERY_FAILED.value
            self._db.commit()
            self._safe_audit(
                "record_comptapilot_document_publish_failed",
                delivery_id=delivery.id,
                package_id=pkg.id,
                organization_id=delivery.organization_id,
                error_code=receipt.error_code,
            )
            return delivery

        if receipt.uncertain or receipt.status == "unknown":
            return self._mark_unknown(
                delivery,
                attempt,
                error_code=receipt.error_code or "remote_status_unknown",
                message=receipt.message_sanitized or "État distant inconnu",
                started=started,
                pkg=pkg,
                external_reference=receipt.external_reference,
            )

        retryable = bool(receipt.retryable)
        pi_metrics.incr("product_delivery_retry_total")
        return self._fail_delivery(
            delivery,
            attempt,
            error_code=receipt.error_code or "delivery_failed",
            message=receipt.message_sanitized or "Livraison échouée",
            retryable=retryable,
            started=started,
            pkg=pkg,
        )

    def _mark_unknown(
        self,
        delivery: ElfisProductDocumentDelivery,
        attempt: ElfisProductDocumentDeliveryAttempt,
        *,
        error_code: str,
        message: str,
        started: datetime,
        pkg: ElfisProductProcessingPackage | None,
        external_reference: str | None,
    ) -> ElfisProductDocumentDelivery:
        duration = int((datetime.utcnow() - started).total_seconds() * 1000)
        attempt.status = AttemptStatus.FAILED.value
        attempt.completed_at = datetime.utcnow()
        attempt.duration_ms = duration
        attempt.error_code = error_code
        attempt.retryable = False
        delivery.status = DeliveryStatus.UNKNOWN.value
        delivery.last_error_code = error_code
        delivery.last_error_message_sanitized = sanitize_error_message(message)
        if external_reference:
            delivery.external_reference = external_reference
        delivery.locked_by = None
        delivery.locked_until = None
        if pkg:
            pkg.status = PackageStatus.DELIVERY_PENDING.value
        self._db.commit()
        pi_metrics.incr("product_delivery_unknown_total")
        self._safe_audit(
            "record_product_document_delivery_failed",
            delivery_id=delivery.id,
            package_id=delivery.package_id,
            organization_id=delivery.organization_id,
            product_key=delivery.product_key,
            error_code=error_code,
            status=DeliveryStatus.UNKNOWN.value,
            attempt_number=delivery.attempt_count,
        )
        return delivery

    def reconcile_delivery(
        self,
        delivery_id: str,
        *,
        dry_run: bool = True,
    ) -> ElfisProductDocumentDelivery:
        delivery = self.get_delivery_platform(delivery_id)
        if delivery.status not in (
            DeliveryStatus.UNKNOWN.value,
            DeliveryStatus.DELIVERING.value,
            DeliveryStatus.MANUAL_REVIEW.value,
        ):
            raise ProductIntegrationValidationError("not_reconcilable", "Livraison non reconciliable")
        bridge = self._bridges.get(delivery.bridge_key)
        from app.product_integrations.registry import ProductReceipt

        probe = ProductReceipt(
            status="unknown",
            external_reference=delivery.external_reference,
            uncertain=True,
        )
        remote = bridge.get_delivery_status(probe)
        if dry_run:
            return delivery
        if remote.status == "delivered" and remote.external_reference:
            delivery.status = DeliveryStatus.DELIVERED.value
            delivery.external_reference = remote.external_reference
            delivery.delivered_at = datetime.utcnow()
            delivery.last_error_code = None
            pkg = self._repo.get_package(delivery.package_id)
            if pkg:
                pkg.status = PackageStatus.DELIVERED.value
            self._db.commit()
            self._safe_audit(
                "record_product_document_delivery_completed",
                delivery_id=delivery.id,
                package_id=delivery.package_id,
                organization_id=delivery.organization_id,
                product_key=delivery.product_key,
                status=delivery.status,
                external_reference=delivery.external_reference,
            )
            return delivery
        if remote.status == "validated_not_delivered":
            delivery.status = DeliveryStatus.VALIDATED_NOT_DELIVERED.value
            delivery.external_reference = remote.external_reference
            self._db.commit()
            return delivery
        if remote.uncertain or remote.status == "unknown":
            delivery.status = DeliveryStatus.MANUAL_REVIEW.value
            delivery.last_error_code = "manual_review_required"
            delivery.last_error_message_sanitized = sanitize_error_message(
                "Reconciliation — état distant inconnu"
            )
            self._db.commit()
            return delivery
        # confirmé absent et sûr → retry
        if delivery.attempt_count < delivery.max_attempts:
            delivery.status = DeliveryStatus.QUEUED.value
            delivery.next_retry_at = datetime.utcnow()
            pi_metrics.incr("product_delivery_retry_total")
        else:
            delivery.status = DeliveryStatus.BLOCKED.value
        self._db.commit()
        return delivery

    def _fail_delivery(
        self,
        delivery: ElfisProductDocumentDelivery,
        attempt: ElfisProductDocumentDeliveryAttempt,
        *,
        error_code: str,
        message: str,
        retryable: bool,
        started: datetime,
        pkg: ElfisProductProcessingPackage | None = None,
    ) -> ElfisProductDocumentDelivery:
        duration = int((datetime.utcnow() - started).total_seconds() * 1000)
        attempt.status = AttemptStatus.FAILED.value
        attempt.completed_at = datetime.utcnow()
        attempt.duration_ms = duration
        attempt.error_code = error_code
        attempt.retryable = retryable
        delivery.last_error_code = error_code
        delivery.last_error_message_sanitized = sanitize_error_message(message)
        delivery.locked_by = None
        delivery.locked_until = None
        pkg = pkg or self._repo.get_package(delivery.package_id)
        if retryable and delivery.attempt_count < delivery.max_attempts:
            initial = int(getattr(settings, "product_delivery_retry_initial_seconds", 10) or 10)
            max_s = int(getattr(settings, "product_delivery_retry_max_seconds", 300) or 300)
            delay = min(max_s, initial * (2 ** max(0, delivery.attempt_count - 1)))
            delivery.status = DeliveryStatus.RETRYING.value
            delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
            if pkg:
                pkg.status = PackageStatus.DELIVERY_PENDING.value
        else:
            delivery.status = DeliveryStatus.FAILED.value
            delivery.failed_at = datetime.utcnow()
            if pkg:
                pkg.status = PackageStatus.DELIVERY_FAILED.value
        self._db.commit()
        pi_metrics.incr("deliveries_failed")
        self._safe_audit(
            "record_product_document_delivery_failed",
            delivery_id=delivery.id,
            package_id=delivery.package_id,
            organization_id=delivery.organization_id,
            product_key=delivery.product_key,
            error_code=error_code,
            attempt_number=delivery.attempt_count,
            status=delivery.status,
        )
        return delivery

    def _store_package_artifact(
        self,
        *,
        organization_id: int,
        package_id: str,
        content: bytes,
        checksum: str,
    ) -> ElfisStorageObject:
        from app.document_processing.validation.pipeline import store_validation_artifact
        from app.document_processing.validation.policies import ValidationLimits

        limits = ValidationLimits.from_settings()
        return store_validation_artifact(
            self._db,
            organization_id=organization_id,
            validation_id=package_id,
            content=content,
            checksum=checksum,
            limits=limits,
        )

    def _safe_audit(self, method: str, **kwargs: Any) -> None:
        if not self._audit:
            return
        try:
            getattr(self._audit, method)(**{k: v for k, v in kwargs.items() if v is not None})
        except Exception:
            logger.debug("pi_audit_failed", exc_info=True)
