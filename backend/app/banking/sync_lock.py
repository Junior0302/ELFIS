"""Verrou distribué de synchronisation bancaire (BANK-3.1).

``pg_try_advisory_lock`` est un lock de SESSION PostgreSQL : il appartient à
la connexion physique, pas à l'objet ``sqlalchemy.orm.Session``.

Après ``Session.commit()``, SQLAlchemy peut rendre la connexion au pool et en
checkout une autre. Un lock pris via ``session.execute`` pourrait alors :

- rester coincé sur une connexion poolée (fuite)
- être libéré sur une autre connexion (no-op)

Correction : checkout d'une ``Connection`` SQLAlchemy dédiée, conservée ouverte
jusqu'à ``pg_advisory_unlock`` puis ``close()``. Les commits métier de la
Session n'y touchent pas.

SQLite : verrou process-local, sans garantie multi-instance.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# int4 namespace dédié — hors plage des locks jobs/events.
ADVISORY_LOCK_NAMESPACE = 31001
ADVISORY_LOCK_POLL_SECONDS = 0.1


def _bind_engine(db: Session) -> Engine:
    bind = db.get_bind()
    engine = getattr(bind, "engine", bind)
    if not isinstance(engine, Engine):
        raise RuntimeError("Impossible de résoudre l'Engine SQLAlchemy pour le verrou banking.")
    return engine


@dataclass
class BankingSyncLock:
    """Jeton de verrou. ``lock_connection`` doit rester ouverte jusqu'à release."""

    organization_id: int
    connection_id: int
    dialect: str
    lock_connection: Connection | None = None
    backend_pid: int | None = None
    sqlite_key: tuple[int, int] | None = None
    released: bool = field(default=False, repr=False)


_SQLITE_LOCKS_GUARD = threading.Lock()
_SQLITE_LOCKS: dict[tuple[int, int], threading.Lock] = {}
_SQLITE_HELD: dict[tuple[int, int], threading.Lock] = {}


def _sqlite_lock_key(db: Session, connection_id: int) -> tuple[int, int]:
    return (id(_bind_engine(db)), int(connection_id))


def _sqlite_lock_for(db: Session, connection_id: int) -> threading.Lock:
    key = _sqlite_lock_key(db, connection_id)
    with _SQLITE_LOCKS_GUARD:
        lock = _SQLITE_LOCKS.setdefault(key, threading.Lock())
    return lock


def lock_backend_pid(lock: BankingSyncLock) -> int | None:
    """PID PostgreSQL de la connexion pinée (test / observabilité)."""
    conn = lock.lock_connection
    if conn is None or conn.closed:
        return None
    return int(conn.execute(text("SELECT pg_backend_pid()")).scalar())


def lock_is_held(lock: BankingSyncLock) -> bool:
    """True si cette connexion physique détient encore l'advisory lock."""
    conn = lock.lock_connection
    if conn is None or conn.closed:
        return False
    held = conn.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pg_locks
                WHERE locktype = 'advisory'
                  AND classid = :ns
                  AND objid = :cid
                  AND pid = pg_backend_pid()
            )
            """
        ),
        {"ns": ADVISORY_LOCK_NAMESPACE, "cid": int(lock.connection_id)},
    ).scalar()
    return bool(held)


def acquire_connection_sync_lock(
    db: Session,
    *,
    organization_id: int,
    connection_id: int,
    wait_seconds: float,
) -> BankingSyncLock | None:
    """Tente d'acquérir le verrou. None si contention / timeout."""
    dialect = db.get_bind().dialect.name
    deadline = time.monotonic() + max(0.0, wait_seconds)
    if dialect == "postgresql":
        return _acquire_postgres(
            db,
            organization_id=organization_id,
            connection_id=connection_id,
            deadline=deadline,
        )
    lock = _sqlite_lock_for(db, connection_id)
    remaining = max(0.0, deadline - time.monotonic())
    if lock.acquire(timeout=remaining if remaining > 0 else 0):
        key = _sqlite_lock_key(db, connection_id)
        _SQLITE_HELD[key] = lock
        logger.info(
            "banking_sync_lock_acquired",
            extra={
                "organization_id": organization_id,
                "connection_id": connection_id,
                "backend": dialect,
            },
        )
        return BankingSyncLock(
            organization_id=organization_id,
            connection_id=connection_id,
            dialect=dialect,
            sqlite_key=key,
        )
    logger.info(
        "banking_sync_lock_contention",
        extra={
            "organization_id": organization_id,
            "connection_id": connection_id,
            "backend": dialect,
        },
    )
    return None


def _acquire_postgres(
    db: Session,
    *,
    organization_id: int,
    connection_id: int,
    deadline: float,
) -> BankingSyncLock | None:
    engine = _bind_engine(db)
    lock_conn = engine.connect()
    try:
        while True:
            got = lock_conn.execute(
                text("SELECT pg_try_advisory_lock(:ns, :cid)"),
                {"ns": ADVISORY_LOCK_NAMESPACE, "cid": int(connection_id)},
            ).scalar()
            if got:
                pid = int(lock_conn.execute(text("SELECT pg_backend_pid()")).scalar())
                logger.info(
                    "banking_sync_lock_acquired",
                    extra={
                        "organization_id": organization_id,
                        "connection_id": connection_id,
                        "backend": "postgresql",
                        "backend_pid": pid,
                    },
                )
                return BankingSyncLock(
                    organization_id=organization_id,
                    connection_id=connection_id,
                    dialect="postgresql",
                    lock_connection=lock_conn,
                    backend_pid=pid,
                )
            if time.monotonic() >= deadline:
                logger.info(
                    "banking_sync_lock_contention",
                    extra={
                        "organization_id": organization_id,
                        "connection_id": connection_id,
                        "backend": "postgresql",
                    },
                )
                lock_conn.close()
                return None
            time.sleep(ADVISORY_LOCK_POLL_SECONDS)
    except Exception:
        lock_conn.close()
        raise


def release_connection_sync_lock(lock: BankingSyncLock | None) -> None:
    if lock is None or lock.released:
        return
    lock.released = True
    if lock.dialect == "postgresql" and lock.lock_connection is not None:
        _release_postgres(lock)
        return
    if lock.sqlite_key is not None:
        held = _SQLITE_HELD.pop(lock.sqlite_key, None)
        if held is not None and held.locked():
            held.release()


def _release_postgres(lock: BankingSyncLock) -> None:
    conn = lock.lock_connection
    if conn is None:
        return
    unlocked = False
    try:
        if not conn.closed:
            conn.execute(
                text("SELECT pg_advisory_unlock(:ns, :cid)"),
                {"ns": ADVISORY_LOCK_NAMESPACE, "cid": int(lock.connection_id)},
            )
            unlocked = True
    except Exception:
        logger.warning(
            "banking_sync_lock_release_failed",
            extra={
                "organization_id": lock.organization_id,
                "connection_id": lock.connection_id,
                "backend_pid": lock.backend_pid,
            },
        )
    finally:
        try:
            if not unlocked and not conn.closed:
                # Ne jamais rendre au pool une connexion qui détiendrait encore le lock.
                conn.invalidate()
        finally:
            conn.close()
            lock.lock_connection = None
