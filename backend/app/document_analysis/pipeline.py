"""Pipeline séquentiel Document Analysis — étapes indépendantes."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable

from app.document_analysis import ANALYSIS_VERSION, REPORT_SCHEMA_VERSION
from app.document_analysis.analyzers.ocr_decision import decide_ocr
from app.document_analysis.analyzers.technical import analyze_technical
from app.document_analysis.classifiers import classify_document
from app.document_analysis.language import analyze_language
from app.document_analysis.metadata import analyze_metadata
from app.document_analysis.orientation import analyze_orientation
from app.document_analysis.pages import analyze_pages
from app.document_analysis.quality import analyze_quality

logger = logging.getLogger(__name__)

StepCallback = Callable[[str, int, int], None]

PIPELINE_STEPS = [
    "upload_complete",
    "validation_ok",
    "metadata",
    "technical",
    "format_detection",
    "pages",
    "orientation",
    "quality",
    "language",
    "ocr_decision",
    "classification",
    "ready_for_ai",
]


def run_analysis_pipeline(
    *,
    content: bytes,
    filename: str,
    mime: str | None,
    extension: str | None,
    checksum_sha256: str | None,
    fingerprint: dict[str, Any] | None,
    size_bytes: int,
    on_step: StepCallback | None = None,
) -> dict[str, Any]:
    """Exécute le pipeline. Ne modifie jamais le document. Pas d'OCR réel / LLM."""
    t0 = time.perf_counter()
    warnings: list[str] = []
    total = len(PIPELINE_STEPS)
    step_idx = 0

    def tick(name: str) -> None:
        nonlocal step_idx
        step_idx += 1
        if on_step:
            on_step(name, step_idx, total)

    tick("upload_complete")
    tick("validation_ok")

    metadata = analyze_metadata(
        filename=filename,
        size_bytes=size_bytes,
        mime=mime,
        extension=extension,
        checksum_sha256=checksum_sha256,
        fingerprint=fingerprint,
    )
    tick("metadata")

    technical = analyze_technical(content, mime=mime, extension=extension)
    tick("technical")

    # Étape format réel (dérivée de technical)
    format_info = {
        "detected_format": technical.get("detected_format"),
        "is_pdf": (technical.get("pdf") or {}).get("is_pdf"),
        "is_zip": (technical.get("zip") or {}).get("is_zip"),
        "is_xml": technical.get("is_xml"),
        "is_csv": technical.get("is_csv"),
        "is_json": technical.get("is_json"),
        "is_image": technical.get("is_image"),
    }
    tick("format_detection")

    pages = analyze_pages(technical)
    tick("pages")

    orientation = analyze_orientation(content, technical)
    tick("orientation")

    quality = analyze_quality(content, technical, pages, orientation)
    tick("quality")

    language = analyze_language(content, technical)
    tick("language")

    ocr_decision = decide_ocr(technical, language)
    tick("ocr_decision")

    classification = classify_document(
        content, filename=filename, technical=technical
    )
    tick("classification")

    if (technical.get("pdf") or {}).get("is_encrypted"):
        warnings.append("pdf_encrypted")
    if orientation.get("mixed"):
        warnings.append("mixed_orientation")
    if quality.get("score", 100) < 45:
        warnings.append("low_quality")
    if ocr_decision.get("need_ocr"):
        warnings.append("ocr_recommended")
    if classification.get("label") == "unknown":
        warnings.append("classification_uncertain")
    if technical.get("zip", {}).get("malformed"):
        warnings.append("zip_malformed")

    tick("ready_for_ai")

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "analysis_version": ANALYSIS_VERSION,
        "technical": technical,
        "format": format_info,
        "metadata": metadata,
        "pages": pages,
        "quality": quality,
        "orientation": {
            "degrees": orientation.get("degrees"),
            "mixed": bool(orientation.get("mixed")),
            "confidence": orientation.get("confidence"),
            "method": orientation.get("method"),
        },
        "language": language,
        "ocr_decision": ocr_decision,
        "classification": classification,
        "warnings": warnings,
        "processing_time_ms": elapsed_ms,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        # Garantie non-scope
        "extraction": None,
        "llm_used": False,
        "ocr_executed": False,
    }
    logger.info(
        "document_analysis_pipeline_completed",
        extra={
            "operation": "analysis_pipeline",
            "detected_format": technical.get("detected_format"),
            "need_ocr": ocr_decision.get("need_ocr"),
            "classification": classification.get("label"),
            "duration_ms": elapsed_ms,
            "result": "ok",
        },
    )
    return report
