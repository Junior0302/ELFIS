"""Limites de payload centralisées."""

from __future__ import annotations

from app.config import settings
from app.security.security_config import max_json_body_bytes, max_upload_bytes
from app.security.security_exceptions import SecurityError
from app.security.security_types import ErrorCode


def check_content_length(content_length: str | None, *, max_bytes: int | None = None) -> None:
    if not content_length:
        return
    try:
        size = int(content_length)
    except ValueError as exc:
        raise SecurityError(
            ErrorCode.VALIDATION_ERROR,
            "En-tête Content-Length invalide",
            status_code=400,
        ) from exc
    limit = max_bytes if max_bytes is not None else max(max_json_body_bytes(), max_upload_bytes())
    # Plafond absolu middleware (12 Mo historique + config)
    absolute = max(limit, 12 * 1024 * 1024)
    if size > absolute:
        raise SecurityError(
            ErrorCode.PAYLOAD_TOO_LARGE,
            "Requête trop volumineuse",
            status_code=413,
            details={"max_bytes": absolute, "declared_bytes": size},
        )


def max_bytes_for_path(path: str) -> int:
    if path.startswith("/api/subscriptions/webhook") or path.startswith("/api/webhooks/stripe"):
        return int(getattr(settings, "elfis_billing_webhook_max_bytes", 1_048_576))
    if path.startswith("/api/vault") or "/upload" in path:
        return max_upload_bytes()
    if path.startswith("/api/ai") or path.startswith("/api/elfis-ai"):
        return int(getattr(settings, "elfis_ai_max_input_bytes", 262_144)) + 65_536
    return max_json_body_bytes()


def assert_bytes_within(size: int, *, max_bytes: int, label: str = "payload") -> None:
    if size > max_bytes:
        raise SecurityError(
            ErrorCode.PAYLOAD_TOO_LARGE,
            f"{label} trop volumineux",
            status_code=413,
            details={"max_bytes": max_bytes, "size": size},
        )
