"""Sélection schéma + source texte OCR."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.config import settings
from app.document_processing.extraction.exceptions import ExtractionValidationError
from app.document_processing.extraction.schema_registry import (
    DocumentExtractionSchemaRegistry,
    get_extraction_schema_registry,
)
from app.document_processing.extraction.types import (
    SCHEMA_GENERIC_V1,
    SCHEMA_INVOICE_BASIC_V1,
    SCHEMA_QUOTE_BASIC_V1,
    SCHEMA_RECEIPT_BASIC_V1,
)
from app.document_processing.ocr.models import ElfisDocumentOCRResult
from app.document_processing.ocr.types import OCRResultStatus


@dataclass
class SchemaSelection:
    schema_key: str
    schema_version: str
    reason_code: str
    classification_id: str | None = None
    requires_review: bool = False
    effective_document_type: str | None = None


@dataclass
class SourceSelection:
    ocr_result_id: str
    reason_code: str
    extraction_method: str | None = None
    fallback_chain: list[str] = field(default_factory=list)


class ExtractionSchemaSelectionService:
    def __init__(self, registry: DocumentExtractionSchemaRegistry | None = None) -> None:
        self._reg = registry or get_extraction_schema_registry()

    def select(
        self,
        *,
        effective_document_type: str | None,
        classification_id: str | None = None,
        classification_confirmed: bool = False,
        classification_requires_review: bool = False,
    ) -> SchemaSelection:
        dtype = (effective_document_type or "unknown").strip().lower()
        generic_key = (
            getattr(settings, "document_extraction_default_generic_schema", None) or SCHEMA_GENERIC_V1
        ).strip()

        mapping = {
            "invoice": SCHEMA_INVOICE_BASIC_V1,
            "supplier_invoice": SCHEMA_INVOICE_BASIC_V1,
            "customer_invoice": SCHEMA_INVOICE_BASIC_V1,
            "credit_note": SCHEMA_INVOICE_BASIC_V1,
            "quote": SCHEMA_QUOTE_BASIC_V1,
            "receipt": SCHEMA_RECEIPT_BASIC_V1,
            "expense_report": SCHEMA_RECEIPT_BASIC_V1,
        }

        if dtype == "invoice" and classification_requires_review and not classification_confirmed:
            # type ambigu → générique + revue (ne pas forcer facture sur un montant seul)
            schema = self._reg.latest(generic_key)
            return SchemaSelection(
                schema_key=schema.schema_key,
                schema_version=schema.schema_version,
                reason_code="ambiguous_invoice_type",
                classification_id=classification_id,
                requires_review=True,
                effective_document_type=dtype,
            )

        key = mapping.get(dtype)
        if key:
            schema = self._reg.latest(key)
            reason = "confirmed_type" if classification_confirmed else "effective_type"
            return SchemaSelection(
                schema_key=schema.schema_key,
                schema_version=schema.schema_version,
                reason_code=reason,
                classification_id=classification_id,
                requires_review=schema.human_review_mandatory or classification_requires_review,
                effective_document_type=dtype,
            )

        schema = self._reg.latest(generic_key)
        return SchemaSelection(
            schema_key=schema.schema_key,
            schema_version=schema.schema_version,
            reason_code="unknown_or_generic",
            classification_id=classification_id,
            requires_review=True,
            effective_document_type=dtype,
        )


class ExtractionSourceSelectionService:
    """Sélectionne un OCRResult de la même version — jamais d'autre version."""

    ALLOWED_STATUSES = frozenset(
        {
            OCRResultStatus.COMPLETED.value,
            OCRResultStatus.PARTIALLY_COMPLETED.value,
        }
    )

    def __init__(self, db: Session) -> None:
        self._db = db

    def select(
        self,
        *,
        organization_id: int,
        document_id: str,
        document_version_id: str,
    ) -> SourceSelection:
        chain: list[str] = []
        rows = (
            self._db.query(ElfisDocumentOCRResult)
            .filter(
                ElfisDocumentOCRResult.organization_id == organization_id,
                ElfisDocumentOCRResult.document_id == document_id,
                ElfisDocumentOCRResult.document_version_id == document_version_id,
            )
            .order_by(ElfisDocumentOCRResult.created_at.desc())
            .all()
        )
        if not rows:
            raise ExtractionValidationError("ocr_source_missing", "Aucun OCRResult pour cette version")

        preferred = None
        for row in rows:
            chain.append(f"{row.id}:{row.status}:{row.extraction_method}")
            if row.status == OCRResultStatus.REJECTED.value:
                continue
            if row.status == OCRResultStatus.SUPERSEDED.value:
                continue
            if not row.text_artifact_storage_object_id:
                continue
            if row.status not in self.ALLOWED_STATUSES:
                continue
            # priorité: completed > partial ; native_pdf_text acceptable
            if preferred is None:
                preferred = row
            if row.status == OCRResultStatus.COMPLETED.value:
                preferred = row
                break

        if preferred is None:
            raise ExtractionValidationError(
                "ocr_source_unavailable",
                "Aucun OCRResult utilisable (rejeté/purgé/incomplet)",
            )

        reason = "ocr_completed"
        if preferred.extraction_method == "native_pdf_text":
            reason = "native_pdf_text"
        elif preferred.status == OCRResultStatus.PARTIALLY_COMPLETED.value:
            reason = "ocr_partial"

        return SourceSelection(
            ocr_result_id=preferred.id,
            reason_code=reason,
            extraction_method=preferred.extraction_method,
            fallback_chain=chain[:10],
        )
