"""UploadAnalyticsService — statistiques backend-only."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.document_intake.enums import DocumentLifecycleStatus
from app.document_intake.events import publish_upload_session_event
from app.document_intake.models import ElfisDocumentIntakeItem, ElfisDocumentUploadSession

logger = logging.getLogger(__name__)


def _empty_analytics() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "file_count": 0,
        "total_bytes": 0,
        "received_bytes": 0,
        "validated_count": 0,
        "duplicate_count": 0,
        "rejected_count": 0,
        "quarantined_count": 0,
        "cancelled_count": 0,
        "average_upload_speed_bps": None,
        "duration_ms": None,
        "dominant_format": None,
        "format_distribution": {},
        "error_distribution": {},
        "completion_percent": 0,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }


class UploadAnalyticsService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def initialize(self, session: ElfisDocumentUploadSession) -> dict[str, Any]:
        analytics = _empty_analytics()
        session.analytics_json = analytics
        return analytics

    def get_for_upload_session(
        self, session: ElfisDocumentUploadSession
    ) -> dict[str, Any]:
        data = dict(session.analytics_json or {})
        if not data.get("schema_version"):
            return self.recalculate(session, publish=False)
        return data

    def recalculate(
        self,
        session: ElfisDocumentUploadSession,
        *,
        publish: bool = True,
    ) -> dict[str, Any]:
        items = (
            self._db.query(ElfisDocumentIntakeItem)
            .filter(ElfisDocumentIntakeItem.organization_id == session.organization_id)
            .filter(ElfisDocumentIntakeItem.upload_session_id == session.id)
            .all()
        )
        analytics = _empty_analytics()
        formats: dict[str, int] = {}
        errors: dict[str, int] = {}
        for it in items:
            analytics["file_count"] += 1
            analytics["received_bytes"] += int(it.size_bytes or 0)
            analytics["total_bytes"] += int(it.size_bytes or 0)
            fid = it.format_id or "unknown"
            formats[fid] = formats.get(fid, 0) + 1
            st = it.lifecycle_status or it.status
            if st in (
                DocumentLifecycleStatus.VALIDATED.value,
                DocumentLifecycleStatus.READY_FOR_ANALYSIS.value,
            ):
                analytics["validated_count"] += 1
            if st == DocumentLifecycleStatus.DUPLICATE.value:
                analytics["duplicate_count"] += 1
            if st == DocumentLifecycleStatus.REJECTED.value:
                analytics["rejected_count"] += 1
                reason = it.reject_reason or "rejected"
                errors[reason] = errors.get(reason, 0) + 1
            if st == DocumentLifecycleStatus.QUARANTINED.value:
                analytics["quarantined_count"] += 1
                reason = it.quarantine_reason or "quarantined"
                errors[reason] = errors.get(reason, 0) + 1
            if st == DocumentLifecycleStatus.CANCELLED.value:
                analytics["cancelled_count"] += 1

        analytics["format_distribution"] = formats
        analytics["error_distribution"] = errors
        if formats:
            analytics["dominant_format"] = max(formats.items(), key=lambda x: x[1])[0]

        expected = int(session.expected_file_count or 0)
        if expected > 0:
            analytics["completion_percent"] = min(
                100, int(round(100.0 * analytics["file_count"] / expected))
            )
        elif analytics["file_count"] > 0:
            analytics["completion_percent"] = 100
        else:
            analytics["completion_percent"] = 0

        started = session.started_at
        ended = session.completed_at or session.cancelled_at
        if started and ended:
            duration_ms = int((ended - started).total_seconds() * 1000)
            analytics["duration_ms"] = max(0, duration_ms)
            if duration_ms >= 1000 and analytics["received_bytes"] > 0:
                analytics["average_upload_speed_bps"] = int(
                    analytics["received_bytes"] / (duration_ms / 1000.0)
                )
            else:
                analytics["average_upload_speed_bps"] = None
        else:
            analytics["duration_ms"] = None
            analytics["average_upload_speed_bps"] = None

        analytics["updated_at"] = datetime.utcnow().isoformat() + "Z"
        session.analytics_json = analytics
        session.received_file_count = analytics["file_count"]
        session.received_total_bytes = analytics["received_bytes"]
        session.validated_file_count = analytics["validated_count"]
        session.duplicate_file_count = analytics["duplicate_count"]
        session.rejected_file_count = analytics["rejected_count"]
        session.quarantined_file_count = analytics["quarantined_count"]
        session.cancelled_file_count = analytics["cancelled_count"]
        session.version = int(session.version or 1) + 1
        session.updated_at = datetime.utcnow()
        self._db.flush()

        if publish:
            publish_upload_session_event(
                self._db,
                event_type="document.upload.analytics.updated",
                session=session,
                metadata={"file_count": analytics["file_count"]},
                idempotency_key=f"document:analytics:{session.id}:{session.version}",
                commit=False,
            )
        return analytics

    def record_file_received(self, session: ElfisDocumentUploadSession) -> dict[str, Any]:
        return self.recalculate(session)

    def record_file_validated(self, session: ElfisDocumentUploadSession) -> dict[str, Any]:
        return self.recalculate(session)

    def record_file_rejected(self, session: ElfisDocumentUploadSession) -> dict[str, Any]:
        return self.recalculate(session)

    def record_file_duplicate(self, session: ElfisDocumentUploadSession) -> dict[str, Any]:
        return self.recalculate(session)

    def record_file_quarantined(self, session: ElfisDocumentUploadSession) -> dict[str, Any]:
        return self.recalculate(session)

    def finalize(self, session: ElfisDocumentUploadSession) -> dict[str, Any]:
        return self.recalculate(session)
