"""Logging structuré sécurisé — Accounting Pipeline."""

from __future__ import annotations

import re
from typing import Any

_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|authorization|bearer|iban|bic)[=:\s]+[^\s,;]+"
)


def sanitize_accounting_error(message: str | None, *, max_len: int = 500) -> str | None:
    if message is None:
        return None
    cleaned = _SECRET_RE.sub(r"\1=***", str(message))
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 3] + "..."
    return cleaned


def safe_accounting_log_context(
    *,
    proposal_id: str | None = None,
    entry_id: str | None = None,
    vault_document_id: str | None = None,
    organization_id: int | None = None,
    document_type: str | None = None,
    status: str | None = None,
    current_stage: str | None = None,
    requires_review: bool | None = None,
    confidence: float | None = None,
    balanced: bool | None = None,
    duration_ms: int | None = None,
    job_id: str | None = None,
    correlation_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    for key, val in {
        "proposal_id": proposal_id,
        "entry_id": entry_id,
        "vault_document_id": vault_document_id,
        "organization_id": organization_id,
        "document_type": document_type,
        "status": status,
        "current_stage": current_stage,
        "requires_review": requires_review,
        "confidence": confidence,
        "balanced": balanced,
        "duration_ms": duration_ms,
        "job_id": job_id,
        "correlation_id": correlation_id,
    }.items():
        if val is not None:
            ctx[key] = val
    forbidden = {
        "lines",
        "entry_lines",
        "pdf",
        "raw_text",
        "extracted_text",
        "prompt",
        "api_key",
        "token",
        "iban",
        "bic",
        "previous_data",
        "new_data",
    }
    for k, v in extra.items():
        if k.lower() in forbidden:
            continue
        ctx[k] = v
    return ctx
