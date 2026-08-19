"""Helpers Phase E — Platform Admin, ops, incidents, audit, reliability."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.events.event_models import ElfisEvent
from app.events.event_schemas import EventStatus
from app.jobs.job_models import ElfisJob
from app.jobs.job_types import JobNames, JobStatus
from app.platform_admin.admin_models import ElfisOperationalIncident


REASON = "Phase E — action opérationnelle contrôlée"
NOTE = "Phase E — note incident contrôlée"


def assert_safe_admin_body(body: Any) -> None:
    blob = str(body).lower()
    for forbidden in (
        "sk_live",
        "sk_test",
        "xkeysib-",
        "xsmtpsib-",
        "traceback",
        "authorization: bearer",
        "bearer eyj",
        "c:\\users\\",
        "/home/",
        "select * from",
        "-----begin",
    ):
        assert forbidden not in blob, f"fuite suspecte: {forbidden}"


def seed_failed_job(
    db: Session,
    *,
    org_id: int,
    job_name: str = JobNames.SYSTEM_HEALTH_CHECK,
    status: str = JobStatus.DEAD_LETTER,
    secret_in_error: str = "api_key=sk_live_SHOULD_NOT_LEAK",
) -> str:
    now = datetime.utcnow()
    jid = str(uuid4())
    row = ElfisJob(
        id=str(uuid4()),
        job_id=jid,
        job_name=job_name,
        organization_id=org_id,
        status=status,
        payload={"probe": True, "api_key": "sk_live_payload_secret"},
        attempt_count=3,
        max_attempts=5,
        last_error=secret_in_error,
        available_at=now,
        created_at=now,
        updated_at=now,
        failed_at=now,
        correlation_id=f"corr-job-{jid[:8]}",
    )
    db.add(row)
    db.commit()
    return jid


def seed_pending_job(db: Session, *, org_id: int) -> str:
    now = datetime.utcnow()
    jid = str(uuid4())
    db.add(
        ElfisJob(
            id=str(uuid4()),
            job_id=jid,
            job_name=JobNames.SYSTEM_HEALTH_CHECK,
            organization_id=org_id,
            status=JobStatus.PENDING,
            payload={"probe": True},
            available_at=now,
            created_at=now,
            updated_at=now,
            correlation_id=f"corr-pend-{jid[:8]}",
        )
    )
    db.commit()
    return jid


def seed_stale_job(db: Session, *, org_id: int, hours_ago: int = 3) -> str:
    started = datetime.utcnow() - timedelta(hours=hours_ago)
    jid = str(uuid4())
    db.add(
        ElfisJob(
            id=str(uuid4()),
            job_id=jid,
            job_name=JobNames.SYSTEM_HEALTH_CHECK,
            organization_id=org_id,
            status=JobStatus.PROCESSING,
            payload={},
            available_at=started,
            created_at=started,
            updated_at=started,
            started_at=started,
            locked_at=started,
            locked_by="worker-stale-phase-e",
            correlation_id=f"corr-stale-{jid[:8]}",
        )
    )
    db.commit()
    return jid


def seed_dead_letter_event(
    db: Session,
    *,
    org_id: int,
    event_name: str = "delivery.email.failed.v1",
) -> str:
    now = datetime.utcnow()
    eid = str(uuid4())
    db.add(
        ElfisEvent(
            id=str(uuid4()),
            event_id=eid,
            event_name=event_name,
            event_version=1,
            organization_id=org_id,
            aggregate_type="sales_document",
            aggregate_id="1",
            payload={
                "document_id": 1,
                "status": "failed",
                "api_key": "sk_live_event_secret",
                "pdf_bytes": "SHOULD_NOT_APPEAR",
            },
            metadata_json={"source": "phase_e"},
            status=EventStatus.dead_letter.value,
            attempt_count=5,
            max_attempts=5,
            available_at=now,
            failed_at=now,
            last_error="handler boom api_key=sk_live_err",
            correlation_id=f"corr-evt-{eid[:8]}",
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    return eid


def seed_open_incident(
    db: Session,
    *,
    org_id: int | None = None,
    incident_type: str = "job_dead_letter",
    source_id: str | None = None,
) -> str:
    now = datetime.utcnow()
    iid = str(uuid4())
    sid = source_id or str(uuid4())
    db.add(
        ElfisOperationalIncident(
            id=iid,
            incident_id=iid,
            organization_id=org_id,
            incident_type=incident_type,
            severity="error",
            status="open",
            title=f"Incident Phase E {incident_type}",
            summary="Résumé filtré Phase E",
            source_type="job",
            source_id=sid,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    return iid


def count_admin_audits(db: Session, *, action: str) -> int:
    from app.platform_admin.admin_models import ElfisAdminAuditLog

    return db.query(ElfisAdminAuditLog).filter(ElfisAdminAuditLog.action == action).count()
