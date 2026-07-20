"""Logging structuré sécurisé — Job Queue."""

from __future__ import annotations

import re
from typing import Any

from app.jobs.job_models import ElfisJob

_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|authorization|bearer|jwt|supabase)[=:\s]+[^\s,;]+"
)
_MAX_ERROR = 2000


def sanitize_job_error(message: str | None, *, max_len: int = _MAX_ERROR) -> str | None:
    if message is None:
        return None
    cleaned = _SECRET_RE.sub(r"\1=***", str(message))
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 3] + "..."
    return cleaned


def safe_job_log_context(
    job: ElfisJob | None = None,
    *,
    job_id: str | None = None,
    job_name: str | None = None,
    organization_id: int | None = None,
    queue_name: str | None = None,
    attempt_number: int | None = None,
    worker_id: str | None = None,
    status: str | None = None,
    progress: int | None = None,
    duration_ms: int | None = None,
    correlation_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    if job is not None:
        ctx.update(
            {
                "job_id": job.job_id,
                "job_name": job.job_name,
                "organization_id": job.organization_id,
                "queue_name": job.queue_name,
                "attempt_number": job.attempt_count,
                "worker_id": job.locked_by,
                "status": job.status,
                "progress": job.progress,
                "correlation_id": job.correlation_id,
            }
        )
    if job_id is not None:
        ctx["job_id"] = job_id
    if job_name is not None:
        ctx["job_name"] = job_name
    if organization_id is not None:
        ctx["organization_id"] = organization_id
    if queue_name is not None:
        ctx["queue_name"] = queue_name
    if attempt_number is not None:
        ctx["attempt_number"] = attempt_number
    if worker_id is not None:
        ctx["worker_id"] = worker_id
    if status is not None:
        ctx["status"] = status
    if progress is not None:
        ctx["progress"] = progress
    if duration_ms is not None:
        ctx["duration_ms"] = duration_ms
    if correlation_id is not None:
        ctx["correlation_id"] = correlation_id
    for k, v in extra.items():
        if k in ("payload", "result", "pdf", "pdf_bytes", "api_key", "token", "password"):
            continue
        ctx[k] = v
    return ctx


# Clés interdites dans payload/result
FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "pdf",
        "pdf_bytes",
        "pdf_base64",
        "file_content",
        "content_base64",
        "jwt",
        "api_key",
        "apikey",
        "password",
        "supabase_key",
        "service_role_key",
        "authorization",
        "signed_url",
        "email_body",
        "html_body",
        "raw_email",
    }
)


def assert_safe_payload(data: dict[str, Any] | None, *, label: str = "payload") -> None:
    if not data:
        return
    for key in data:
        lk = str(key).lower()
        if lk in FORBIDDEN_PAYLOAD_KEYS or any(f in lk for f in ("password", "api_key", "jwt", "secret")):
            from app.jobs.job_exceptions import JobValidationError

            raise JobValidationError(f"{label} contient une clé interdite: {key}")
