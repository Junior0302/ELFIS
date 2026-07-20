"""Persistance Job Queue."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, bindparam, or_, text
from sqlalchemy.orm import Session

from app.jobs.job_models import ElfisJob, ElfisJobAttempt
from app.jobs.job_types import AttemptStatus, JobStatus


class JobRepository:
    def __init__(self, db: Session):
        self._db = db

    def find_by_job_id(self, job_id: str) -> ElfisJob | None:
        return self._db.query(ElfisJob).filter(ElfisJob.job_id == job_id).first()

    def find_by_idempotency_key(self, key: str) -> ElfisJob | None:
        if not key:
            return None
        return (
            self._db.query(ElfisJob)
            .filter(ElfisJob.idempotency_key == key)
            .order_by(ElfisJob.created_at.asc())
            .first()
        )

    def create_job(self, job: ElfisJob, *, commit: bool = True) -> ElfisJob:
        self._db.add(job)
        if commit:
            self._db.commit()
            self._db.refresh(job)
        else:
            self._db.flush()
        return job

    def save_job(self, job: ElfisJob, *, commit: bool = True) -> ElfisJob:
        job.updated_at = datetime.utcnow()
        self._db.add(job)
        if commit:
            self._db.commit()
            self._db.refresh(job)
        else:
            self._db.flush()
        return job

    def create_attempt(self, attempt: ElfisJobAttempt, *, commit: bool = True) -> ElfisJobAttempt:
        self._db.add(attempt)
        if commit:
            self._db.commit()
            self._db.refresh(attempt)
        else:
            self._db.flush()
        return attempt

    def save_attempt(self, attempt: ElfisJobAttempt, *, commit: bool = True) -> ElfisJobAttempt:
        self._db.add(attempt)
        if commit:
            self._db.commit()
            self._db.refresh(attempt)
        else:
            self._db.flush()
        return attempt

    def list_attempts(self, job_id: str) -> list[ElfisJobAttempt]:
        return (
            self._db.query(ElfisJobAttempt)
            .filter(ElfisJobAttempt.job_id == job_id)
            .order_by(ElfisJobAttempt.attempt_number.asc())
            .all()
        )

    def find_attempt(self, job_id: str, attempt_number: int) -> ElfisJobAttempt | None:
        return (
            self._db.query(ElfisJobAttempt)
            .filter(
                ElfisJobAttempt.job_id == job_id,
                ElfisJobAttempt.attempt_number == attempt_number,
            )
            .first()
        )

    def list_jobs(
        self,
        *,
        organization_id: int | None = None,
        user_id: int | None = None,
        job_name: str | None = None,
        queue_name: str | None = None,
        status: str | None = None,
        worker_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ElfisJob], int]:
        q = self._db.query(ElfisJob)
        if organization_id is not None:
            q = q.filter(ElfisJob.organization_id == organization_id)
        if user_id is not None:
            q = q.filter(ElfisJob.user_id == user_id)
        if job_name:
            q = q.filter(ElfisJob.job_name == job_name)
        if queue_name:
            q = q.filter(ElfisJob.queue_name == queue_name)
        if status:
            q = q.filter(ElfisJob.status == status)
        if worker_id:
            q = q.filter(ElfisJob.locked_by == worker_id)
        if date_from is not None:
            q = q.filter(ElfisJob.created_at >= date_from)
        if date_to is not None:
            q = q.filter(ElfisJob.created_at <= date_to)
        total = q.count()
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        rows = (
            q.order_by(ElfisJob.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def claim_jobs(
        self,
        *,
        worker_id: str,
        queues: list[str],
        batch_size: int,
        lock_timeout_seconds: int,
    ) -> list[ElfisJob]:
        """Réserve un lot de jobs (transaction courte). Concurrence réelle = Postgres."""
        now = datetime.utcnow()
        lock_expired_before = now - timedelta(seconds=max(30, lock_timeout_seconds))
        queues = [q for q in queues if q] or ["default"]
        dialect = self._db.bind.dialect.name if self._db.bind is not None else "sqlite"

        if dialect == "postgresql":
            return self._claim_jobs_postgres(
                worker_id=worker_id,
                queues=queues,
                batch_size=batch_size,
                now=now,
                lock_expired_before=lock_expired_before,
            )
        return self._claim_jobs_sqlite(
            worker_id=worker_id,
            queues=queues,
            batch_size=batch_size,
            now=now,
            lock_expired_before=lock_expired_before,
        )

    def _claim_jobs_postgres(
        self,
        *,
        worker_id: str,
        queues: list[str],
        batch_size: int,
        now: datetime,
        lock_expired_before: datetime,
    ) -> list[ElfisJob]:
        sql = text(
            """
            SELECT id FROM elfis_jobs
            WHERE queue_name IN :queues
              AND (
                (status IN ('pending', 'scheduled', 'retry') AND available_at <= :now)
                OR (
                    status = 'processing'
                    AND (
                        (heartbeat_at IS NOT NULL AND heartbeat_at < :lock_expired_before)
                        OR (heartbeat_at IS NULL AND locked_at IS NOT NULL
                            AND locked_at < :lock_expired_before)
                    )
                )
              )
            ORDER BY priority ASC, available_at ASC, created_at ASC
            LIMIT :batch_size
            FOR UPDATE SKIP LOCKED
            """
        ).bindparams(
            bindparam("queues", expanding=True),
        )
        ids = [
            row[0]
            for row in self._db.execute(
                sql,
                {
                    "queues": queues,
                    "now": now,
                    "lock_expired_before": lock_expired_before,
                    "batch_size": batch_size,
                },
            ).fetchall()
        ]
        if not ids:
            return []
        rows = (
            self._db.query(ElfisJob)
            .filter(ElfisJob.id.in_(ids))
            .order_by(
                ElfisJob.priority.asc(),
                ElfisJob.available_at.asc(),
                ElfisJob.created_at.asc(),
            )
            .all()
        )
        claimed: list[ElfisJob] = []
        for row in rows:
            self._mark_processing(row, worker_id=worker_id, now=now)
            claimed.append(row)
        self._db.commit()
        for row in claimed:
            self._db.refresh(row)
        return claimed

    def _claim_jobs_sqlite(
        self,
        *,
        worker_id: str,
        queues: list[str],
        batch_size: int,
        now: datetime,
        lock_expired_before: datetime,
    ) -> list[ElfisJob]:
        candidates = (
            self._db.query(ElfisJob)
            .filter(
                ElfisJob.queue_name.in_(queues),
                or_(
                    and_(
                        ElfisJob.status.in_(
                            [JobStatus.PENDING, JobStatus.SCHEDULED, JobStatus.RETRY]
                        ),
                        ElfisJob.available_at <= now,
                    ),
                    and_(
                        ElfisJob.status == JobStatus.PROCESSING,
                        or_(
                            and_(
                                ElfisJob.heartbeat_at.isnot(None),
                                ElfisJob.heartbeat_at < lock_expired_before,
                            ),
                            and_(
                                ElfisJob.heartbeat_at.is_(None),
                                ElfisJob.locked_at.isnot(None),
                                ElfisJob.locked_at < lock_expired_before,
                            ),
                        ),
                    ),
                ),
            )
            .order_by(
                ElfisJob.priority.asc(),
                ElfisJob.available_at.asc(),
                ElfisJob.created_at.asc(),
            )
            .limit(batch_size)
            .all()
        )
        claimed: list[ElfisJob] = []
        for row in candidates:
            updated = (
                self._db.query(ElfisJob)
                .filter(
                    ElfisJob.id == row.id,
                    or_(
                        ElfisJob.status.in_(
                            [JobStatus.PENDING, JobStatus.SCHEDULED, JobStatus.RETRY]
                        ),
                        and_(
                            ElfisJob.status == JobStatus.PROCESSING,
                            or_(
                                and_(
                                    ElfisJob.heartbeat_at.isnot(None),
                                    ElfisJob.heartbeat_at < lock_expired_before,
                                ),
                                and_(
                                    ElfisJob.heartbeat_at.is_(None),
                                    ElfisJob.locked_at < lock_expired_before,
                                ),
                            ),
                        ),
                    ),
                )
                .update(
                    {
                        ElfisJob.status: JobStatus.PROCESSING,
                        ElfisJob.locked_at: now,
                        ElfisJob.locked_by: worker_id,
                        ElfisJob.heartbeat_at: now,
                        ElfisJob.started_at: row.started_at or now,
                        ElfisJob.updated_at: now,
                        ElfisJob.attempt_count: ElfisJob.attempt_count + 1,
                        ElfisJob.progress: 0,
                        ElfisJob.progress_message: None,
                        ElfisJob.last_error: None,
                    },
                    synchronize_session=False,
                )
            )
            if updated:
                claimed.append(row)
                attempt_number = (row.attempt_count or 0) + 1
                self._db.add(
                    ElfisJobAttempt(
                        id=str(uuid.uuid4()),
                        job_id=row.job_id,
                        attempt_number=attempt_number,
                        worker_id=worker_id,
                        status=AttemptStatus.PROCESSING,
                        started_at=now,
                        created_at=now,
                    )
                )
        self._db.commit()
        result: list[ElfisJob] = []
        for row in claimed:
            refreshed = self.find_by_job_id(row.job_id)
            if refreshed and refreshed.locked_by == worker_id:
                result.append(refreshed)
        return result

    def _mark_processing(self, row: ElfisJob, *, worker_id: str, now: datetime) -> None:
        row.attempt_count = (row.attempt_count or 0) + 1
        row.status = JobStatus.PROCESSING
        row.locked_at = now
        row.locked_by = worker_id
        row.heartbeat_at = now
        if row.started_at is None:
            row.started_at = now
        row.progress = 0
        row.progress_message = None
        row.last_error = None
        row.updated_at = now
        self._db.add(
            ElfisJobAttempt(
                id=str(uuid.uuid4()),
                job_id=row.job_id,
                attempt_number=row.attempt_count,
                worker_id=worker_id,
                status=AttemptStatus.PROCESSING,
                started_at=now,
                created_at=now,
            )
        )
