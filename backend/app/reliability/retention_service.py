"""Politiques de rétention — pas de suppression métier automatique."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.config import settings


@dataclass(frozen=True)
class RetentionPolicy:
    category: str
    days: int
    destructive_default: bool = False
    notes: str = ""


def _days(name: str, default: int) -> int:
    return int(getattr(settings, name, default))


def load_retention_policies() -> list[RetentionPolicy]:
    return [
        RetentionPolicy("admin_audit", _days("elfis_retention_admin_audit_days", 730)),
        RetentionPolicy("billing_events", _days("elfis_retention_billing_events_days", 730)),
        RetentionPolicy("job_attempts", _days("elfis_retention_job_attempts_days", 180)),
        RetentionPolicy("event_attempts", _days("elfis_retention_event_attempts_days", 180)),
        RetentionPolicy("notifications", _days("elfis_retention_notifications_days", 365)),
        RetentionPolicy("ai_usage", _days("elfis_retention_ai_usage_days", 730)),
        RetentionPolicy(
            "document_extractions",
            _days("elfis_retention_document_extractions_days", 365),
            notes="Texte extrait uniquement — pas les documents Vault",
        ),
        RetentionPolicy("incidents", _days("elfis_retention_incidents_days", 730)),
        RetentionPolicy("delivery_history", _days("elfis_retention_delivery_history_days", 365)),
        RetentionPolicy(
            "security_events",
            _days("elfis_retention_security_events_days", 365),
        ),
        RetentionPolicy(
            "business_documents",
            0,
            destructive_default=False,
            notes="Jamais auto-supprimé sans politique commerciale/légale",
        ),
    ]


class RetentionService:
    def policies(self) -> list[dict[str, Any]]:
        return [asdict(p) for p in load_retention_policies()]

    def policy_map(self) -> dict[str, RetentionPolicy]:
        return {p.category: p for p in load_retention_policies()}
