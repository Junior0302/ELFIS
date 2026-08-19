"""Génération Universal Document ID — DOC-YYYY-XXXXXXXX."""

from __future__ import annotations

import logging
import re
import threading
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.document_intake.models import ElfisDocumentDocIdCounter

logger = logging.getLogger(__name__)

DOC_ID_RE = re.compile(r"^DOC-\d{4}-\d{8}$")
MAX_RETRIES = 8
_ALLOC_LOCK = threading.Lock()


def is_valid_universal_document_id(value: str | None) -> bool:
    return bool(value and DOC_ID_RE.match(value))


def allocate_universal_document_id(db: Session, *, year: int | None = None) -> str:
    """Alloue un DOC ID via compteur transactionnel (pas MAX+1).

    - PostgreSQL : SELECT … FOR UPDATE
    - Verrou process-local : protège la concurrence in-process (SQLite / workers)
    """
    y = year or datetime.utcnow().year
    last_err: Exception | None = None
    for _attempt in range(MAX_RETRIES):
        try:
            with _ALLOC_LOCK:
                nested = db.begin_nested()
                try:
                    row = (
                        db.query(ElfisDocumentDocIdCounter)
                        .filter(ElfisDocumentDocIdCounter.year == y)
                        .with_for_update()
                        .first()
                    )
                    if row is None:
                        row = ElfisDocumentDocIdCounter(year=y, last_value=0)
                        db.add(row)
                        db.flush()
                    row.last_value = int(row.last_value or 0) + 1
                    row.updated_at = datetime.utcnow()
                    db.flush()
                    doc_id = f"DOC-{y}-{int(row.last_value):08d}"
                    nested.commit()
                    logger.info(
                        "universal_document_id_allocated",
                        extra={
                            "universal_document_id": doc_id,
                            "operation": "allocate_doc_id",
                        },
                    )
                    return doc_id
                except IntegrityError as exc:
                    nested.rollback()
                    last_err = exc
        except IntegrityError as exc:
            last_err = exc
            continue
    raise RuntimeError(f"DOC ID allocation failed after retries: {last_err}")
