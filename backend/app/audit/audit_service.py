"""AuditService — enregistrement central, jamais bloquant pour le métier."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.audit.audit_context import AuditContext, current_audit_context
from app.audit.audit_event import AuditEventDraft, normalize_action
from app.audit.audit_exceptions import AuditPersistenceError
from app.audit.audit_filters import AuditEventFilters
from app.audit.audit_models import ElfisAuditEvent
from app.audit.audit_repository import AuditRepository
from app.audit.audit_sanitize import (
    sanitize_ip,
    sanitize_message,
    sanitize_metadata,
    sanitize_user_agent,
)
from app.audit.audit_types import AuditCategory, AuditStatus, Severity

logger = logging.getLogger(__name__)


class AuditService:
    """Service d'audit testable, utilisable hors FastAPI.

    Par défaut, les écritures utilisent une session isolée (SessionLocal)
    pour ne jamais contaminer une transaction métier.
    """

    def __init__(
        self,
        db: Session | None = None,
        *,
        isolated_writes: bool = True,
    ) -> None:
        self._db = db
        self._isolated_writes = isolated_writes

    def _read_db(self) -> Session:
        if self._db is not None:
            return self._db
        from app.database import SessionLocal

        return SessionLocal()

    def record(
        self,
        action: str,
        *,
        severity: str | Severity = Severity.INFO,
        category: str | AuditCategory = AuditCategory.OTHER,
        status: str | AuditStatus | None = None,
        success: bool = True,
        message: str | None = None,
        context: AuditContext | None = None,
        actor_user_id: int | None = None,
        actor_email: str | None = None,
        organization_id: int | None = None,
        product: str | None = None,
        service: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        target_display: str | None = None,
        request_id: str | None = None,
        correlation_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
        duration_ms: int | None = None,
        occurred_at: datetime | None = None,
        commit: bool = True,
    ) -> ElfisAuditEvent | None:
        """Enregistre un événement. Retourne None si l'écriture échoue (sans lever)."""
        try:
            return self._record_or_raise(
                action,
                severity=severity,
                category=category,
                status=status,
                success=success,
                message=message,
                context=context,
                actor_user_id=actor_user_id,
                actor_email=actor_email,
                organization_id=organization_id,
                product=product,
                service=service,
                target_type=target_type,
                target_id=target_id,
                target_display=target_display,
                request_id=request_id,
                correlation_id=correlation_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata,
                duration_ms=duration_ms,
                occurred_at=occurred_at,
                commit=commit,
            )
        except Exception as exc:  # noqa: BLE001 — audit ne doit jamais casser le métier
            logger.warning(
                "audit_write_failed",
                extra={
                    "action": str(action),
                    "error": type(exc).__name__,
                    "error_message": str(exc)[:200],
                },
            )
            return None

    def log(self, action: str, **kwargs: Any) -> ElfisAuditEvent | None:
        """Alias de record()."""
        return self.record(action, **kwargs)

    async def record_async(self, action: str, **kwargs: Any) -> ElfisAuditEvent | None:
        """Compat async — l'écriture reste synchrone (SQLAlchemy sync)."""
        return self.record(action, **kwargs)

    def _record_or_raise(
        self,
        action: str,
        *,
        severity: str | Severity = Severity.INFO,
        category: str | AuditCategory = AuditCategory.OTHER,
        status: str | AuditStatus | None = None,
        success: bool = True,
        message: str | None = None,
        context: AuditContext | None = None,
        actor_user_id: int | None = None,
        actor_email: str | None = None,
        organization_id: int | None = None,
        product: str | None = None,
        service: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        target_display: str | None = None,
        request_id: str | None = None,
        correlation_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
        duration_ms: int | None = None,
        occurred_at: datetime | None = None,
        commit: bool = True,
    ) -> ElfisAuditEvent:
        ctx = (context or current_audit_context())
        sev = severity.value if isinstance(severity, Severity) else str(severity).upper()
        cat = category.value if isinstance(category, AuditCategory) else str(category).upper()
        if status is None:
            st = AuditStatus.SUCCESS.value if success else AuditStatus.FAILURE.value
        else:
            st = status.value if isinstance(status, AuditStatus) else str(status).upper()

        draft = AuditEventDraft(
            id=str(uuid4()),
            action=normalize_action(action),
            severity=sev,
            category=cat,
            status=st,
            success=bool(success),
            message=sanitize_message(message),
            actor_user_id=actor_user_id if actor_user_id is not None else ctx.actor_user_id,
            actor_email=actor_email if actor_email is not None else ctx.actor_email,
            organization_id=organization_id if organization_id is not None else ctx.organization_id,
            product=product if product is not None else ctx.product,
            service=service if service is not None else ctx.service,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            target_display=sanitize_message(target_display, max_len=255),
            request_id=request_id if request_id is not None else ctx.request_id,
            correlation_id=correlation_id if correlation_id is not None else ctx.correlation_id,
            ip_address=sanitize_ip(ip_address if ip_address is not None else ctx.ip_address),
            user_agent=sanitize_user_agent(user_agent if user_agent is not None else ctx.user_agent),
            metadata=sanitize_metadata(metadata) or {},
            duration_ms=duration_ms,
            occurred_at=occurred_at or datetime.utcnow(),
        )

        row = ElfisAuditEvent(
            id=draft.ensure_id(),
            occurred_at=draft.occurred_at,
            severity=draft.severity,
            category=draft.category,
            action=draft.action,
            status=draft.status,
            actor_user_id=draft.actor_user_id,
            actor_email=(draft.actor_email or None) and str(draft.actor_email)[:255],
            organization_id=draft.organization_id,
            product=draft.product,
            service=draft.service,
            target_type=draft.target_type,
            target_id=draft.target_id,
            target_display=draft.target_display,
            request_id=draft.request_id,
            correlation_id=draft.correlation_id,
            ip_address=draft.ip_address,
            user_agent=draft.user_agent,
            metadata_json=draft.metadata or None,
            message=draft.message,
            duration_ms=draft.duration_ms,
            success=draft.success,
        )

        if self._isolated_writes or self._db is None:
            return self._persist_isolated(row, commit=commit)
        return self._persist_shared(row, commit=commit)

    def _persist_isolated(self, row: ElfisAuditEvent, *, commit: bool) -> ElfisAuditEvent:
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            AuditRepository(db).insert_event(row, flush=True)
            if commit:
                db.commit()
                db.refresh(row)
            return row
        except Exception as exc:
            db.rollback()
            raise AuditPersistenceError(str(exc)) from exc
        finally:
            db.close()

    def _persist_shared(self, row: ElfisAuditEvent, *, commit: bool) -> ElfisAuditEvent:
        assert self._db is not None
        try:
            # SAVEPOINT pour ne pas annuler la transaction métier en cas d'échec
            with self._db.begin_nested():
                AuditRepository(self._db).insert_event(row, flush=True)
            if commit:
                self._db.commit()
            return row
        except Exception as exc:
            raise AuditPersistenceError(str(exc)) from exc

    # --- Lecture (peut lever) ---

    def get_event(self, event_id: str) -> ElfisAuditEvent | None:
        db = self._read_db()
        owns = self._db is None
        try:
            return AuditRepository(db).find_by_id(event_id)
        finally:
            if owns:
                db.close()

    def list_events(self, filters: AuditEventFilters | None = None) -> list[ElfisAuditEvent]:
        db = self._read_db()
        owns = self._db is None
        try:
            return AuditRepository(db).list_events(filters)
        finally:
            if owns:
                db.close()

    def count_events(self, filters: AuditEventFilters | None = None) -> int:
        db = self._read_db()
        owns = self._db is None
        try:
            return AuditRepository(db).count_events(filters)
        finally:
            if owns:
                db.close()

    def find_by_correlation(self, correlation_id: str, *, limit: int = 100) -> list[ElfisAuditEvent]:
        db = self._read_db()
        owns = self._db is None
        try:
            return AuditRepository(db).find_by_correlation(correlation_id, limit=limit)
        finally:
            if owns:
                db.close()

    def find_recent(self, *, limit: int = 50) -> list[ElfisAuditEvent]:
        db = self._read_db()
        owns = self._db is None
        try:
            return AuditRepository(db).find_recent(limit=limit)
        finally:
            if owns:
                db.close()

    def statistics(self, *, hours: int = 24) -> dict[str, Any]:
        db = self._read_db()
        owns = self._db is None
        try:
            return AuditRepository(db).statistics(hours=hours)
        finally:
            if owns:
                db.close()
