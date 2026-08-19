"""ExtractionEligibilityService."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.document_analysis.enums import AnalysisReportStatus
from app.document_analysis.repository import DocumentAnalysisRepository
from app.document_extraction.enums import ExtractionStatus, IneligibilityReason
from app.document_extraction.exceptions import DocumentExtractionIneligibleError
from app.document_extraction.models import ElfisDocumentExtraction
from app.document_intake.enums import DocumentLifecycleStatus
from app.document_intake.models import ElfisDocumentIntakeItem


class ExtractionEligibilityService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._analysis = DocumentAnalysisRepository(db)

    def get_ineligibility_reasons(
        self,
        item: ElfisDocumentIntakeItem,
        *,
        organization_id: int,
        allow_running: bool = False,
    ) -> list[str]:
        reasons: list[str] = []
        if item.organization_id != organization_id:
            reasons.append(IneligibilityReason.ORGANIZATION_MISMATCH.value)
            return reasons

        status = item.lifecycle_status or item.status
        if status == DocumentLifecycleStatus.QUARANTINED.value:
            reasons.append(IneligibilityReason.DOCUMENT_QUARANTINED.value)
        if status == DocumentLifecycleStatus.REJECTED.value:
            reasons.append(IneligibilityReason.DOCUMENT_REJECTED.value)
        if status == DocumentLifecycleStatus.CANCELLED.value:
            reasons.append(IneligibilityReason.DOCUMENT_CANCELLED.value)

        allowed = {
            DocumentLifecycleStatus.READY_FOR_AI.value,
            DocumentLifecycleStatus.OCR_PENDING.value,
            DocumentLifecycleStatus.EXTRACTION_PENDING.value,
            DocumentLifecycleStatus.EXTRACTING.value,
            DocumentLifecycleStatus.EXTRACTED.value,
            DocumentLifecycleStatus.AWAITING_VALIDATION.value,
            DocumentLifecycleStatus.FAILED.value,
        }
        if status not in allowed and status != DocumentLifecycleStatus.READY_FOR_AI.value:
            if status not in (
                DocumentLifecycleStatus.READY_FOR_AI.value,
                DocumentLifecycleStatus.FAILED.value,
            ):
                reasons.append(IneligibilityReason.DOCUMENT_NOT_READY.value)

        if status not in (
            DocumentLifecycleStatus.READY_FOR_AI.value,
            DocumentLifecycleStatus.FAILED.value,
            DocumentLifecycleStatus.AWAITING_VALIDATION.value,
            DocumentLifecycleStatus.EXTRACTED.value,
            DocumentLifecycleStatus.OCR_PENDING.value,
        ):
            # Mid-extraction states ok for get; start requires ready_for_ai or failed
            pass

        report = self._analysis.get_latest_for_item(
            organization_id=organization_id, document_intake_item_id=item.id
        )
        if not report or report.status != AnalysisReportStatus.COMPLETED.value:
            reasons.append(IneligibilityReason.ANALYSIS_MISSING.value)

        running = (
            self._db.query(ElfisDocumentExtraction)
            .filter(ElfisDocumentExtraction.organization_id == organization_id)
            .filter(ElfisDocumentExtraction.document_intake_item_id == item.id)
            .filter(
                ElfisDocumentExtraction.status.in_(
                    [
                        ExtractionStatus.PENDING.value,
                        ExtractionStatus.QUEUED.value,
                        ExtractionStatus.PREPARING.value,
                        ExtractionStatus.EXTRACTING.value,
                        ExtractionStatus.NORMALIZING.value,
                        ExtractionStatus.RECONCILING.value,
                        ExtractionStatus.VALIDATING.value,
                    ]
                )
            )
            .first()
        )
        if running and not allow_running:
            reasons.append(IneligibilityReason.EXTRACTION_ALREADY_RUNNING.value)

        return reasons

    def is_eligible(
        self,
        item: ElfisDocumentIntakeItem,
        *,
        organization_id: int,
        for_start: bool = True,
    ) -> bool:
        reasons = self.get_ineligibility_reasons(
            item, organization_id=organization_id, allow_running=not for_start
        )
        if for_start:
            status = item.lifecycle_status or item.status
            if status not in (
                DocumentLifecycleStatus.READY_FOR_AI.value,
                DocumentLifecycleStatus.FAILED.value,
            ):
                if IneligibilityReason.DOCUMENT_NOT_READY.value not in reasons:
                    # awaiting_validation already done — start only with force elsewhere
                    if status != DocumentLifecycleStatus.READY_FOR_AI.value:
                        reasons.append(IneligibilityReason.DOCUMENT_NOT_READY.value)
            # Filter ANALYSIS / QUARANTINE etc.
            hard = {
                IneligibilityReason.ORGANIZATION_MISMATCH.value,
                IneligibilityReason.DOCUMENT_QUARANTINED.value,
                IneligibilityReason.DOCUMENT_REJECTED.value,
                IneligibilityReason.DOCUMENT_CANCELLED.value,
                IneligibilityReason.ANALYSIS_MISSING.value,
                IneligibilityReason.EXTRACTION_ALREADY_RUNNING.value,
                IneligibilityReason.DOCUMENT_NOT_READY.value,
            }
            return not any(r in hard for r in reasons)
        return not reasons

    def assert_eligible(
        self,
        item: ElfisDocumentIntakeItem,
        *,
        organization_id: int,
        for_start: bool = True,
    ) -> None:
        reasons = self.get_ineligibility_reasons(
            item, organization_id=organization_id, allow_running=False
        )
        status = item.lifecycle_status or item.status
        if for_start and status not in (
            DocumentLifecycleStatus.READY_FOR_AI.value,
            DocumentLifecycleStatus.FAILED.value,
        ):
            if IneligibilityReason.DOCUMENT_NOT_READY.value not in reasons:
                reasons.append(IneligibilityReason.DOCUMENT_NOT_READY.value)
        hard = [
            r
            for r in reasons
            if r
            in {
                IneligibilityReason.ORGANIZATION_MISMATCH.value,
                IneligibilityReason.DOCUMENT_QUARANTINED.value,
                IneligibilityReason.DOCUMENT_REJECTED.value,
                IneligibilityReason.DOCUMENT_CANCELLED.value,
                IneligibilityReason.ANALYSIS_MISSING.value,
                IneligibilityReason.EXTRACTION_ALREADY_RUNNING.value,
                IneligibilityReason.DOCUMENT_NOT_READY.value,
            }
        ]
        if hard:
            raise DocumentExtractionIneligibleError(
                hard[0], f"Document non éligible: {', '.join(hard)}"
            )
