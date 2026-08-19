"""DTO / construction d'événements d'audit (hors ORM)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.audit.audit_types import AuditAction, AuditCategory, AuditStatus, Severity


@dataclass
class AuditEventDraft:
    """Brouillon avant persistance — tous les champs optionnels sauf action."""

    action: str
    severity: str = Severity.INFO.value
    category: str = AuditCategory.OTHER.value
    status: str = AuditStatus.SUCCESS.value
    success: bool = True
    message: str | None = None
    actor_user_id: int | None = None
    actor_email: str | None = None
    organization_id: int | None = None
    product: str | None = None
    service: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    target_display: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: int | None = None
    occurred_at: datetime | None = None
    id: str | None = None

    def ensure_id(self) -> str:
        if not self.id:
            self.id = str(uuid4())
        return self.id


def normalize_action(action: str | AuditAction) -> str:
    if isinstance(action, AuditAction):
        return action.value
    return str(action).strip().upper()


def normalize_enum(value: str | Severity | AuditStatus | AuditCategory, enum_cls: type) -> str:
    if isinstance(value, enum_cls):
        return value.value
    raw = str(value).strip().upper()
    try:
        return enum_cls(raw).value
    except ValueError:
        return raw
