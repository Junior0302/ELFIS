"""Contrat OCRProvider + capacités."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class OCRProviderCapabilities:
    pdf: bool = False
    images: bool = False
    multipage: bool = False
    native_text: bool = False
    confidence: bool = False
    bounding_boxes: bool = False
    tables: bool = False
    handwriting: bool = False
    language_detection: bool = False
    orientation_detection: bool = False


@dataclass
class OCRRequest:
    document_id: str
    document_version_id: str
    mime_type: str
    language_hints: list[str] = field(default_factory=list)
    page_range: tuple[int, int] | None = None
    temp_path: Path | None = None
    options: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    max_pages: int = 50
    max_page_characters: int = 50_000
    max_text_characters: int = 500_000
    # modes de test noop
    noop_mode: str | None = None


@dataclass
class OCRPagePayload:
    page_number: int
    text: str = ""
    confidence: float | None = None
    detected_language: str | None = None
    rotation_degrees: float | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class OCRProviderResult:
    success: bool
    provider_key: str
    provider_version: str
    extraction_method: str
    pages: list[OCRPagePayload] = field(default_factory=list)
    detected_languages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    processing_duration_ms: int = 0
    retryable: bool = False
    error_code: str | None = None
    error_message_sanitized: str | None = None
    partially_completed: bool = False


class OCRProvider(Protocol):
    provider_key: str
    provider_version: str
    capabilities: OCRProviderCapabilities
    supported_mime_types: tuple[str, ...]
    supported_languages: tuple[str, ...]
    max_pages: int
    max_file_size_bytes: int

    async def recognize(self, request: OCRRequest) -> OCRProviderResult: ...

    def health(self) -> dict[str, Any]: ...
