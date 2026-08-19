"""Contexte de requête — request_id / correlation_id (contextvars)."""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar

from app.security.security_types import MAX_REQUEST_ID_LEN, REQUEST_ID_PATTERN

_request_id: ContextVar[str | None] = ContextVar("elfis_request_id", default=None)
_correlation_id: ContextVar[str | None] = ContextVar("elfis_correlation_id", default=None)
_organization_id: ContextVar[int | None] = ContextVar("elfis_organization_id", default=None)
_user_id: ContextVar[int | None] = ContextVar("elfis_user_id", default=None)

_ID_RE = re.compile(REQUEST_ID_PATTERN)


def new_id() -> str:
    return str(uuid.uuid4())


def normalize_id_header(value: str | None) -> str:
    """Retourne un ID valide, ou génère un UUID si absent/invalide."""
    raw = (value or "").strip()
    if not raw or len(raw) > MAX_REQUEST_ID_LEN or not _ID_RE.match(raw):
        return new_id()
    return raw


def normalize_optional_id(value: str | None) -> str | None:
    """None si absent ou invalide (pour correlation → fallback request_id)."""
    raw = (value or "").strip()
    if not raw:
        return None
    if len(raw) > MAX_REQUEST_ID_LEN or not _ID_RE.match(raw):
        return None
    return raw


def bind_request_ids(*, request_id: str, correlation_id: str) -> None:
    _request_id.set(request_id)
    _correlation_id.set(correlation_id)


def set_actor(*, user_id: int | None = None, organization_id: int | None = None) -> None:
    if user_id is not None:
        _user_id.set(user_id)
    if organization_id is not None:
        _organization_id.set(organization_id)


def get_request_id() -> str | None:
    return _request_id.get()


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def get_organization_id() -> int | None:
    return _organization_id.get()


def get_user_id() -> int | None:
    return _user_id.get()


def clear_request_context() -> None:
    _request_id.set(None)
    _correlation_id.set(None)
    _organization_id.set(None)
    _user_id.set(None)


def current_context() -> dict:
    return {
        "request_id": get_request_id(),
        "correlation_id": get_correlation_id(),
        "organization_id": get_organization_id(),
        "user_id": get_user_id(),
    }
