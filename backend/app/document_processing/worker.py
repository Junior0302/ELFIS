"""Worker Document Processing — hors processus HTTP."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import socket
import time
import uuid
from typing import Any

from app.audit.audit_logger import AuditLogger
from app.config import settings
from app.database import SessionLocal
from app.document_processing.orchestrator import DocumentProcessingOrchestrator
from app.document_processing.repository import DocumentProcessingRepository

logger = logging.getLogger(__name__)

_STOP = False


def default_worker_id() -> str:
    return f"dp-{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"[:128]


def _handle_signal(signum, frame) -> None:  # noqa: ANN001
    global _STOP
    _STOP = True
    logger.info("document_processing_worker_stop_requested", extra={"signal": signum})


async def process_once(
    *,
    worker_id: str | None = None,
    max_jobs: int = 1,
    pipeline: str | None = None,
) -> int:
    wid = worker_id or default_worker_id()
    lease = int(getattr(settings, "document_processing_lease_seconds", 60) or 60)
    db = SessionLocal()
    processed = 0
    try:
        audit = AuditLogger(db)
        repo = DocumentProcessingRepository(db)
        orch = DocumentProcessingOrchestrator(db, audit_logger=audit)
        jobs = repo.claim_jobs(
            worker_id=wid,
            batch_size=max(1, min(max_jobs, 20)),
            lease_seconds=lease,
            pipeline_key=pipeline,
        )
        for job in jobs:
            if getattr(job, "_lease_recovered", False):
                try:
                    audit.record_document_processing_job_lease_recovered(
                        job_id=job.id,
                        document_id=job.document_id,
                        version_id=job.document_version_id,
                        organization_id=job.organization_id,
                        pipeline_key=job.pipeline_key,
                        worker_id=wid,
                    )
                except Exception:
                    logger.debug("lease_recovered_audit_failed", exc_info=True)
            await orch.run_job(job.id, worker_id=wid)
            processed += 1
        return processed
    finally:
        db.close()


def run_worker_loop(
    *,
    once: bool = False,
    poll_seconds: float | None = None,
    worker_id: str | None = None,
    max_jobs: int = 5,
    pipeline: str | None = None,
) -> int:
    global _STOP
    _STOP = False
    try:
        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)
    except Exception:
        pass

    wid = worker_id or default_worker_id()
    poll = float(
        poll_seconds
        if poll_seconds is not None
        else getattr(settings, "document_processing_worker_poll_seconds", 2) or 2
    )
    total = 0
    logger.info("document_processing_worker_start", extra={"worker_id": wid, "once": once})
    while not _STOP:
        n = asyncio.run(process_once(worker_id=wid, max_jobs=max_jobs, pipeline=pipeline))
        total += n
        if once:
            break
        if n == 0:
            time.sleep(max(0.2, poll))
    logger.info("document_processing_worker_stop", extra={"worker_id": wid, "processed": total})
    return total
