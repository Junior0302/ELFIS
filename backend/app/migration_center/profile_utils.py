"""Helpers profils versionnés + token."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.migration_center.enums import EMPTY_PROFILE_ENVELOPE


def new_session_token() -> str:
    return f"mig_{uuid4().hex}"


def profile_envelope(data: dict[str, Any] | None = None, *, schema_version: int = 1) -> dict[str, Any]:
    return {"schema_version": int(schema_version), "data": dict(data or {})}


def empty_profile_envelope() -> dict[str, Any]:
    return profile_envelope({})


def unwrap_company_profile(raw: Any) -> dict[str, Any] | None:
    """Expose le profil entreprise à plat (compat Sprint 1 frontend)."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None
    if "schema_version" in raw and "data" in raw and isinstance(raw["data"], dict):
        return dict(raw["data"])
    # Legacy Sprint 1 flat
    return dict(raw)


def wrap_company_profile(flat: dict[str, Any]) -> dict[str, Any]:
    return profile_envelope(flat)


def ensure_profile_envelope(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict) and "schema_version" in raw and "data" in raw:
        return {"schema_version": int(raw.get("schema_version") or 1), "data": dict(raw.get("data") or {})}
    if isinstance(raw, dict) and raw:
        return profile_envelope(raw)
    return empty_profile_envelope()


# Réexport
EMPTY = EMPTY_PROFILE_ENVELOPE
