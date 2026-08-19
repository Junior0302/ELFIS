"""Extracteur PDF — couche texte native via pypdf (déjà installé)."""

from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.document_intelligence.document_exceptions import DocumentValidationError
from app.document_intelligence.document_quality import calculate_quality, normalize_text
from app.document_intelligence.document_schemas import DocumentExtractionOutput
from app.document_intelligence.document_types import ExtractorNames
from app.document_intelligence.extractors.base import DocumentTextExtractor


class PdfTextExtractor(DocumentTextExtractor):
    extractor_name = ExtractorNames.PDF_TEXT
    extractor_version = "pypdf-v1"
    supported_mime_types = {"application/pdf"}

    def extract(self, *, path: Path, mime_type: str, filename: str) -> DocumentExtractionOutput:
        from pypdf import PdfReader

        max_pages = max(1, int(settings.elfis_document_max_pages))
        try:
            reader = PdfReader(str(path))
        except Exception as exc:
            raise DocumentValidationError("PDF illisible") from exc

        total_pages = len(reader.pages)
        if total_pages > max_pages:
            raise DocumentValidationError(
                f"PDF trop paginé ({total_pages} > max {max_pages})"
            )

        page_texts: list[str] = []
        empty_pages = 0
        for idx, page in enumerate(reader.pages):
            raw = page.extract_text() or ""
            cleaned = normalize_text(raw)
            if not cleaned:
                empty_pages += 1
            page_texts.append(cleaned)

        text = normalize_text("\n\n".join(t for t in page_texts if t))
        quality = calculate_quality(text, page_count=total_pages or 1)

        # PDF sans texte ou majoritairement vide → OCR requis
        if not text or empty_pages >= max(1, total_pages // 2 + (1 if total_pages > 1 else 0)):
            quality["requires_ocr"] = True
            quality["requires_review"] = True
            if "no_text" not in quality["warnings"] and not text:
                quality["warnings"].append("no_text")
            if empty_pages and "majority_empty_pages" not in quality["warnings"]:
                quality["warnings"].append("majority_empty_pages")

        return DocumentExtractionOutput(
            text=text,
            page_count=total_pages,
            language=None,
            quality_score=float(quality["quality_score"]),
            confidence=float(quality["confidence"]),
            requires_ocr=bool(quality["requires_ocr"]),
            requires_review=bool(quality["requires_review"]),
            metadata={
                "empty_pages": empty_pages,
                "filename": filename,
                "engine": "pypdf",
                **(quality.get("metrics") or {}),
            },
            warnings=list(quality.get("warnings") or []),
        )
