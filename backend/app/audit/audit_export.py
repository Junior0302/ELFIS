"""Export sécurisé des événements d'audit (CSV / JSONL)."""

from __future__ import annotations

import csv
import io
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Iterator

from sqlalchemy.orm import Session

from app.audit.audit_filters import AuditEventFilters
from app.audit.audit_models import ElfisAuditEvent
from app.audit.audit_repository import AuditRepository
from app.audit.audit_sanitize import sanitize_metadata, sanitize_message
from app.audit.audit_service import AuditService
from app.audit.audit_types import AuditAction, AuditCategory, Severity
from app.config import settings

logger = logging.getLogger(__name__)

_CSV_DANGEROUS_PREFIX = ("=", "+", "-", "@", "\t", "\r")


def mask_ip_for_export(ip: str | None) -> str:
    if not ip:
        return ""
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.*.*"
    if ":" in ip:
        segs = ip.split(":")
        return f"{segs[0]}:{segs[1]}:*:*" if len(segs) >= 2 else "*"
    return ip[:4] + "…" if len(ip) > 4 else "*"


def neutralize_csv_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r", " ").replace("\n", " ")
    if text.startswith(_CSV_DANGEROUS_PREFIX):
        text = "'" + text
    return text


def event_to_export_row(row: ElfisAuditEvent) -> dict[str, Any]:
    meta = sanitize_metadata(row.metadata_json if isinstance(row.metadata_json, dict) else None)
    return {
        "id": row.id,
        "occurred_at": row.occurred_at.isoformat() if row.occurred_at else "",
        "severity": row.severity,
        "category": row.category,
        "action": row.action,
        "status": row.status,
        "success": row.success,
        "actor_user_id": row.actor_user_id,
        "actor_email": row.actor_email or "",
        "organization_id": row.organization_id,
        "product": row.product or "",
        "service": row.service or "",
        "target_type": row.target_type or "",
        "target_id": row.target_id or "",
        "target_display": sanitize_message(row.target_display, max_len=255) or "",
        "request_id": row.request_id or "",
        "correlation_id": row.correlation_id or "",
        "ip_address": mask_ip_for_export(row.ip_address),
        "message": sanitize_message(row.message, max_len=500) or "",
        "duration_ms": row.duration_ms,
        "metadata": json.dumps(meta or {}, ensure_ascii=False),
    }


_CSV_FIELDS = [
    "id",
    "occurred_at",
    "severity",
    "category",
    "action",
    "status",
    "success",
    "actor_user_id",
    "actor_email",
    "organization_id",
    "product",
    "service",
    "target_type",
    "target_id",
    "target_display",
    "request_id",
    "correlation_id",
    "ip_address",
    "message",
    "duration_ms",
    "metadata",
]


class AuditExportService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = AuditRepository(db)
        # Même session que la requête (tests + commit indépendant via record)
        self._audit = AuditService(db, isolated_writes=False)

    def _log(self, action: str, **kwargs: Any) -> None:
        self._audit.record(action, commit=True, **kwargs)

    def validate_export_filters(self, filters: AuditEventFilters) -> str | None:
        err = filters.validate_enums()
        if err:
            return err
        max_days = int(settings.audit_export_max_range_days)
        err = filters.validate_date_range(max_days=max_days)
        if err:
            return err
        if filters.date_from is None and filters.date_to is None:
            filters.date_from = datetime.utcnow() - timedelta(days=max_days)
            filters.date_to = datetime.utcnow()
        elif filters.date_from is None and filters.date_to is not None:
            filters.date_from = filters.date_to - timedelta(days=max_days)
        elif filters.date_to is None and filters.date_from is not None:
            filters.date_to = datetime.utcnow()
        return filters.validate_date_range(max_days=max_days)

    def safe_filter_summary(self, filters: AuditEventFilters) -> dict[str, Any]:
        return {
            "date_from": filters.date_from.isoformat() if filters.date_from else None,
            "date_to": filters.date_to.isoformat() if filters.date_to else None,
            "category": filters.category,
            "severity": filters.severity,
            "action": filters.action,
            "status": filters.status,
            "success": filters.success,
            "service": filters.service,
            "product": filters.product,
            "organization_id": filters.organization_id,
            "actor_user_id": filters.actor_user_id,
            "q": bool(filters.q),
        }

    def export_csv_chunks(
        self,
        filters: AuditEventFilters,
        *,
        actor_user_id: int | None = None,
    ) -> Iterator[str]:
        started = time.monotonic()
        max_rows = int(settings.audit_export_max_rows)
        timeout = float(settings.audit_export_timeout_seconds)
        self._log(
            AuditAction.AUDIT_EXPORT_REQUESTED.value,
            category=AuditCategory.SECURITY,
            severity=Severity.INFO,
            success=True,
            actor_user_id=actor_user_id,
            service="audit_export",
            message="Export audit demandé",
            metadata={"format": "csv", "filters": self.safe_filter_summary(filters)},
        )
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        count = 0
        try:
            for row in self._repo.iter_events(filters, max_rows=max_rows):
                if time.monotonic() - started > timeout:
                    raise TimeoutError("export_timeout")
                data = event_to_export_row(row)
                safe = {k: neutralize_csv_cell(data.get(k)) for k in _CSV_FIELDS}
                writer.writerow(safe)
                count += 1
                if count % 100 == 0:
                    yield buf.getvalue()
                    buf.seek(0)
                    buf.truncate(0)
            yield buf.getvalue()
            duration_ms = int((time.monotonic() - started) * 1000)
            self._log(
                AuditAction.AUDIT_EXPORT_COMPLETED.value,
                category=AuditCategory.SECURITY,
                severity=Severity.INFO,
                success=True,
                actor_user_id=actor_user_id,
                service="audit_export",
                message="Export audit terminé",
                duration_ms=duration_ms,
                metadata={
                    "format": "csv",
                    "row_count": count,
                    "filters": self.safe_filter_summary(filters),
                },
            )
        except Exception as exc:  # noqa: BLE001
            self._log(
                AuditAction.AUDIT_EXPORT_FAILED.value,
                category=AuditCategory.SECURITY,
                severity=Severity.WARNING,
                success=False,
                actor_user_id=actor_user_id,
                service="audit_export",
                message="Export audit échoué",
                metadata={
                    "format": "csv",
                    "error": type(exc).__name__,
                    "row_count": count,
                },
            )
            raise

    def export_jsonl_chunks(
        self,
        filters: AuditEventFilters,
        *,
        actor_user_id: int | None = None,
    ) -> Iterator[str]:
        started = time.monotonic()
        max_rows = int(settings.audit_export_max_rows)
        timeout = float(settings.audit_export_timeout_seconds)
        self._log(
            AuditAction.AUDIT_EXPORT_REQUESTED.value,
            category=AuditCategory.SECURITY,
            severity=Severity.INFO,
            success=True,
            actor_user_id=actor_user_id,
            service="audit_export",
            message="Export audit demandé",
            metadata={"format": "jsonl", "filters": self.safe_filter_summary(filters)},
        )
        count = 0
        try:
            for row in self._repo.iter_events(filters, max_rows=max_rows):
                if time.monotonic() - started > timeout:
                    raise TimeoutError("export_timeout")
                data = event_to_export_row(row)
                count += 1
                yield json.dumps(data, ensure_ascii=False) + "\n"
            duration_ms = int((time.monotonic() - started) * 1000)
            self._log(
                AuditAction.AUDIT_EXPORT_COMPLETED.value,
                category=AuditCategory.SECURITY,
                severity=Severity.INFO,
                success=True,
                actor_user_id=actor_user_id,
                service="audit_export",
                duration_ms=duration_ms,
                metadata={
                    "format": "jsonl",
                    "row_count": count,
                    "filters": self.safe_filter_summary(filters),
                },
            )
        except Exception as exc:  # noqa: BLE001
            self._log(
                AuditAction.AUDIT_EXPORT_FAILED.value,
                category=AuditCategory.SECURITY,
                severity=Severity.WARNING,
                success=False,
                actor_user_id=actor_user_id,
                service="audit_export",
                metadata={"format": "jsonl", "error": type(exc).__name__, "row_count": count},
            )
            raise
