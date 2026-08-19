"""Logging structuré sécurisé — Document Intelligence."""

from __future__ import annotations

import re
from typing import Any

_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|authorization|bearer|jwt|signed)[=:\s]+[^\s,;]+"
)


def sanitize_document_error(message: str | None, *, max_len: int = 500) -> str | None:
    if message is None:
        return None
    cleaned = _SECRET_RE.sub(r"\1=***", str(message))
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 3] + "..."
    return cleaned


def safe_document_log_context(
    *,
    extraction_id: str | None = None,
    vault_document_id: str | None = None,
    organization_id: int | None = None,
    extractor_name: str | None = None,
    status: str | None = None,
    file_size_bytes: int | None = None,
    page_count: int | None = None,
    text_length: int | None = None,
    quality_score: float | None = None,
    confidence: float | None = None,
    requires_ocr: bool | None = None,
    duration_ms: int | None = None,
    job_id: str | None = None,
    correlation_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    for key, val in {
        "extraction_id": extraction_id,
        "vault_document_id": vault_document_id,
        "organization_id": organization_id,
        "extractor_name": extractor_name,
        "status": status,
        "file_size_bytes": file_size_bytes,
        "page_count": page_count,
        "text_length": text_length,
        "quality_score": quality_score,
        "confidence": confidence,
        "requires_ocr": requires_ocr,
        "duration_ms": duration_ms,
        "job_id": job_id,
        "correlation_id": correlation_id,
    }.items():
        if val is not None:
            ctx[key] = val
    forbidden = {
        "text_content",
        "text",
        "pdf",
        "content",
        "content_bytes",
        "signed_url",
        "download_url",
        "api_key",
        "token",
        "temp_path",
    }
    for k, v in extra.items():
        if k.lower() in forbidden:
            continue
        ctx[k] = v
    return ctx
