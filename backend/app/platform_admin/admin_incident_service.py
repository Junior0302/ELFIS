"""Incidents opérationnels — déduplication par source."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models_saas import User
from app.platform_admin.admin_audit_service import AdminAuditService
from app.platform_admin.admin_exceptions import AdminNotFoundError
from app.platform_admin.admin_models import ElfisOperationalIncident
from app.platform_admin.admin_security import clamp_page, clamp_page_size, require_action_reason
from app.platform_admin.admin_types import IncidentSeverity, IncidentStatus


class AdminIncidentService:
    def __init__(self, db: Session):
        self.db = db
        self.audit = AdminAuditService(db)

    def upsert_incident(
        self,
        *,
        incident_type: str,
        source_type: str,
        source_id: str,
        title: str,
        summary: str | None = None,
        severity: str = IncidentSeverity.ERROR,
        organization_id: int | None = None,
    ) -> ElfisOperationalIncident:
        existing = (
            self.db.query(ElfisOperationalIncident)
            .filter(
                ElfisOperationalIncident.source_type == source_type,
                ElfisOperationalIncident.source_id == source_id,
                ElfisOperationalIncident.incident_type == incident_type,
            )
            .first()
        )
        now = datetime.utcnow()
        if existing:
            existing.last_seen_at = now
            existing.updated_at = now
            if existing.status in (IncidentStatus.RESOLVED, IncidentStatus.IGNORED):
                # Ne pas réouvrir automatiquement — juste rafraîchir last_seen
                pass
            elif existing.severity != severity:
                existing.severity = severity
            self.db.flush()
            return existing
        row = ElfisOperationalIncident(
            id=str(uuid4()),
            incident_id=str(uuid4()),
            organization_id=organization_id,
            incident_type=incident_type,
            severity=severity,
            status=IncidentStatus.OPEN,
            source_type=source_type,
            source_id=source_id,
            title=title[:255],
            summary=summary,
            first_seen_at=now,
            last_seen_at=now,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def list_incidents(
        self,
        *,
        organization_id: int | None = None,
        status: str | None = None,
        incident_type: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        page_n = clamp_page(page)
        size = clamp_page_size(page_size)
        q = self.db.query(ElfisOperationalIncident)
        if organization_id:
            q = q.filter(ElfisOperationalIncident.organization_id == organization_id)
        if status:
            q = q.filter(ElfisOperationalIncident.status == status)
        if incident_type:
            q = q.filter(ElfisOperationalIncident.incident_type == incident_type)
        total = q.count()
        rows = (
            q.order_by(ElfisOperationalIncident.last_seen_at.desc())
            .offset((page_n - 1) * size)
            .limit(size)
            .all()
        )
        return {
            "incidents": [self._serialize(r) for r in rows],
            "total": total,
            "page": page_n,
            "page_size": size,
        }

    def get_incident(self, incident_id: str) -> dict[str, Any]:
        row = (
            self.db.query(ElfisOperationalIncident)
            .filter(ElfisOperationalIncident.incident_id == incident_id)
            .first()
        )
        if not row:
            raise AdminNotFoundError("Incident introuvable")
        return self._serialize(row)

    def acknowledge(self, incident_id: str, *, actor: User, note: str, ip: str | None = None) -> dict:
        return self._transition(
            incident_id,
            actor=actor,
            note=note,
            new_status=IncidentStatus.ACKNOWLEDGED,
            action="incident.acknowledge",
            ip=ip,
        )

    def resolve(self, incident_id: str, *, actor: User, note: str, ip: str | None = None) -> dict:
        return self._transition(
            incident_id,
            actor=actor,
            note=note,
            new_status=IncidentStatus.RESOLVED,
            action="incident.resolve",
            ip=ip,
            set_resolved=True,
        )

    def ignore(self, incident_id: str, *, actor: User, note: str, ip: str | None = None) -> dict:
        return self._transition(
            incident_id,
            actor=actor,
            note=note,
            new_status=IncidentStatus.IGNORED,
            action="incident.ignore",
            ip=ip,
            set_resolved=True,
        )

    def scan_dead_letters(self) -> int:
        """Crée des incidents pour jobs/events dead_letter (idempotent)."""
        created = 0
        try:
            from app.jobs.job_models import ElfisJob
            from app.platform_admin.admin_types import IncidentTypes

            for job in (
                self.db.query(ElfisJob).filter(ElfisJob.status == "dead_letter").limit(100).all()
            ):
                before = self.db.query(ElfisOperationalIncident).count()
                self.upsert_incident(
                    incident_type=IncidentTypes.JOB_DEAD_LETTER,
                    source_type="job",
                    source_id=job.job_id,
                    title=f"Job dead letter: {job.job_name}",
                    summary=(job.last_error or "")[:500],
                    severity=IncidentSeverity.ERROR,
                    organization_id=job.organization_id,
                )
                if self.db.query(ElfisOperationalIncident).count() > before:
                    created += 1
        except Exception:
            pass
        try:
            from app.events.event_models import ElfisEvent
            from app.platform_admin.admin_types import IncidentTypes

            for ev in (
                self.db.query(ElfisEvent).filter(ElfisEvent.status == "dead_letter").limit(100).all()
            ):
                self.upsert_incident(
                    incident_type=IncidentTypes.EVENT_DEAD_LETTER,
                    source_type="event",
                    source_id=ev.event_id,
                    title=f"Event dead letter: {ev.event_name}",
                    summary=(ev.last_error or "")[:500],
                    severity=IncidentSeverity.ERROR,
                    organization_id=ev.organization_id,
                )
        except Exception:
            pass
        return created

    def _transition(
        self,
        incident_id: str,
        *,
        actor: User,
        note: str,
        new_status: str,
        action: str,
        ip: str | None,
        set_resolved: bool = False,
    ) -> dict:
        cleaned = require_action_reason(note)
        row = (
            self.db.query(ElfisOperationalIncident)
            .filter(ElfisOperationalIncident.incident_id == incident_id)
            .first()
        )
        if not row:
            raise AdminNotFoundError("Incident introuvable")
        prev = {"incident_status": row.status}
        row.status = new_status
        row.updated_at = datetime.utcnow()
        if set_resolved:
            row.resolved_at = datetime.utcnow()
            row.resolved_by = actor.id
            row.resolution_note = cleaned
        self.audit.record(
            actor=actor,
            action=action,
            target_type="incident",
            target_id=incident_id,
            organization_id=row.organization_id,
            reason=cleaned,
            previous_state=prev,
            new_state={"incident_status": new_status},
            ip=ip,
        )
        self.db.flush()
        return self._serialize(row)

    def _serialize(self, row: ElfisOperationalIncident) -> dict[str, Any]:
        return {
            "incident_id": row.incident_id,
            "organization_id": row.organization_id,
            "incident_type": row.incident_type,
            "severity": row.severity,
            "status": row.status,
            "source_type": row.source_type,
            "source_id": row.source_id,
            "title": row.title,
            "summary": row.summary,
            "first_seen_at": row.first_seen_at,
            "last_seen_at": row.last_seen_at,
            "resolved_at": row.resolved_at,
            "resolved_by": row.resolved_by,
            "resolution_note": row.resolution_note,
        }
