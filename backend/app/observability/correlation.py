"""Propagation correlation_id — ne casse pas les champs existants."""

from __future__ import annotations

from typing import Any

from app.observability.request_context import get_correlation_id, get_request_id


def ensure_correlation_id(payload: dict[str, Any] | None = None) -> str:
    """Retourne correlation_id actuel ou en crée un — pour jobs/events."""
    cid = get_correlation_id() or get_request_id()
    if cid:
        return cid
    from app.observability.request_context import new_id

    return new_id()


def inject_correlation(data: dict[str, Any] | None) -> dict[str, Any]:
    """Ajoute correlation_id si absent — préserve la valeur existante."""
    out = dict(data or {})
    if not out.get("correlation_id"):
        out["correlation_id"] = ensure_correlation_id()
    if not out.get("request_id") and get_request_id():
        out["request_id"] = get_request_id()
    return out
