"""Filtres de requête pour list_events / statistiques / export."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.audit.audit_types import AuditCategory, AuditStatus, Severity
from app.config import settings

_MAX_TEXT = 128
_MAX_Q = 64
_ALLOWED_SEVERITY = {s.value for s in Severity}
_ALLOWED_STATUS = {s.value for s in AuditStatus}
_ALLOWED_CATEGORY = {c.value for c in AuditCategory}
_ALLOWED_SORT = frozenset({"occurred_at_desc", "occurred_at_asc"})


@dataclass
class AuditEventFilters:
    date_from: datetime | None = None
    date_to: datetime | None = None
    severity: str | None = None
    category: str | None = None
    actor_user_id: int | None = None
    actor_email: str | None = None
    organization_id: int | None = None
    service: str | None = None
    product: str | None = None
    action: str | None = None
    status: str | None = None
    success: bool | None = None
    target_type: str | None = None
    target_id: str | None = None
    correlation_id: str | None = None
    request_id: str | None = None
    q: str | None = None
    sort: str = "occurred_at_desc"
    limit: int = 25
    offset: int = 0

    def __post_init__(self) -> None:
        if self.limit < 1:
            self.limit = 1
        if self.limit > 100:
            self.limit = 100
        if self.offset < 0:
            self.offset = 0
        if self.severity:
            self.severity = str(self.severity).strip().upper()[:32]
        if self.category:
            self.category = str(self.category).strip().upper()[:32]
        if self.action:
            self.action = str(self.action).strip().upper()[:_MAX_TEXT]
        if self.status:
            self.status = str(self.status).strip().upper()[:32]
        if self.service:
            self.service = str(self.service).strip()[:_MAX_TEXT]
        if self.product:
            self.product = str(self.product).strip()[:_MAX_TEXT]
        if self.actor_email:
            self.actor_email = str(self.actor_email).strip().lower()[:255]
        if self.target_type:
            self.target_type = str(self.target_type).strip()[:64]
        if self.target_id:
            self.target_id = str(self.target_id).strip()[:128]
        if self.correlation_id:
            self.correlation_id = str(self.correlation_id).strip()[:64]
        if self.request_id:
            self.request_id = str(self.request_id).strip()[:64]
        if self.q:
            self.q = str(self.q).strip()[:_MAX_Q] or None
        if self.sort not in _ALLOWED_SORT:
            self.sort = "occurred_at_desc"

    def validate_enums(self) -> str | None:
        if self.severity and self.severity not in _ALLOWED_SEVERITY:
            return "invalid_severity"
        if self.status and self.status not in _ALLOWED_STATUS:
            return "invalid_status"
        if self.category and self.category not in _ALLOWED_CATEGORY:
            return "invalid_category"
        return None

    def validate_date_range(self, *, max_days: int | None = None) -> str | None:
        if self.date_from and self.date_to and self.date_from > self.date_to:
            return "invalid_date_range"
        max_d = max_days if max_days is not None else int(settings.audit_search_max_range_days)
        if self.date_from and self.date_to:
            delta = self.date_to - self.date_from
            if delta > timedelta(days=max_d):
                return "date_range_too_large"
        return None
