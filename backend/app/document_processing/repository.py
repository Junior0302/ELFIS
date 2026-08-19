"""Repository Document Processing — claim SKIP LOCKED."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session
from sqlalchemy.sql import bindparam

from app.document_processing.models import (
    ElfisDocumentProcessingAttempt,
    ElfisDocumentProcessingJob,
    ElfisDocumentProcessingStep,
)
from app.document_processing.types import ProcessingJobStatus, ProcessingStepStatus


def _naive_utc(value: datetime | None) -> datetime | None:
    """Normalise timestamptz PG (aware) vs datetime.utcnow() (naive)."""
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


class DocumentProcessingRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_job(self, job_id: str) -> ElfisDocumentProcessingJob | None:
        return self._db.get(ElfisDocumentProcessingJob, job_id)

    def get_by_idempotency(
        self, organization_id: int, idempotency_key: str
    ) -> ElfisDocumentProcessingJob | None:
        return (
            self._db.query(ElfisDocumentProcessingJob)
            .filter(
                ElfisDocumentProcessingJob.organization_id == organization_id,
                ElfisDocumentProcessingJob.idempotency_key == idempotency_key,
            )
            .first()
        )

    def create_job(self, job: ElfisDocumentProcessingJob, *, commit: bool = False) -> ElfisDocumentProcessingJob:
        self._db.add(job)
        self._db.flush()
        if commit:
            self._db.commit()
            self._db.refresh(job)
        return job

    def create_step(self, step: ElfisDocumentProcessingStep, *, commit: bool = False) -> ElfisDocumentProcessingStep:
        self._db.add(step)
        self._db.flush()
        if commit:
            self._db.commit()
        return step

    def create_attempt(
        self, attempt: ElfisDocumentProcessingAttempt, *, commit: bool = False
    ) -> ElfisDocumentProcessingAttempt:
        self._db.add(attempt)
        self._db.flush()
        if commit:
            self._db.commit()
        return attempt

    def list_steps(self, job_id: str) -> list[ElfisDocumentProcessingStep]:
        return (
            self._db.query(ElfisDocumentProcessingStep)
            .filter(ElfisDocumentProcessingStep.job_id == job_id)
            .order_by(ElfisDocumentProcessingStep.sequence_number.asc())
            .all()
        )

    def list_attempts(self, job_id: str) -> list[ElfisDocumentProcessingAttempt]:
        return (
            self._db.query(ElfisDocumentProcessingAttempt)
            .filter(ElfisDocumentProcessingAttempt.job_id == job_id)
            .order_by(
                ElfisDocumentProcessingAttempt.started_at.asc(),
                ElfisDocumentProcessingAttempt.attempt_number.asc(),
            )
            .all()
        )

    def list_jobs(
        self,
        *,
        organization_id: int | None,
        status: str | None = None,
        document_id: str | None = None,
        pipeline_key: str | None = None,
        product: str | None = None,
        limit: int = 50,
        offset: int = 0,
        platform: bool = False,
    ) -> tuple[list[ElfisDocumentProcessingJob], int]:
        q = self._db.query(ElfisDocumentProcessingJob)
        if not platform:
            if organization_id is None:
                return [], 0
            q = q.filter(ElfisDocumentProcessingJob.organization_id == organization_id)
        elif organization_id is not None:
            q = q.filter(ElfisDocumentProcessingJob.organization_id == organization_id)
        if status:
            q = q.filter(ElfisDocumentProcessingJob.status == status)
        if document_id:
            q = q.filter(ElfisDocumentProcessingJob.document_id == document_id)
        if pipeline_key:
            q = q.filter(ElfisDocumentProcessingJob.pipeline_key == pipeline_key)
        if product:
            q = q.filter(ElfisDocumentProcessingJob.product == product)
        total = q.count()
        items = (
            q.order_by(
                ElfisDocumentProcessingJob.created_at.desc(),
                ElfisDocumentProcessingJob.id.desc(),
            )
            .offset(max(0, offset))
            .limit(max(1, min(limit, 100)))
            .all()
        )
        return items, int(total)

    def claim_jobs(
        self,
        *,
        worker_id: str,
        batch_size: int,
        lease_seconds: int,
        pipeline_key: str | None = None,
    ) -> list[ElfisDocumentProcessingJob]:
        now = datetime.utcnow()
        lock_expired_before = now - timedelta(seconds=max(1, lease_seconds))
        dialect = self._db.bind.dialect.name if self._db.bind is not None else "sqlite"
        if dialect == "postgresql":
            return self._claim_postgres(
                worker_id=worker_id,
                batch_size=batch_size,
                now=now,
                lock_expired_before=lock_expired_before,
                lease_seconds=lease_seconds,
                pipeline_key=pipeline_key,
            )
        return self._claim_sqlite(
            worker_id=worker_id,
            batch_size=batch_size,
            now=now,
            lock_expired_before=lock_expired_before,
            lease_seconds=lease_seconds,
            pipeline_key=pipeline_key,
        )

    def _claim_postgres(
        self,
        *,
        worker_id: str,
        batch_size: int,
        now: datetime,
        lock_expired_before: datetime,
        lease_seconds: int,
        pipeline_key: str | None,
    ) -> list[ElfisDocumentProcessingJob]:
        pipe_clause = ""
        params: dict = {
            "now": now,
            "lock_expired_before": lock_expired_before,
            "batch_size": batch_size,
        }
        if pipeline_key:
            pipe_clause = "AND pipeline_key = :pipeline_key"
            params["pipeline_key"] = pipeline_key
        sql = text(
            f"""
            SELECT id FROM elfis_document_processing_jobs
            WHERE (
                (status IN ('queued', 'retrying') AND scheduled_at <= :now)
                OR (
                    status = 'running'
                    AND locked_until IS NOT NULL
                    AND locked_until < :now
                )
                OR (
                    status = 'running'
                    AND heartbeat_at IS NOT NULL
                    AND heartbeat_at < :lock_expired_before
                )
            )
            {pipe_clause}
            ORDER BY priority ASC, scheduled_at ASC, created_at ASC
            LIMIT :batch_size
            FOR UPDATE SKIP LOCKED
            """
        )
        ids = [row[0] for row in self._db.execute(sql, params).fetchall()]
        if not ids:
            return []
        rows = (
            self._db.query(ElfisDocumentProcessingJob)
            .filter(ElfisDocumentProcessingJob.id.in_(ids))
            .all()
        )
        claimed: list[ElfisDocumentProcessingJob] = []
        for row in rows:
            self._mark_running(row, worker_id=worker_id, now=now, lease_seconds=lease_seconds)
            claimed.append(row)
        self._db.commit()
        for row in claimed:
            self._db.refresh(row)
        return claimed

    def _claim_sqlite(
        self,
        *,
        worker_id: str,
        batch_size: int,
        now: datetime,
        lock_expired_before: datetime,
        lease_seconds: int,
        pipeline_key: str | None,
    ) -> list[ElfisDocumentProcessingJob]:
        q = self._db.query(ElfisDocumentProcessingJob).filter(
            or_(
                and_(
                    ElfisDocumentProcessingJob.status.in_(
                        [ProcessingJobStatus.QUEUED.value, ProcessingJobStatus.RETRYING.value]
                    ),
                    ElfisDocumentProcessingJob.scheduled_at <= now,
                ),
                and_(
                    ElfisDocumentProcessingJob.status == ProcessingJobStatus.RUNNING.value,
                    or_(
                        and_(
                            ElfisDocumentProcessingJob.locked_until.isnot(None),
                            ElfisDocumentProcessingJob.locked_until < now,
                        ),
                        and_(
                            ElfisDocumentProcessingJob.heartbeat_at.isnot(None),
                            ElfisDocumentProcessingJob.heartbeat_at < lock_expired_before,
                        ),
                    ),
                ),
            )
        )
        if pipeline_key:
            q = q.filter(ElfisDocumentProcessingJob.pipeline_key == pipeline_key)
        rows = (
            q.order_by(
                ElfisDocumentProcessingJob.priority.asc(),
                ElfisDocumentProcessingJob.scheduled_at.asc(),
                ElfisDocumentProcessingJob.created_at.asc(),
            )
            .limit(batch_size)
            .all()
        )
        claimed: list[ElfisDocumentProcessingJob] = []
        for row in rows:
            self._mark_running(row, worker_id=worker_id, now=now, lease_seconds=lease_seconds)
            claimed.append(row)
        self._db.commit()
        for row in claimed:
            self._db.refresh(row)
        return claimed

    def _mark_running(
        self,
        job: ElfisDocumentProcessingJob,
        *,
        worker_id: str,
        now: datetime,
        lease_seconds: int,
    ) -> None:
        recovered = job.status == ProcessingJobStatus.RUNNING.value and (
            (job.locked_until is not None and _naive_utc(job.locked_until) < now)
            or (
                job.heartbeat_at is not None
                and _naive_utc(job.heartbeat_at) < now - timedelta(seconds=lease_seconds)
            )
        )
        job.status = ProcessingJobStatus.RUNNING.value
        job.locked_at = now
        job.locked_by = worker_id[:128]
        job.locked_until = now + timedelta(seconds=lease_seconds)
        job.heartbeat_at = now
        job.started_at = job.started_at or now
        job.updated_at = now
        if recovered:
            job._lease_recovered = True  # type: ignore[attr-defined]
            from app.document_processing import metrics as dp_metrics

            dp_metrics.incr("leases_recovered")

    def heartbeat(self, job: ElfisDocumentProcessingJob, *, lease_seconds: int) -> None:
        now = datetime.utcnow()
        job.heartbeat_at = now
        job.locked_until = now + timedelta(seconds=lease_seconds)
        job.updated_at = now
        self._db.commit()

    def count_by_status(self) -> dict[str, int]:
        from sqlalchemy import func

        rows = (
            self._db.query(ElfisDocumentProcessingJob.status, func.count(ElfisDocumentProcessingJob.id))
            .group_by(ElfisDocumentProcessingJob.status)
            .all()
        )
        return {str(s): int(c) for s, c in rows}
