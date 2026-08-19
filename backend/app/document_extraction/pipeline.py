"""Pipeline d'extraction versionné."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.document_extraction import EXTRACTION_ENGINE_VERSION, PROMPT_VERSION
from app.document_extraction.document_types import get_schema
from app.document_extraction.enums import ExtractionStrategy
from app.document_extraction.extractors.heuristic_extractor import extract_heuristic
from app.document_extraction.extractors.structured_text_extractor import extract_structured
from app.document_extraction.normalization import normalize_extraction
from app.document_extraction.providers.existing_ai_provider_adapter import (
    get_extraction_ai_provider,
)
from app.document_extraction.quality import (
    check_consistency,
    completeness,
    compute_field_confidence,
    compute_global_confidence,
    reconcile_fields,
)
from app.document_extraction.text_resolver import detect_prompt_injection, resolve_document_text

logger = logging.getLogger(__name__)

ProgressCb = Callable[[str, int], None]

PROGRESS = {
    "eligibility": 5,
    "text_resolution": 15,
    "schema_selection": 20,
    "heuristic_extraction": 35,
    "ai_extraction": 60,
    "normalization": 72,
    "reconciliation": 82,
    "validation": 90,
    "confidence": 96,
    "completed": 100,
}


def compute_input_fingerprint(
    *,
    document_checksum: str,
    analysis_version: str,
    schema_name: str,
    schema_version: str,
    extractor_version: str,
    prompt_version: str,
) -> str:
    raw = "|".join(
        [
            document_checksum or "",
            analysis_version or "",
            schema_name,
            schema_version,
            extractor_version,
            prompt_version,
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def run_extraction_pipeline(
    *,
    content: bytes,
    filename: str,
    mime: str | None,
    extension: str | None,
    checksum_sha256: str,
    analysis_report: dict[str, Any],
    need_ocr: bool | None,
    document_type: str | None,
    organization_id: int,
    db: Session | None = None,
    schema_name: str | None = None,
    on_progress: ProgressCb | None = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    warnings: list[str] = []

    def prog(step: str) -> None:
        if on_progress:
            on_progress(step, PROGRESS.get(step, 0))

    prog("eligibility")
    prog("text_resolution")
    text_info = resolve_document_text(
        content=content,
        filename=filename,
        mime=mime,
        extension=extension,
        analysis_report=analysis_report,
        need_ocr=need_ocr,
    )
    warnings.extend(text_info.get("warnings") or [])
    injections = detect_prompt_injection(text_info.get("text") or "")
    if injections:
        warnings.append("prompt_injection_detected")

    if text_info.get("requires_ocr") and not (text_info.get("text") or "").strip():
        return {
            "status": "ocr_pending",
            "requires_ocr": True,
            "text_info": {**text_info, "text": ""},  # ne pas remonter texte dans events
            "warnings": warnings,
            "structured_data": {},
            "field_provenance": {},
            "quality_summary": {"requires_human_review": True},
            "strategy": ExtractionStrategy.FALLBACK.value,
            "processing_time_ms": int((time.perf_counter() - t0) * 1000),
            "llm_used": False,
            "import_created": False,
        }

    prog("schema_selection")
    dtype = document_type or (analysis_report.get("classification") or {}).get("label") or "unknown"
    schema = get_schema(schema_name, dtype)
    tech = analysis_report.get("technical") or {}
    fmt = tech.get("detected_format") or "unknown"

    sources: list[tuple[str, dict, dict]] = []
    strategy = ExtractionStrategy.HEURISTIC.value

    # Structured
    if fmt in {"json", "csv", "xml"}:
        s_data, s_prov = extract_structured(content, fmt=fmt)
        if s_data:
            sources.append(("structured_file", s_data, s_prov))
            strategy = ExtractionStrategy.STRUCTURED.value

    prog("heuristic_extraction")
    h_data, h_prov = extract_heuristic(
        text_info.get("text") or "", document_type=schema["document_type"], filename=filename
    )
    if h_data:
        sources.append(("heuristic", h_data, h_prov))

    prog("ai_extraction")
    llm_meta: dict[str, Any] = {}
    use_llm = bool(text_info.get("text")) and strategy != ExtractionStrategy.STRUCTURED.value
    # Always try LLM adapter — it no-ops if disabled
    if use_llm:
        provider = get_extraction_ai_provider(db)
        l_data, l_prov, llm_meta = provider.extract_structured(
            text=text_info.get("text") or "",
            schema=schema,
            document_type=schema["document_type"],
            filename=filename,
            organization_id=organization_id,
        )
        if l_data:
            sources.append(("llm", l_data, l_prov))
            strategy = (
                ExtractionStrategy.HEURISTIC_PLUS_LLM.value
                if h_data
                else ExtractionStrategy.LLM.value
            )
        elif not sources:
            strategy = ExtractionStrategy.FALLBACK.value
    if llm_meta.get("injection_flags"):
        warnings.append("prompt_injection_detected")

    if not sources:
        strategy = ExtractionStrategy.FALLBACK.value
        sources.append(("fallback", {}, {}))

    prog("reconciliation")
    merged, provenance, reconciliation = reconcile_fields(sources)

    prog("normalization")
    normalized, norm_meta = normalize_extraction(merged)

    prog("validation")
    consistency = check_consistency(normalized)
    warnings.extend(consistency.get("warnings") or [])
    errors = list(consistency.get("errors") or [])

    prog("confidence")
    quality_score = (analysis_report.get("quality") or {}).get("score")
    field_conf = compute_field_confidence(provenance, quality_score)
    complete = completeness(
        normalized,
        schema.get("critical_fields") or [],
        schema.get("recommended_fields") or [],
    )
    quality_summary = compute_global_confidence(
        field_confidence=field_conf,
        critical_fields=schema.get("critical_fields") or [],
        consistency_score=float(consistency.get("consistency_score") or 0),
        completeness_score=complete,
    )
    # Enrich provenance with confidence levels
    for path, fc in field_conf.items():
        if path in provenance:
            provenance[path] = fc

    prog("completed")
    # Strip full text from returned text_info for persistence safety in events
    safe_text_info = {
        k: v for k, v in text_info.items() if k != "text" and k != "page_texts"
    }
    safe_text_info["character_count"] = text_info.get("character_count")
    safe_text_info["source"] = text_info.get("source")

    useful = bool(normalized) and complete > 0.05
    return {
        "status": "completed" if useful else "failed",
        "requires_ocr": False,
        "schema_name": schema["schema_name"],
        "schema_version": schema["schema_version"],
        "document_type": schema["document_type"],
        "strategy": strategy,
        "structured_data": normalized,
        "field_provenance": provenance,
        "reconciliation": reconciliation,
        "normalization_meta": norm_meta,
        "quality_summary": quality_summary,
        "warnings": warnings,
        "errors": errors,
        "text_info": safe_text_info,
        "llm_meta": {
            "used_llm": bool(llm_meta.get("used_llm")),
            "provider": llm_meta.get("provider"),
            "model_name": llm_meta.get("model_name"),
            "prompt_version": PROMPT_VERSION,
            "skipped": llm_meta.get("skipped"),
            "error": llm_meta.get("error"),
        },
        "processing_time_ms": int((time.perf_counter() - t0) * 1000),
        "extraction_version": EXTRACTION_ENGINE_VERSION,
        "input_fingerprint": compute_input_fingerprint(
            document_checksum=checksum_sha256,
            analysis_version=str(analysis_report.get("analysis_version") or "1"),
            schema_name=schema["schema_name"],
            schema_version=schema["schema_version"],
            extractor_version=EXTRACTION_ENGINE_VERSION,
            prompt_version=PROMPT_VERSION,
        ),
        "import_created": False,
        "business_entities_created": False,
    }
