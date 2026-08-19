"""Extracteur TXT."""

from __future__ import annotations

from pathlib import Path

from app.document_intelligence.document_exceptions import DocumentValidationError
from app.document_intelligence.document_quality import calculate_quality, normalize_text
from app.document_intelligence.document_schemas import DocumentExtractionOutput
from app.document_intelligence.document_security import looks_like_binary
from app.document_intelligence.document_types import ExtractorNames
from app.document_intelligence.extractors.base import DocumentTextExtractor


class PlainTextExtractor(DocumentTextExtractor):
    extractor_name = ExtractorNames.PLAIN_TEXT
    extractor_version = "utf8-v1"
    supported_mime_types = {"text/plain"}

    def extract(self, *, path: Path, mime_type: str, filename: str) -> DocumentExtractionOutput:
        content = path.read_bytes()
        if looks_like_binary(content):
            raise DocumentValidationError("Fichier TXT binaire refusé")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception as exc:
                raise DocumentValidationError("Encodage texte illisible") from exc

        text = normalize_text(text)
        quality = calculate_quality(text, page_count=1)
        return DocumentExtractionOutput(
            text=text,
            page_count=1,
            language=None,
            quality_score=float(quality["quality_score"]),
            confidence=float(quality["confidence"]),
            requires_ocr=False,
            requires_review=bool(quality["requires_review"]),
            metadata={"filename": filename, "engine": "plain_text", **(quality.get("metrics") or {})},
            warnings=list(quality.get("warnings") or []),
        )
