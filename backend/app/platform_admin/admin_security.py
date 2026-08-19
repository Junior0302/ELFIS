"""Sécurité Platform Admin — filtrage, raisons, pagination."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.platform_admin.admin_exceptions import AdminValidationError
from app.platform_admin.admin_types import ALLOWED_STATE_KEYS, FORBIDDEN_ADMIN_RESPONSE_KEYS


def require_action_reason(reason: str | None) -> str:
    if not getattr(settings, "elfis_platform_admin_require_action_reason", True):
        return (reason or "").strip()[:2000]
    cleaned = (reason or "").strip()
    if len(cleaned) < 3:
        raise AdminValidationError("Une raison administrative est obligatoire")
    if len(cleaned) > 2000:
        raise AdminValidationError("Raison trop longue")
    return cleaned


def clamp_page(page: int | None) -> int:
    try:
        p = int(page or 1)
    except (TypeError, ValueError):
        p = 1
    return max(1, p)


def clamp_page_size(page_size: int | None) -> int:
    default = int(getattr(settings, "elfis_platform_admin_default_page_size", 25) or 25)
    maximum = int(getattr(settings, "elfis_platform_admin_max_page_size", 100) or 100)
    try:
        size = int(page_size or default)
    except (TypeError, ValueError):
        size = default
    return max(1, min(size, maximum))


def filter_state_dict(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    out: dict[str, Any] = {}
    for key, value in data.items():
        if key not in ALLOWED_STATE_KEYS:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[key] = value
        else:
            out[key] = str(value)[:200]
    return out


def scrub_dict(data: Any, *, depth: int = 0) -> Any:
    if depth > 4:
        return None
    if isinstance(data, dict):
        cleaned: dict[str, Any] = {}
        for key, value in data.items():
            if str(key).lower() in FORBIDDEN_ADMIN_RESPONSE_KEYS:
                continue
            cleaned[str(key)] = scrub_dict(value, depth=depth + 1)
        return cleaned
    if isinstance(data, list):
        return [scrub_dict(item, depth=depth + 1) for item in data[:50]]
    if isinstance(data, str) and len(data) > 500:
        return data[:497] + "..."
    return data


def assert_search_query(q: str | None) -> str:
    cleaned = (q or "").strip()
    if len(cleaned) < 2:
        raise AdminValidationError("Requête trop courte")
    if len(cleaned) > 100:
        raise AdminValidationError("Requête trop longue")
    return cleaned
