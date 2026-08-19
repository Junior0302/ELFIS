"""Repository — accès SQL elfis_audit_events (+ archive)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Iterator

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.audit.audit_filters import AuditEventFilters
from app.audit.audit_models import ElfisAuditEvent, ElfisAuditEventArchive


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def insert_event(self, row: ElfisAuditEvent, *, flush: bool = True) -> ElfisAuditEvent:
        self._db.add(row)
        if flush:
            self._db.flush()
        return row

    def find_by_id(self, event_id: str) -> ElfisAuditEvent | None:
        return self._db.get(ElfisAuditEvent, event_id)

    def find_by_correlation(
        self,
        correlation_id: str,
        *,
        limit: int = 100,
    ) -> list[ElfisAuditEvent]:
        return (
            self._db.query(ElfisAuditEvent)
            .filter(ElfisAuditEvent.correlation_id == correlation_id)
            .order_by(ElfisAuditEvent.occurred_at.desc(), ElfisAuditEvent.id.desc())
            .limit(max(1, min(limit, 500)))
            .all()
        )

    def find_recent(self, *, limit: int = 50) -> list[ElfisAuditEvent]:
        return (
            self._db.query(ElfisAuditEvent)
            .order_by(ElfisAuditEvent.occurred_at.desc(), ElfisAuditEvent.id.desc())
            .limit(max(1, min(limit, 500)))
            .all()
        )

    def _apply_filters(self, q, filters: AuditEventFilters):
        if filters.date_from is not None:
            q = q.filter(ElfisAuditEvent.occurred_at >= filters.date_from)
        if filters.date_to is not None:
            q = q.filter(ElfisAuditEvent.occurred_at <= filters.date_to)
        if filters.severity:
            q = q.filter(ElfisAuditEvent.severity == filters.severity)
        if filters.category:
            q = q.filter(ElfisAuditEvent.category == filters.category)
        if filters.actor_user_id is not None:
            q = q.filter(ElfisAuditEvent.actor_user_id == filters.actor_user_id)
        if filters.actor_email:
            q = q.filter(ElfisAuditEvent.actor_email == filters.actor_email)
        if filters.organization_id is not None:
            q = q.filter(ElfisAuditEvent.organization_id == filters.organization_id)
        if filters.service:
            q = q.filter(ElfisAuditEvent.service == filters.service)
        if filters.product:
            q = q.filter(ElfisAuditEvent.product == filters.product)
        if filters.action:
            q = q.filter(ElfisAuditEvent.action == filters.action)
        if filters.status:
            q = q.filter(ElfisAuditEvent.status == filters.status)
        if filters.success is not None:
            q = q.filter(ElfisAuditEvent.success == filters.success)
        if filters.target_type:
            q = q.filter(ElfisAuditEvent.target_type == filters.target_type)
        if filters.target_id:
            q = q.filter(ElfisAuditEvent.target_id == filters.target_id)
        if filters.correlation_id:
            q = q.filter(ElfisAuditEvent.correlation_id == filters.correlation_id)
        if filters.request_id:
            q = q.filter(ElfisAuditEvent.request_id == filters.request_id)
        if filters.q:
            like = f"%{filters.q}%"
            q = q.filter(
                or_(
                    ElfisAuditEvent.action.ilike(like),
                    ElfisAuditEvent.message.ilike(like),
                    ElfisAuditEvent.target_display.ilike(like),
                    ElfisAuditEvent.actor_email.ilike(like),
                    ElfisAuditEvent.service.ilike(like),
                    ElfisAuditEvent.product.ilike(like),
                )
            )
        return q

    def _order(self, q, filters: AuditEventFilters):
        if filters.sort == "occurred_at_asc":
            return q.order_by(ElfisAuditEvent.occurred_at.asc(), ElfisAuditEvent.id.asc())
        return q.order_by(ElfisAuditEvent.occurred_at.desc(), ElfisAuditEvent.id.desc())

    def list_events(self, filters: AuditEventFilters | None = None) -> list[ElfisAuditEvent]:
        filters = filters or AuditEventFilters()
        q = self._db.query(ElfisAuditEvent)
        q = self._apply_filters(q, filters)
        q = self._order(q, filters)
        return q.offset(filters.offset).limit(filters.limit).all()

    def count_events(self, filters: AuditEventFilters | None = None) -> int:
        filters = filters or AuditEventFilters()
        q = self._db.query(func.count(ElfisAuditEvent.id))
        q = self._apply_filters(q, filters)
        return int(q.scalar() or 0)

    def iter_events(
        self,
        filters: AuditEventFilters,
        *,
        max_rows: int,
    ) -> Iterator[ElfisAuditEvent]:
        """Itère les événements pour export (borné, sans charger tout en mémoire)."""
        q = self._db.query(ElfisAuditEvent)
        q = self._apply_filters(q, filters)
        q = self._order(q, filters)
        yield from q.limit(max_rows).yield_per(200)

    def statistics(
        self,
        *,
        since: datetime | None = None,
        hours: int = 24,
    ) -> dict[str, Any]:
        if since is None:
            since = datetime.utcnow() - timedelta(hours=max(1, hours))
        base = self._db.query(ElfisAuditEvent).filter(ElfisAuditEvent.occurred_at >= since)
        total = base.count()
        success = base.filter(ElfisAuditEvent.success.is_(True)).count()
        failure = base.filter(ElfisAuditEvent.success.is_(False)).count()

        by_severity = dict(
            self._db.query(ElfisAuditEvent.severity, func.count(ElfisAuditEvent.id))
            .filter(ElfisAuditEvent.occurred_at >= since)
            .group_by(ElfisAuditEvent.severity)
            .all()
        )
        by_category = dict(
            self._db.query(ElfisAuditEvent.category, func.count(ElfisAuditEvent.id))
            .filter(ElfisAuditEvent.occurred_at >= since)
            .group_by(ElfisAuditEvent.category)
            .all()
        )
        by_action_rows = (
            self._db.query(ElfisAuditEvent.action, func.count(ElfisAuditEvent.id))
            .filter(ElfisAuditEvent.occurred_at >= since)
            .group_by(ElfisAuditEvent.action)
            .order_by(func.count(ElfisAuditEvent.id).desc())
            .limit(20)
            .all()
        )
        by_service_rows = (
            self._db.query(ElfisAuditEvent.service, func.count(ElfisAuditEvent.id))
            .filter(ElfisAuditEvent.occurred_at >= since)
            .filter(ElfisAuditEvent.service.isnot(None))
            .group_by(ElfisAuditEvent.service)
            .order_by(func.count(ElfisAuditEvent.id).desc())
            .limit(15)
            .all()
        )
        # Évolution quotidienne (agrégée, pas de charge ligne à ligne)
        dialect = self._db.bind.dialect.name if self._db.bind is not None else "sqlite"
        if dialect == "sqlite":
            day_expr = func.strftime("%Y-%m-%d", ElfisAuditEvent.occurred_at)
        else:
            day_expr = func.to_char(ElfisAuditEvent.occurred_at, "YYYY-MM-DD")
        by_day_rows = (
            self._db.query(day_expr, func.count(ElfisAuditEvent.id))
            .filter(ElfisAuditEvent.occurred_at >= since)
            .group_by(day_expr)
            .order_by(day_expr.asc())
            .all()
        )
        by_action = {str(k): int(v) for k, v in by_action_rows}
        by_sev = {str(k): int(v) for k, v in by_severity.items()}
        permission_denied = int(by_action.get("PERMISSION_DENIED", 0))
        login_failure = int(by_action.get("LOGIN_FAILURE", 0))
        iam_changes = int(by_action.get("ROLE_ASSIGNED", 0)) + int(by_action.get("ROLE_REMOVED", 0))
        warnings_errors = (
            int(by_sev.get("WARNING", 0))
            + int(by_sev.get("ERROR", 0))
            + int(by_sev.get("CRITICAL", 0))
        )
        return {
            "since": since.isoformat(),
            "hours": hours,
            "total": total,
            "success": success,
            "failure": failure,
            "by_severity": by_sev,
            "by_category": {str(k): int(v) for k, v in by_category.items()},
            "by_action": by_action,
            "by_service": {str(k): int(v) for k, v in by_service_rows if k},
            "by_day": {str(k): int(v) for k, v in by_day_rows if k},
            "permission_denied": permission_denied,
            "login_failure": login_failure,
            "iam_changes": iam_changes,
            "warnings_errors": warnings_errors,
        }

    def archive_exists(self, event_id: str) -> bool:
        return (
            self._db.query(ElfisAuditEventArchive.id)
            .filter(ElfisAuditEventArchive.id == event_id)
            .first()
            is not None
        )

    def insert_archive(self, row: ElfisAuditEventArchive, *, flush: bool = True) -> None:
        self._db.add(row)
        if flush:
            self._db.flush()

    def delete_live(self, event_id: str) -> int:
        return (
            self._db.query(ElfisAuditEvent)
            .filter(ElfisAuditEvent.id == event_id)
            .delete(synchronize_session=False)
        )

    def list_candidates_before(
        self,
        *,
        before: datetime,
        limit: int,
        category: str | None = None,
        severity: str | None = None,
    ) -> list[ElfisAuditEvent]:
        q = self._db.query(ElfisAuditEvent).filter(ElfisAuditEvent.occurred_at < before)
        if category:
            q = q.filter(ElfisAuditEvent.category == category)
        if severity:
            q = q.filter(ElfisAuditEvent.severity == severity)
        return (
            q.order_by(ElfisAuditEvent.occurred_at.asc(), ElfisAuditEvent.id.asc())
            .limit(limit)
            .all()
        )

    def count_archive(self) -> int:
        return int(self._db.query(func.count(ElfisAuditEventArchive.id)).scalar() or 0)

    def purge_archive_before(self, *, before: datetime, limit: int) -> int:
        ids = [
            r[0]
            for r in (
                self._db.query(ElfisAuditEventArchive.id)
                .filter(ElfisAuditEventArchive.archived_at < before)
                .order_by(ElfisAuditEventArchive.archived_at.asc())
                .limit(limit)
                .all()
            )
        ]
        if not ids:
            return 0
        return (
            self._db.query(ElfisAuditEventArchive)
            .filter(ElfisAuditEventArchive.id.in_(ids))
            .delete(synchronize_session=False)
        )
