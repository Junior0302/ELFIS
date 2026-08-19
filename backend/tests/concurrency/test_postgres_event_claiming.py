"""RC1 — Event claiming PostgreSQL FOR UPDATE SKIP LOCKED."""

from __future__ import annotations

import threading
from datetime import datetime
from uuid import uuid4

from app.events.event_models import ElfisEvent
from app.events.event_repository import EventRepository
from app.events.event_schemas import EventStatus
from tests.concurrency.postgres_helpers import make_pg_session_factory, require_postgres


def test_postgres_event_claiming_skip_locked_unique():
    require_postgres()
    Session, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"

    import inspect
    from app.events.event_repository import EventRepository as ER

    src = inspect.getsource(ER._claim_events_postgres)
    assert "FOR UPDATE SKIP LOCKED" in src

    db = Session()
    now = datetime.utcnow()
    org_id = 910001
    event_ids: list[str] = []
    try:
        for i in range(100):
            eid = str(uuid4())
            event_ids.append(eid)
            db.add(
                ElfisEvent(
                    id=str(uuid4()),
                    event_id=eid,
                    event_name="rc1.probe.v1",
                    event_version=1,
                    organization_id=org_id,
                    payload={"i": i},
                    metadata_json={"rc1": True},
                    status=EventStatus.pending.value,
                    available_at=now,
                    created_at=now,
                    updated_at=now,
                    priority=1,
                )
            )
        db.commit()
    finally:
        db.close()

    claimed: list[str] = []
    lock = threading.Lock()
    errors: list[str] = []
    target = set(event_ids)

    def worker(wid: str) -> None:
        local = Session()
        try:
            idle = 0
            while idle < 5:
                batch = EventRepository(local).claim_events(
                    worker_id=wid,
                    batch_size=10,
                    lock_timeout_seconds=60,
                )
                # claim_events commit déjà
                ours = [e for e in batch if e.event_id in target]
                if ours:
                    idle = 0
                    with lock:
                        for e in ours:
                            claimed.append(e.event_id)
                else:
                    idle += 1
                with lock:
                    if len(set(claimed)) >= 100:
                        break
        except Exception as exc:
            with lock:
                errors.append(f"{wid}:{type(exc).__name__}")
        finally:
            local.close()

    threads = [threading.Thread(target=worker, args=(f"rc1-ew-{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=90)

    assert not errors, errors
    assert len(set(claimed)) == 100, f"claimed={len(set(claimed))}"
    assert set(claimed) == target

    db = Session()
    try:
        db.query(ElfisEvent).filter(ElfisEvent.event_id.in_(event_ids)).delete(
            synchronize_session=False
        )
        db.commit()
    finally:
        db.close()
