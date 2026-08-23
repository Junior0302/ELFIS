"""Identité et empreinte métier des transactions — sans déduplication destructive."""

from __future__ import annotations

from datetime import date


def provider_transaction_id(raw: object | None) -> str:
    """Identifiant provider tel que fourni, ou vide. Jamais un hash métier."""
    if raw is None or raw == "":
        return ""
    return str(raw).strip()[:128]


def business_fingerprint(amount: float, label: str, booked_at: date | str) -> tuple[float, str, str]:
    """Empreinte secondaire (détection de candidat), jamais une clé d'upsert."""
    booked = booked_at.isoformat() if isinstance(booked_at, date) else str(booked_at)
    return (round(float(amount), 2), (label or "").strip().lower(), booked)
