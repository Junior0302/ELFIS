"""Sanitisation metadata_json documents / storage objects."""

from __future__ import annotations

import json
from typing import Any

from app.config import settings
from app.storage.storage_exceptions import StorageValidationError
from app.storage.storage_reject_codes import StorageRejectCode

_BLOCKED_KEYS = frozenset(
    {
        "token",
        "password",
        "passwd",
        "secret",
        "cookie",
        "cookies",
        "authorization",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "content",
        "bytes",
        "raw",
        "file_content",
        "file_bytes",
        "physical_path",
        "file_path",
        "local_path",
        "storage_path",
        "filepath",
        "path",
    }
)


def sanitize_document_metadata(
    data: dict[str, Any] | None,
    *,
    max_bytes: int | None = None,
    max_keys: int = 32,
    max_depth: int = 3,
) -> dict[str, Any] | None:
    if not data:
        return None
    if not isinstance(data, dict):
        raise StorageValidationError(
            StorageRejectCode.METADATA_INVALID.value,
            "metadata doit être un objet JSON",
        )
    limit = max_bytes or int(getattr(settings, "elfis_max_metadata_json_bytes", 65_536) or 65_536)
    cleaned = _walk(data, depth=0, max_depth=max_depth, max_keys=max_keys)
    encoded = json.dumps(cleaned, ensure_ascii=False, default=str)
    if len(encoded.encode("utf-8")) > limit:
        raise StorageValidationError(
            StorageRejectCode.METADATA_INVALID.value,
            f"metadata trop volumineux (max {limit} octets)",
        )
    return cleaned or None


def _walk(value: Any, *, depth: int, max_depth: int, max_keys: int) -> Any:
    if depth > max_depth:
        raise StorageValidationError(
            StorageRejectCode.METADATA_INVALID.value,
            "metadata trop profond",
        )
    if isinstance(value, dict):
        if len(value) > max_keys:
            raise StorageValidationError(
                StorageRejectCode.METADATA_INVALID.value,
                f"trop de clés metadata (max {max_keys})",
            )
        out: dict[str, Any] = {}
        for k, v in value.items():
            key = str(k)[:64]
            lowered = key.lower().replace("-", "_")
            if lowered in _BLOCKED_KEYS or any(b in lowered for b in _BLOCKED_KEYS):
                continue
            if isinstance(v, (bytes, bytearray)):
                continue
            out[key] = _walk(v, depth=depth + 1, max_depth=max_depth, max_keys=max_keys)
        return out
    if isinstance(value, list):
        if len(value) > max_keys:
            raise StorageValidationError(
                StorageRejectCode.METADATA_INVALID.value,
                "liste metadata trop longue",
            )
        return [
            _walk(item, depth=depth + 1, max_depth=max_depth, max_keys=max_keys)
            for item in value[:max_keys]
        ]
    if isinstance(value, str):
        return value[:500]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:200]
