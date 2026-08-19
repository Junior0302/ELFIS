"""Validation de schéma — pas de validation comptable."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.document_processing.extraction.normalization import ExtractionNormalizationService
from app.document_processing.extraction.provider import ExtractedFieldPayload
from app.document_processing.extraction.schema_registry import ExtractionSchemaDef
from app.document_processing.extraction.types import FieldType


@dataclass
class SchemaValidationResult:
    valid: bool
    missing_required_fields: list[str] = field(default_factory=list)
    invalid_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    validation_codes: list[str] = field(default_factory=list)
    requires_review: bool = False
    normalized_fields: dict[str, ExtractedFieldPayload] = field(default_factory=dict)

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "missing_required_fields": list(self.missing_required_fields),
            "invalid_fields": list(self.invalid_fields),
            "warnings": list(self.warnings)[:20],
            "validation_codes": list(self.validation_codes)[:30],
            "requires_review": self.requires_review,
        }


class ExtractionSchemaValidator:
    def __init__(self) -> None:
        self._norm = ExtractionNormalizationService()

    def validate(
        self,
        schema: ExtractionSchemaDef,
        fields: dict[str, ExtractedFieldPayload],
        *,
        max_fields: int = 100,
        max_field_length: int = 2000,
        review_threshold: float = 0.80,
    ) -> SchemaValidationResult:
        result = SchemaValidationResult(valid=True)
        fmap = schema.field_map()
        out: dict[str, ExtractedFieldPayload] = {}

        if len(fields) > max_fields:
            result.valid = False
            result.validation_codes.append("too_many_fields")
            result.warnings.append("too_many_fields")

        # champs inconnus
        for path in fields:
            if path not in fmap:
                result.warnings.append(f"unknown_field:{path}")
                result.validation_codes.append("unknown_field")

        for fdef in schema.fields:
            payload = fields.get(fdef.path)
            if payload is None or payload.value is None or payload.value == "":
                if fdef.required:
                    result.missing_required_fields.append(fdef.path)
                    result.valid = False
                    result.validation_codes.append(f"missing:{fdef.path}")
                continue
            try:
                normalized, ambiguous = self._normalize_typed(
                    fdef.field_type, payload.value, max_len=min(fdef.max_length, max_field_length)
                )
            except ValueError as exc:
                result.invalid_fields.append(fdef.path)
                result.valid = False
                result.validation_codes.append(f"invalid:{fdef.path}:{exc}")
                payload.status = "invalid"
                payload.validation_codes = list(payload.validation_codes or []) + [str(exc)]
                out[fdef.path] = payload
                continue

            if ambiguous:
                result.requires_review = True
                result.warnings.append(f"ambiguous_date:{fdef.path}")
                result.validation_codes.append(f"ambiguous:{fdef.path}")
                payload.status = "invalid"
                result.invalid_fields.append(fdef.path)
                result.valid = False

            payload.normalized_value = normalized
            payload.field_type = fdef.field_type.value
            if payload.status == "extracted" and not ambiguous:
                payload.status = "extracted"
            conf = payload.confidence
            if conf is not None and conf < review_threshold:
                result.requires_review = True
                result.validation_codes.append(f"low_confidence:{fdef.path}")
            out[fdef.path] = payload

        # warning non bloquant cohérence montants (pas validation comptable)
        self._amount_consistency_warning(out, result)

        if schema.human_review_mandatory:
            result.requires_review = True

        if result.missing_required_fields or result.invalid_fields:
            result.valid = False

        result.normalized_fields = out
        return result

    def _normalize_typed(
        self, ftype: FieldType, value: Any, *, max_len: int
    ) -> tuple[Any, bool]:
        if ftype == FieldType.STRING:
            return self._norm.normalize_string(value, max_len=max_len), False
        if ftype == FieldType.DECIMAL:
            return self._norm.normalize_decimal(value), False
        if ftype == FieldType.PERCENTAGE:
            return self._norm.normalize_percentage(value), False
        if ftype == FieldType.CURRENCY_CODE:
            return self._norm.normalize_currency(value), False
        if ftype == FieldType.DATE:
            return self._norm.normalize_date(value)
        if ftype == FieldType.INTEGER:
            return self._norm.normalize_integer(value), False
        if ftype == FieldType.BOOLEAN:
            return self._norm.normalize_boolean(value), False
        if ftype == FieldType.ENUM:
            s = self._norm.normalize_string(value, max_len=max_len)
            return s, False
        if ftype in (FieldType.OBJECT, FieldType.ARRAY):
            return value, False
        return self._norm.normalize_string(value, max_len=max_len), False

    def _amount_consistency_warning(
        self, fields: dict[str, ExtractedFieldPayload], result: SchemaValidationResult
    ) -> None:
        try:
            sub = fields.get("subtotal")
            tax = fields.get("tax_amount")
            tot = fields.get("total_amount")
            if not (sub and tax and tot):
                return
            if sub.normalized_value is None or tax.normalized_value is None or tot.normalized_value is None:
                return
            s = Decimal(str(sub.normalized_value))
            t = Decimal(str(tax.normalized_value))
            tot_v = Decimal(str(tot.normalized_value))
            if abs((s + t) - tot_v) > Decimal("0.05"):
                result.warnings.append("amount_sum_mismatch")
                result.validation_codes.append("amount_sum_mismatch")
                result.requires_review = True
        except Exception:
            return
