"""Registre providers extraction."""

from __future__ import annotations

from app.config import settings
from app.document_processing.extraction.exceptions import ExtractionValidationError
from app.document_processing.extraction.provider import DocumentExtractionProvider
from app.document_processing.extraction.providers.noop import NoopExtractionProvider
from app.document_processing.extraction.providers.rules import RulesDocumentExtractionProvider
from app.document_processing.extraction.types import PROVIDER_NOOP, PROVIDER_RULES


class ExtractionProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, DocumentExtractionProvider] = {}

    def register(self, provider: DocumentExtractionProvider) -> None:
        self._providers[provider.provider_key] = provider

    def get(self, key: str) -> DocumentExtractionProvider:
        p = self._providers.get(key)
        if not p:
            raise ExtractionValidationError("provider_unknown", f"Provider inconnu: {key}")
        return p

    def configured(self) -> DocumentExtractionProvider:
        key = (getattr(settings, "document_extraction_provider", None) or PROVIDER_NOOP).strip().lower()
        if key in ("external", "openai", "ai"):
            raise ExtractionValidationError(
                "provider_disabled",
                "Provider externe/IA non activé dans RC2.5.4",
            )
        return self.get(key)

    def list_public(self) -> list[dict]:
        out = []
        for p in self._providers.values():
            out.append(
                {
                    "key": p.provider_key,
                    "version": p.provider_version,
                    "available": True,
                    "capabilities": {
                        "tables": p.supports_tables,
                        "line_items": p.supports_line_items,
                        "confidence": p.supports_confidence,
                        "evidence": p.supports_evidence,
                        "ocr_text": p.requires_ocr_text or p.capabilities.ocr_text,
                        "native_text": p.supports_native_text,
                    },
                    "supported_schemas": sorted(p.supported_schemas),
                    "supported_languages": sorted(p.supported_languages),
                    "max_text_characters": p.max_text_characters,
                }
            )
        return out


def build_default_extraction_provider_registry() -> ExtractionProviderRegistry:
    reg = ExtractionProviderRegistry()
    reg.register(NoopExtractionProvider())
    if getattr(settings, "document_extraction_rules_enabled", True):
        reg.register(RulesDocumentExtractionProvider())
    return reg


_REG: ExtractionProviderRegistry | None = None


def get_extraction_provider_registry() -> ExtractionProviderRegistry:
    global _REG
    if _REG is None:
        _REG = build_default_extraction_provider_registry()
    return _REG


def reset_extraction_provider_registry_for_tests() -> None:
    global _REG
    _REG = None
