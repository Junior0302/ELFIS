"""Contexte d'exécution d'un job (exposé aux handlers)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.jobs.job_models import ElfisJob


class JobContext:
    """API contrôlée pour les handlers — pas d'accès libre à la session métier."""

    def __init__(
        self,
        *,
        job_id: str,
        organization_id: int | None,
        user_id: int | None,
        correlation_id: str | None,
        attempt_number: int,
        worker_id: str,
        session_factory: Callable[[], "Session"] | None = None,
        db: "Session | None" = None,
    ):
        self.job_id = job_id
        self.organization_id = organization_id
        self.user_id = user_id
        self.correlation_id = correlation_id
        self.attempt_number = attempt_number
        self.worker_id = worker_id
        self._session_factory = session_factory
        self._db = db
        self._cancelled_cache: bool | None = None

    @property
    def db(self) -> "Session":
        if self._db is None:
            raise RuntimeError("JobContext.db indisponible hors exécution worker")
        return self._db

    def update_progress(self, progress: int, message: str | None = None) -> None:
        from app.events.event_bus import safe_publish
        from app.events.event_schemas import DomainEvent
        from app.events.event_types import EventNames
        from app.jobs.job_models import ElfisJob
        from app.jobs.job_types import JobStatus

        progress = max(0, min(100, int(progress)))
        msg = (message or "")[:255] or None

        def _apply(db: "Session") -> ElfisJob | None:
            job = db.query(ElfisJob).filter(ElfisJob.job_id == self.job_id).first()
            if not job:
                return None
            if job.status != JobStatus.PROCESSING:
                return job
            job.progress = progress
            job.progress_message = msg
            job.heartbeat_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            db.commit()
            corr = None
            if job.correlation_id:
                try:
                    corr = uuid.UUID(str(job.correlation_id))
                except (TypeError, ValueError):
                    corr = None
            safe_publish(
                db,
                DomainEvent(
                    event_name=EventNames.JOB_PROGRESS,
                    organization_id=job.organization_id if job.organization_id is not None else 0,
                    aggregate_type="job",
                    aggregate_id=job.job_id,
                    payload={
                        "job_id": job.job_id,
                        "job_name": job.job_name,
                        "organization_id": job.organization_id,
                        "queue_name": job.queue_name,
                        "status": job.status,
                        "attempt_count": job.attempt_count,
                        "progress": job.progress,
                        "correlation_id": job.correlation_id,
                    },
                    metadata={"source": "job_worker"},
                    correlation_id=corr or uuid.uuid4(),
                ),
            )
            return job

        self._with_session(_apply)

    def is_cancelled(self) -> bool:
        from app.jobs.job_models import ElfisJob
        from app.jobs.job_types import JobStatus

        if self._cancelled_cache is True:
            return True

        def _check(db: "Session") -> bool:
            job = db.query(ElfisJob).filter(ElfisJob.job_id == self.job_id).first()
            if not job:
                return False
            return job.status == JobStatus.CANCELLED

        self._cancelled_cache = self._with_session(_check) or False
        return self._cancelled_cache

    def heartbeat(self) -> None:
        from app.jobs.job_models import ElfisJob
        from app.jobs.job_types import JobStatus

        def _beat(db: "Session") -> None:
            job = db.query(ElfisJob).filter(ElfisJob.job_id == self.job_id).first()
            if not job or job.status != JobStatus.PROCESSING:
                return
            now = datetime.utcnow()
            job.heartbeat_at = now
            job.updated_at = now
            db.commit()

        self._with_session(_beat)

    def _with_session(self, fn):
        if self._db is not None:
            return fn(self._db)
        if self._session_factory is None:
            return None
        db = self._session_factory()
        try:
            return fn(db)
        finally:
            db.close()
