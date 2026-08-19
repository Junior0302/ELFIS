"""Readiness consolidée + détection stale jobs/events."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.observability.health import details, ready
from app.platform_admin.admin_incident_service import AdminIncidentService
from app.platform_admin.admin_types import IncidentSeverity


class ReadinessService:
    def __init__(self, db: Session):
        self.db = db

    def readiness(self) -> dict[str, Any]:
        return ready(self.db)

    def details(self) -> dict[str, Any]:
        return details(self.db)

    def detect_stale_jobs(self) -> dict[str, Any]:
        from app.jobs.job_models import ElfisJob
        from app.jobs.job_types import JobStatus

        stale_seconds = int(getattr(settings, "elfis_stale_job_seconds", 1800))
        cutoff = datetime.utcnow() - timedelta(seconds=stale_seconds)
        rows = (
            self.db.query(ElfisJob)
            .filter(
                ElfisJob.status == JobStatus.PROCESSING,
                ElfisJob.updated_at < cutoff,
            )
            .limit(50)
            .all()
        )
        incidents = []
        incident_svc = AdminIncidentService(self.db)
        for job in rows:
            inc = incident_svc.upsert_incident(
                incident_type="stale_job",
                source_type="job",
                source_id=str(job.job_id),
                title=f"Job stale: {job.job_name}",
                summary=f"Processing depuis > {stale_seconds}s",
                severity=IncidentSeverity.WARNING,
                organization_id=getattr(job, "organization_id", None),
            )
            incidents.append(inc.incident_id)
        return {
            "stale_count": len(rows),
            "stale_seconds": stale_seconds,
            "job_ids": [j.job_id for j in rows],
            "incident_ids": incidents,
            "auto_failed": False,
            "note": "V1 : incident uniquement — pas de fail automatique des jobs sync",
        }

    def detect_stale_events(self) -> dict[str, Any]:
        from app.events.event_models import ElfisEvent

        stale_seconds = int(getattr(settings, "elfis_stale_event_seconds", 1800))
        cutoff = datetime.utcnow() - timedelta(seconds=stale_seconds)
        # Statuts processing typiques
        q = self.db.query(ElfisEvent).filter(ElfisEvent.status == "processing")
        if hasattr(ElfisEvent, "updated_at"):
            q = q.filter(ElfisEvent.updated_at < cutoff)
        elif hasattr(ElfisEvent, "locked_at"):
            q = q.filter(ElfisEvent.locked_at < cutoff)
        rows = q.limit(50).all()
        incidents = []
        incident_svc = AdminIncidentService(self.db)
        for ev in rows:
            eid = getattr(ev, "event_id", None) or getattr(ev, "id", None)
            inc = incident_svc.upsert_incident(
                incident_type="stale_event",
                source_type="event",
                source_id=str(eid),
                title=f"Event stale: {getattr(ev, 'event_name', 'unknown')}",
                summary=f"Processing depuis > {stale_seconds}s",
                severity=IncidentSeverity.WARNING,
                organization_id=getattr(ev, "organization_id", None),
            )
            incidents.append(inc.incident_id)
        return {
            "stale_count": len(rows),
            "stale_seconds": stale_seconds,
            "event_ids": [getattr(r, "event_id", r.id) for r in rows],
            "incident_ids": incidents,
            "auto_republish": False,
        }
