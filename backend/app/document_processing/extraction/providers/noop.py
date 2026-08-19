"""Provider noop — tests / staging, lecture texte optionnelle."""

from __future__ import annotations

import time

from app.document_processing.extraction.provider import (
    ExtractedFieldPayload,
    ExtractionProviderCapabilities,
    ExtractionProviderResult,
    ExtractionRequest,
    FieldEvidence,
)
from app.document_processing.extraction.types import PROVIDER_NOOP, FieldType


class NoopExtractionProvider:
    provider_key = PROVIDER_NOOP
    provider_version = "1.0.0"
    capabilities = ExtractionProviderCapabilities()
    supported_schemas = frozenset(
        {
            "generic_document_v1",
            "invoice_basic_v1",
            "quote_basic_v1",
            "receipt_basic_v1",
        }
    )
    supported_languages = frozenset({"fra", "eng"})
    requires_ocr_text = False
    supports_native_text = True
    supports_tables = False
    supports_line_items = False
    supports_confidence = True
    supports_evidence = True
    max_text_characters = 500_000

    async def extract(self, request: ExtractionRequest) -> ExtractionProviderResult:
        t0 = time.perf_counter()
        mode = (
            request.noop_mode
            or (request.options or {}).get("noop_mode")
            or "ok"
        )
        mode = str(mode).strip().lower()
        # ne lit pas source_text sauf mode read_source (tests)
        if mode == "read_source" and request.source_text:
            pass

        duration = int((time.perf_counter() - t0) * 1000)

        if mode == "retryable":
            return ExtractionProviderResult(
                success=False,
                provider_key=self.provider_key,
                provider_version=self.provider_version,
                retryable=True,
                error_code="noop_retryable",
                error_message_sanitized="Échec noop retryable",
                processing_duration_ms=duration,
            )
        if mode == "permanent":
            return ExtractionProviderResult(
                success=False,
                provider_key=self.provider_key,
                provider_version=self.provider_version,
                retryable=False,
                error_code="noop_permanent",
                error_message_sanitized="Échec noop permanent",
                processing_duration_ms=duration,
            )
        if mode == "timeout":
            return ExtractionProviderResult(
                success=False,
                provider_key=self.provider_key,
                provider_version=self.provider_version,
                retryable=True,
                error_code="noop_timeout",
                error_message_sanitized="Timeout noop simulé",
                processing_duration_ms=duration,
            )
        if mode == "empty":
            return ExtractionProviderResult(
                success=True,
                provider_key=self.provider_key,
                provider_version=self.provider_version,
                fields={},
                partially_completed=True,
                confidence_score=0.0,
                warnings=["noop_empty"],
                processing_duration_ms=duration,
            )
        if mode == "invalid":
            fields = {
                "invoice_number": ExtractedFieldPayload(
                    field_path="invoice_number",
                    field_type=FieldType.STRING.value,
                    value="???",
                    confidence=0.2,
                    status="extracted",
                    evidence=[FieldEvidence(evidence_code="NOOP", method="noop")],
                ),
                "total_amount": ExtractedFieldPayload(
                    field_path="total_amount",
                    field_type=FieldType.DECIMAL.value,
                    value="not-a-number",
                    confidence=0.1,
                    status="extracted",
                ),
            }
            return ExtractionProviderResult(
                success=True,
                provider_key=self.provider_key,
                provider_version=self.provider_version,
                fields=fields,
                partially_completed=True,
                confidence_score=0.15,
                warnings=["noop_invalid_fields"],
                processing_duration_ms=duration,
            )
        if mode == "partial":
            fields = {
                "invoice_number": ExtractedFieldPayload(
                    field_path="invoice_number",
                    field_type=FieldType.STRING.value,
                    value="F-NOOP-001",
                    normalized_value="F-NOOP-001",
                    confidence=0.9,
                    status="extracted",
                    evidence=[FieldEvidence(page=1, rule="noop", evidence_code="NOOP_PARTIAL")],
                ),
            }
            return ExtractionProviderResult(
                success=True,
                provider_key=self.provider_key,
                provider_version=self.provider_version,
                fields=fields,
                partially_completed=True,
                confidence_score=0.5,
                warnings=["noop_partial"],
                processing_duration_ms=duration,
            )

        # ok — champs valides selon schéma facture ou générique
        if request.schema_key == "invoice_basic_v1":
            fields = {
                "invoice_number": ExtractedFieldPayload(
                    field_path="invoice_number",
                    field_type=FieldType.STRING.value,
                    value="F-2026-001",
                    normalized_value="F-2026-001",
                    confidence=0.95,
                    status="extracted",
                    evidence=[FieldEvidence(page=1, rule="noop", evidence_code="NOOP_OK")],
                ),
                "issue_date": ExtractedFieldPayload(
                    field_path="issue_date",
                    field_type=FieldType.DATE.value,
                    value="2026-01-15",
                    normalized_value="2026-01-15",
                    confidence=0.9,
                    status="extracted",
                ),
                "supplier_name": ExtractedFieldPayload(
                    field_path="supplier_name",
                    field_type=FieldType.STRING.value,
                    value="Fournisseur Noop",
                    normalized_value="Fournisseur Noop",
                    confidence=0.85,
                    status="extracted",
                ),
                "currency": ExtractedFieldPayload(
                    field_path="currency",
                    field_type=FieldType.CURRENCY_CODE.value,
                    value="EUR",
                    normalized_value="EUR",
                    confidence=0.99,
                    status="extracted",
                ),
                "total_amount": ExtractedFieldPayload(
                    field_path="total_amount",
                    field_type=FieldType.DECIMAL.value,
                    value="1234.56",
                    normalized_value="1234.56",
                    confidence=0.88,
                    status="extracted",
                ),
            }
        else:
            fields = {
                "title": ExtractedFieldPayload(
                    field_path="title",
                    field_type=FieldType.STRING.value,
                    value="Document noop",
                    normalized_value="Document noop",
                    confidence=0.8,
                    status="extracted",
                ),
                "detected_language": ExtractedFieldPayload(
                    field_path="detected_language",
                    field_type=FieldType.STRING.value,
                    value="fra",
                    normalized_value="fra",
                    confidence=0.7,
                    status="extracted",
                ),
            }
        return ExtractionProviderResult(
            success=True,
            provider_key=self.provider_key,
            provider_version=self.provider_version,
            fields=fields,
            confidence_score=0.9,
            processing_duration_ms=duration,
        )
