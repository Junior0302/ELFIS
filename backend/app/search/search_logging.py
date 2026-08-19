"""Logging structuré — Search Engine."""

from __future__ import annotations

import hashlib
import re
from typing import Any

_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|authorization|bearer|jwt|signed)[=:\s]+[^\s,;]+"
)


def query_hash(query: str | None) -> str | None:
    if not query:
        return None
    return hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]


def sanitize_search_error(message: str | None, *, max_len: int = 500) -> str | None:
    if message is None:
        return None
    cleaned = _SECRET_RE.sub(r"\1=***", str(message))
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 3] + "..."
    return cleaned


def safe_search_log_context(
    *,
    organization_id: int | None = None,
    query_hash_value: str | None = None,
    resource_types: list[str] | None = None,
    result_count: int | None = None,
    execution_time_ms: int | None = None,
    search_document_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    status: str | None = None,
    job_id: str | None = None,
    correlation_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    for key, val in {
        "organization_id": organization_id,
        "query_hash": query_hash_value,
        "resource_types": resource_types,
        "result_count": result_count,
        "execution_time_ms": execution_time_ms,
        "search_document_id": search_document_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "status": status,
        "job_id": job_id,
        "correlation_id": correlation_id,
    }.items():
        if val is not None:
            ctx[key] = val
    forbidden = {
        "query",
        "q",
        "search_text",
        "content",
        "pdf",
        "token",
        "api_key",
        "signed_url",
        "prompt",
    }
    for k, v in extra.items():
        if k.lower() in forbidden:
            continue
        ctx[k] = v
    return ctx
