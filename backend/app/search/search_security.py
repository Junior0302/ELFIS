"""Sécurité Search Engine."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlparse

from app.config import settings
from app.search.search_exceptions import SearchValidationError
from app.search.search_types import INDEXED_RESOURCE_TYPES_V1, SUPPORTED_SORTS, SearchSort

_MAX_TITLE = 512
_MAX_SUBTITLE = 512
_MAX_ACTION = 512
_DANGEROUS_SCHEMES = ("javascript:", "data:", "vbscript:")

FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "pdf",
        "pdf_base64",
        "content_bytes",
        "signed_url",
        "download_url",
        "storage_path",
        "api_key",
        "token",
        "service_role_key",
        "authorization",
        "password",
        "iban",
        "bic",
        "prompt",
    }
)


def assert_resource_type(resource_type: str) -> str:
    value = (resource_type or "").strip()
    if value not in INDEXED_RESOURCE_TYPES_V1:
        raise SearchValidationError(f"Type de ressource inconnu: {value or 'vide'}")
    return value


def assert_query(query: str | None) -> str | None:
    if query is None:
        return None
    q = query.strip()
    max_len = max(1, int(settings.elfis_search_max_query_length))
    if len(q) > max_len:
        raise SearchValidationError(f"Requête trop longue (max {max_len})")
    return q or None


def assert_page_size(page_size: int | None) -> int:
    default = max(1, int(settings.elfis_search_default_page_size))
    max_size = max(1, int(settings.elfis_search_max_page_size))
    size = default if page_size is None else int(page_size)
    if size < 1 or size > max_size:
        raise SearchValidationError(f"page_size invalide (max {max_size})")
    return size


def assert_sort(sort: str | None, *, has_query: bool) -> str:
    if not sort:
        return SearchSort.RELEVANCE if has_query else SearchSort.NEWEST
    value = sort.strip().lower()
    if value not in SUPPORTED_SORTS:
        raise SearchValidationError(f"Tri non supporté: {value}")
    return value


def assert_action_url(url: str | None) -> str | None:
    if not url:
        return None
    value = url.strip()
    if len(value) > _MAX_ACTION:
        raise SearchValidationError("action_url trop longue")
    lowered = value.lower()
    for scheme in _DANGEROUS_SCHEMES:
        if lowered.startswith(scheme):
            raise SearchValidationError("action_url dangereuse refusée")
    # URLs internes relatives uniquement
    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        raise SearchValidationError(f"action_url externe refusée: {parsed.scheme}")
    if not value.startswith("/"):
        raise SearchValidationError("action_url doit être un chemin interne")
    if ".." in value.split("/"):
        raise SearchValidationError("action_url path traversal refusée")
    return value


def truncate_content(text: str | None) -> str:
    raw = text or ""
    max_bytes = max(1024, int(settings.elfis_search_max_content_bytes))
    encoded = raw.encode("utf-8")
    if len(encoded) <= max_bytes:
        return raw
    # Troncature explicite pour l'index uniquement
    truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
    return truncated + "\n…[tronqué pour index]"


def filter_metadata(meta: dict[str, Any] | None) -> dict[str, Any]:
    if not meta:
        return {}
    out: dict[str, Any] = {}
    for key, value in meta.items():
        k = str(key)
        if k.lower() in FORBIDDEN_METADATA_KEYS:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            if isinstance(value, str) and len(value) > 500:
                out[k] = value[:500]
            else:
                out[k] = value
        elif isinstance(value, list) and all(isinstance(x, (str, int, float)) for x in value[:20]):
            out[k] = value[:20]
    return out


def content_hash(*parts: str | None) -> str:
    blob = "\n".join((p or "") for p in parts)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def sanitize_indexed_text(text: str | None) -> str:
    if not text:
        return ""
    cleaned = text.replace("\x00", "")
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
