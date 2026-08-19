"""Audit sécurité — persistance filtrée (pas de credentials)."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.security.security_rate_limit import hash_ip
from app.security.security_redaction import filter_error_details, redact_mapping
from app.security.security_types import SecurityEventType, SecuritySeverity

logger = logging.getLogger("elfis.security")


def record_security_event(
    db: Session | None,
    *,
    event_type: str | SecurityEventType,
    severity: str | SecuritySeverity = SecuritySeverity.WARNING,
    organization_id: int | None = None,
    user_id: int | None = None,
    ip: str | None = None,
    route: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any] | None:
    et = event_type.value if isinstance(event_type, SecurityEventType) else str(event_type)
    sev = severity.value if isinstance(severity, SecuritySeverity) else str(severity)
    safe_details = filter_error_details(redact_mapping(details or {}))
    payload = {
        "event_type": et,
        "severity": sev,
        "organization_id": organization_id,
        "user_id": user_id,
        "ip_hash": hash_ip(ip) if ip else None,
        "route": (route or "")[:255] or None,
        "resource_type": resource_type,
        "resource_id": str(resource_id) if resource_id is not None else None,
        "details": safe_details,
        "request_id": request_id,
        "correlation_id": correlation_id,
    }
    logger.warning("security_event", extra={"elfis": payload})

    if db is None:
        return payload

    try:
        from app.security.security_models import ElfisSecurityEvent

        row = ElfisSecurityEvent(
            id=str(uuid4()),
            security_event_id=str(uuid4()),
            event_type=et,
            severity=sev,
            organization_id=organization_id,
            user_id=user_id,
            ip_hash=payload["ip_hash"],
            route=payload["route"],
            resource_type=resource_type,
            resource_id=payload["resource_id"],
            details=safe_details,
            request_id=request_id,
            correlation_id=correlation_id,
        )
        db.add(row)
        db.flush()
        payload["security_event_id"] = row.security_event_id
        return payload
    except Exception:
        logger.debug("security_event_persist_skipped", exc_info=True)
        return payload


def list_security_events(
    db: Session,
    *,
    event_type: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    from app.security.security_models import ElfisSecurityEvent

    q = db.query(ElfisSecurityEvent).order_by(ElfisSecurityEvent.created_at.desc())
    if event_type:
        q = q.filter(ElfisSecurityEvent.event_type == event_type)
    rows = q.limit(min(max(limit, 1), 200)).all()
    return [
        {
            "security_event_id": r.security_event_id,
            "event_type": r.event_type,
            "severity": r.severity,
            "organization_id": r.organization_id,
            "user_id": r.user_id,
            "ip_hash": r.ip_hash,
            "route": r.route,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "details": r.details or {},
            "request_id": r.request_id,
            "correlation_id": r.correlation_id,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
        }
        for r in rows
    ]
