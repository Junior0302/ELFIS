"""CONC-002 — Events claimés une seule fois."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.events import event_models  # noqa: F401
from app.events.event_models import ElfisEvent
from app.events.event_repository import EventRepository
from app.events.event_schemas import EventStatus
from app.jobs import job_models  # noqa: F401


def test_conc_002_events_claimed_once():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    now = datetime.utcnow()
    for i in range(5):
        db.add(
            ElfisEvent(
                id=str(uuid4()),
                event_id=str(uuid4()),
                event_name="system.health.v1",
                event_version=1,
                organization_id=1,
                payload={"i": i},
                metadata_json={},
                status=EventStatus.pending.value,
                available_at=now,
                created_at=now,
                updated_at=now,
            )
        )
    db.commit()

    s1, s2 = Session(), Session()
    try:
        a = EventRepository(s1).claim_events(
            worker_id="e-a", batch_size=10, lock_timeout_seconds=60
        )
        s1.commit()
        b = EventRepository(s2).claim_events(
            worker_id="e-b", batch_size=10, lock_timeout_seconds=60
        )
        s2.commit()
        ids_a = {e.event_id for e in a}
        ids_b = {e.event_id for e in b}
        assert ids_a.isdisjoint(ids_b)
        assert len(ids_a) + len(ids_b) == 5
    finally:
        s1.close()
        s2.close()
        db.close()
