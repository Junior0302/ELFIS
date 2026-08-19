"""Provider rules — extraction déterministe par regex bornées, aucun ML/réseau."""

from __future__ import annotations

import re
import time

from app.document_processing.extraction.normalization import ExtractionNormalizationService
from app.document_processing.extraction.provider import (
    ExtractedFieldPayload,
    ExtractionProviderCapabilities,
    ExtractionProviderResult,
    ExtractionRequest,
    FieldEvidence,
)
from app.document_processing.extraction.types import PROVIDER_RULES, FieldType

# Regex bornées (pas de backtracking catastrophique)
_INV_NUM = re.compile(
    r"(?i)(?:facture|invoice|n[°o]\.?|num(?:ero|éro)?)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/]{2,40})"
)
_QUOTE_NUM = re.compile(
    r"(?i)(?:devis|quote|proposition)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/]{2,40})"
)
_DATE_LABEL = re.compile(
    r"(?i)(?:date(?:\s+d['e]\s*(?:émission|facture|émission))?|issue\s*date|du)\s*[: ]\s*"
    r"(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{4}-\d{2}-\d{2})"
)
_DUE_LABEL = re.compile(
    r"(?i)(?:échéance|due\s*date|payable\s+avant)\s*[: ]\s*"
    r"(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{4}-\d{2}-\d{2})"
)
_TOTAL = re.compile(
    r"(?i)(?:total\s*ttc|montant\s*ttc|total\s*amount|net\s*à\s*payer)\s*[: ]\s*"
    r"([0-9][0-9\s\u00a0.,]{0,20})"
)
_HT = re.compile(
    r"(?i)(?:total\s*ht|montant\s*ht|subtotal|hors\s*taxe)\s*[: ]\s*"
    r"([0-9][0-9\s\u00a0.,]{0,20})"
)
_TVA_AMT = re.compile(
    r"(?i)(?:montant\s*tva|tax\s*amount|tva)\s*[: ]\s*([0-9][0-9\s\u00a0.,]{0,20})"
)
_TVA_RATE = re.compile(r"(?i)(?:tva|vat|tax)\s*(?:à\s*)?(\d{1,2}(?:[.,]\d{1,2})?)\s*%")
_CURRENCY = re.compile(r"(?i)\b(EUR|USD|GBP|CHF|€|\$|£)\b")
_SUPPLIER = re.compile(
    r"(?i)(?:fournisseur|supplier|émetteur|issuer)\s*[: ]\s*([^\n\r]{3,80})"
)
_CUSTOMER = re.compile(
    r"(?i)(?:client|customer|destinataire)\s*[: ]\s*([^\n\r]{3,80})"
)
_MERCHANT = re.compile(
    r"(?i)(?:commerçant|merchant|magasin)\s*[: ]\s*([^\n\r]{3,80})"
)


class RulesDocumentExtractionProvider:
    provider_key = PROVIDER_RULES
    provider_version = "1.0.0"
    capabilities = ExtractionProviderCapabilities(confidence=True, evidence=True)
    supported_schemas = frozenset(
        {
            "generic_document_v1",
            "invoice_basic_v1",
            "quote_basic_v1",
            "receipt_basic_v1",
        }
    )
    supported_languages = frozenset({"fra", "eng"})
    requires_ocr_text = True
    supports_native_text = True
    supports_tables = False
    supports_line_items = False
    supports_confidence = True
    supports_evidence = True
    max_text_characters = 500_000

    def __init__(self) -> None:
        self._norm = ExtractionNormalizationService()

    async def extract(self, request: ExtractionRequest) -> ExtractionProviderResult:
        t0 = time.perf_counter()
        text = request.source_text or ""
        if len(text) > request.max_text_characters:
            return ExtractionProviderResult(
                success=False,
                provider_key=self.provider_key,
                provider_version=self.provider_version,
                retryable=False,
                error_code="source_too_large",
                error_message_sanitized="Texte source trop long",
                processing_duration_ms=int((time.perf_counter() - t0) * 1000),
            )

        # tronque pour scan regex (sécurité)
        scan = text[: min(len(text), request.max_text_characters, 200_000)]
        fields: dict[str, ExtractedFieldPayload] = {}
        warnings: list[str] = []

        if request.schema_key == "invoice_basic_v1":
            self._put_match(fields, "invoice_number", FieldType.STRING, _INV_NUM, scan, "invoice_number_label_v1")
            self._put_date(fields, "issue_date", _DATE_LABEL, scan, "issue_date_label_v1")
            self._put_date(fields, "due_date", _DUE_LABEL, scan, "due_date_label_v1")
            self._put_match(fields, "supplier_name", FieldType.STRING, _SUPPLIER, scan, "supplier_label_v1")
            self._put_match(fields, "customer_name", FieldType.STRING, _CUSTOMER, scan, "customer_label_v1")
            self._put_currency(fields, scan)
            self._put_amount(fields, "total_amount", _TOTAL, scan, "total_ttc_label_v1")
            self._put_amount(fields, "subtotal", _HT, scan, "total_ht_label_v1")
            self._put_amount(fields, "tax_amount", _TVA_AMT, scan, "tax_amount_label_v1")
            self._put_pct(fields, "tax_rate", _TVA_RATE, scan, "tax_rate_label_v1")
        elif request.schema_key == "quote_basic_v1":
            self._put_match(fields, "quote_number", FieldType.STRING, _QUOTE_NUM, scan, "quote_number_label_v1")
            self._put_date(fields, "issue_date", _DATE_LABEL, scan, "issue_date_label_v1")
            self._put_match(fields, "issuer_name", FieldType.STRING, _SUPPLIER, scan, "issuer_label_v1")
            self._put_match(fields, "customer_name", FieldType.STRING, _CUSTOMER, scan, "customer_label_v1")
            self._put_currency(fields, scan)
            self._put_amount(fields, "total_amount", _TOTAL, scan, "total_ttc_label_v1")
            self._put_amount(fields, "subtotal", _HT, scan, "total_ht_label_v1")
            self._put_amount(fields, "tax_amount", _TVA_AMT, scan, "tax_amount_label_v1")
        elif request.schema_key == "receipt_basic_v1":
            self._put_match(fields, "merchant_name", FieldType.STRING, _MERCHANT, scan, "merchant_label_v1")
            self._put_date(fields, "transaction_date", _DATE_LABEL, scan, "txn_date_label_v1")
            self._put_amount(fields, "total_amount", _TOTAL, scan, "total_label_v1")
            self._put_amount(fields, "tax_amount", _TVA_AMT, scan, "tax_amount_label_v1")
            self._put_currency(fields, scan)
        else:
            # generic
            if scan.strip():
                first = scan.strip().splitlines()[0][:200]
                fields["title"] = ExtractedFieldPayload(
                    field_path="title",
                    field_type=FieldType.STRING.value,
                    value=first,
                    confidence=0.4,
                    status="extracted",
                    evidence=[FieldEvidence(page=1, rule="first_line_v1", evidence_code="FIRST_LINE")],
                )
            self._put_date(fields, "document_date", _DATE_LABEL, scan, "doc_date_label_v1")
            fields["detected_language"] = ExtractedFieldPayload(
                field_path="detected_language",
                field_type=FieldType.STRING.value,
                value="fra" if re.search(r"(?i)\b(facture|devis|total)\b", scan) else "eng",
                confidence=0.5,
                status="extracted",
                evidence=[FieldEvidence(rule="lang_heuristic_v1", evidence_code="LANG_HEURISTIC")],
            )

        if not fields:
            warnings.append("no_rules_match")

        confs = [f.confidence for f in fields.values() if f.confidence is not None]
        avg = sum(confs) / len(confs) if confs else 0.0
        duration = int((time.perf_counter() - t0) * 1000)
        return ExtractionProviderResult(
            success=True,
            provider_key=self.provider_key,
            provider_version=self.provider_version,
            fields=fields,
            warnings=warnings,
            confidence_score=round(avg, 2) if confs else None,
            partially_completed=len(fields) < 3,
            processing_duration_ms=duration,
        )

    def _put_match(
        self,
        fields: dict[str, ExtractedFieldPayload],
        path: str,
        ftype: FieldType,
        pattern: re.Pattern[str],
        text: str,
        rule: str,
    ) -> None:
        m = pattern.search(text)
        if not m:
            return
        val = m.group(1).strip()[:200]
        fields[path] = ExtractedFieldPayload(
            field_path=path,
            field_type=ftype.value,
            value=val,
            confidence=0.75,
            status="extracted",
            evidence=[FieldEvidence(page=1, rule=rule, evidence_code="LABEL_MATCH", method="rules")],
        )

    def _put_date(
        self,
        fields: dict[str, ExtractedFieldPayload],
        path: str,
        pattern: re.Pattern[str],
        text: str,
        rule: str,
    ) -> None:
        m = pattern.search(text)
        if not m:
            return
        fields[path] = ExtractedFieldPayload(
            field_path=path,
            field_type=FieldType.DATE.value,
            value=m.group(1).strip(),
            confidence=0.7,
            status="extracted",
            evidence=[FieldEvidence(page=1, rule=rule, evidence_code="DATE_LABEL", method="rules")],
        )

    def _put_amount(
        self,
        fields: dict[str, ExtractedFieldPayload],
        path: str,
        pattern: re.Pattern[str],
        text: str,
        rule: str,
    ) -> None:
        m = pattern.search(text)
        if not m:
            return
        raw = m.group(1).strip()
        try:
            norm = self._norm.normalize_decimal(raw)
        except ValueError:
            return
        fields[path] = ExtractedFieldPayload(
            field_path=path,
            field_type=FieldType.DECIMAL.value,
            value=raw,
            normalized_value=str(norm),
            confidence=0.8,
            status="extracted",
            evidence=[FieldEvidence(page=1, rule=rule, evidence_code="AMOUNT_LABEL", method="rules")],
        )

    def _put_pct(
        self,
        fields: dict[str, ExtractedFieldPayload],
        path: str,
        pattern: re.Pattern[str],
        text: str,
        rule: str,
    ) -> None:
        m = pattern.search(text)
        if not m:
            return
        raw = m.group(1)
        try:
            norm = self._norm.normalize_percentage(raw + "%")
        except ValueError:
            return
        fields[path] = ExtractedFieldPayload(
            field_path=path,
            field_type=FieldType.PERCENTAGE.value,
            value=raw,
            normalized_value=str(norm),
            confidence=0.75,
            status="extracted",
            evidence=[FieldEvidence(page=1, rule=rule, evidence_code="PCT_LABEL", method="rules")],
        )

    def _put_currency(self, fields: dict[str, ExtractedFieldPayload], text: str) -> None:
        m = _CURRENCY.search(text)
        if not m:
            return
        raw = m.group(1)
        try:
            code = self._norm.normalize_currency(raw)
        except ValueError:
            return
        fields["currency"] = ExtractedFieldPayload(
            field_path="currency",
            field_type=FieldType.CURRENCY_CODE.value,
            value=raw,
            normalized_value=code,
            confidence=0.85,
            status="extracted",
            evidence=[
                FieldEvidence(page=1, rule="currency_token_v1", evidence_code="CURRENCY_TOKEN", method="rules")
            ],
        )
