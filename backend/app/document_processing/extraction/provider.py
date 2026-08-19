"""Contrat ExtractionProvider — n'écrit ni en DB ni Storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol


@dataclass(frozen=True)
class ExtractionProviderCapabilities:
    tables: bool = False
    line_items: bool = False
    confidence: bool = True
    evidence: bool = True
    native_text: bool = True
    ocr_text: bool = True


@dataclass
class ExtractionRequest:
    document_id: str
    document_version_id: str
    organization_id: int
    schema_key: str
    schema_version: str
    effective_document_type: str | None
    source_text: str
    page_metadata: list[dict[str, Any]] = field(default_factory=list)
    language_hints: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    max_text_characters: int = 500_000
    noop_mode: str | None = None


@dataclass
class FieldEvidence:
    page: int | None = None
    rule: str | None = None
    evidence_code: str | None = None
    method: str | None = None


@dataclass
class ExtractedFieldPayload:
    field_path: str
    field_type: str
    value: Any = None
    normalized_value: Any = None
    confidence: float | None = None
    status: str = "extracted"
    evidence: list[FieldEvidence] = field(default_factory=list)
    validation_codes: list[str] = field(default_factory=list)

    def to_public_dict(self) -> dict[str, Any]:
        """Sérialisation artefact — Decimal → str."""
        def _ser(v: Any) -> Any:
            if isinstance(v, Decimal):
                return str(v)
            return v

        return {
            "value": _ser(self.value),
            "normalized_value": _ser(self.normalized_value),
            "confidence": self.confidence,
            "status": self.status,
            "field_type": self.field_type,
            "evidence": [
                {
                    k: v
                    for k, v in {
                        "page": e.page,
                        "rule": e.rule,
                        "evidence_code": e.evidence_code,
                        "method": e.method,
                    }.items()
                    if v is not None
                }
                for e in (self.evidence or [])[:5]
            ],
            "validation_codes": list(self.validation_codes or [])[:10],
        }


@dataclass
class ExtractionProviderResult:
    success: bool
    provider_key: str
    provider_version: str
    fields: dict[str, ExtractedFieldPayload] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    processing_duration_ms: int = 0
    retryable: bool = False
    error_code: str | None = None
    error_message_sanitized: str | None = None
    partially_completed: bool = False
    confidence_score: float | None = None


class DocumentExtractionProvider(Protocol):
    provider_key: str
    provider_version: str
    capabilities: ExtractionProviderCapabilities
    supported_schemas: frozenset[str]
    supported_languages: frozenset[str]
    requires_ocr_text: bool
    supports_native_text: bool
    supports_tables: bool
    supports_line_items: bool
    supports_confidence: bool
    supports_evidence: bool
    max_text_characters: int

    async def extract(self, request: ExtractionRequest) -> ExtractionProviderResult: ...
