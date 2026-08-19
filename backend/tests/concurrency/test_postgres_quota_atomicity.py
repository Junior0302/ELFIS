"""RC1-PG — Quota atomique sous PostgreSQL (BLOCKER si dépassement)."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete

from app.billing.billing_exceptions import QuotaExceededError
from app.billing.billing_models import ElfisQuota, ElfisUsageCounter
from app.billing.billing_types import QuotaPeriods
from app.billing.quota_service import QuotaService
from app.config import settings
from app.models_saas import Organization, OrganizationMember
from tests.concurrency.postgres_helpers import make_pg_session_factory, require_postgres


def test_postgres_quota_atomicity_limit_one(monkeypatch):
    """Deux connexions PG indépendantes — une seule réservation, used+reserved <= 1."""
    require_postgres()
    monkeypatch.setattr(settings, "elfis_billing_enforce_quotas", True)
    Session, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"

    db = Session()
    from calendar import monthrange

    usage_pk = str(uuid4())
    quota_pk = str(uuid4())
    quota_code = "emails.sent.month"
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = datetime(now.year, now.month, 1)
    last = monthrange(now.year, now.month)[1]
    end = datetime(now.year, now.month, last, 23, 59, 59)
    org_id: int
    try:
        org = Organization(name=f"RC1 Quota Org {uuid4().hex[:6]}")
        db.add(org)
        db.flush()
        org_id = int(org.id)

        db.add(
            ElfisQuota(
                id=quota_pk,
                quota_id=str(uuid4()),
                organization_id=org_id,
                quota_code=quota_code,
                limit_value=1,
                period=QuotaPeriods.MONTH,
                hard_limit=True,
                current_period_started_at=start,
                current_period_ends_at=end,
            )
        )
        db.add(
            ElfisUsageCounter(
                id=usage_pk,
                usage_counter_id=str(uuid4()),
                organization_id=org_id,
                usage_code="emails.sent",
                period_started_at=start,
                period_ends_at=end,
                used_value=0,
                reserved_value=0,
            )
        )
        db.commit()
    finally:
        db.close()

    results: list[str] = []
    barrier = threading.Barrier(2)

    def attempt(tag: str) -> None:
        s = Session()
        try:
            barrier.wait(timeout=10)
            QuotaService(s).consume(org_id, quota_code, 1)
            s.commit()
            results.append(f"{tag}:ok")
        except QuotaExceededError:
            s.rollback()
            results.append(f"{tag}:denied")
        except Exception as exc:
            s.rollback()
            results.append(f"{tag}:err:{type(exc).__name__}")
        finally:
            s.close()

    for round_i in range(3):
        results.clear()
        s = Session()
        try:
            row = s.get(ElfisUsageCounter, usage_pk)
            assert row is not None
            row.used_value = 0
            row.reserved_value = 0
            s.commit()
        finally:
            s.close()

        t1 = threading.Thread(target=attempt, args=(f"a{round_i}",))
        t2 = threading.Thread(target=attempt, args=(f"b{round_i}",))
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)

        oks = [r for r in results if r.endswith(":ok")]
        denied = [r for r in results if r.endswith(":denied")]
        assert len(oks) == 1, results
        assert len(denied) == 1, results

        s = Session()
        try:
            row = s.get(ElfisUsageCounter, usage_pk)
            assert int(row.used_value) + int(row.reserved_value) == 1
            assert int(row.used_value) >= 0
            assert int(row.reserved_value) >= 0
        finally:
            s.close()

    # Nettoyage ordonné (FK respectées)
    s = Session()
    try:
        s.execute(delete(ElfisUsageCounter).where(ElfisUsageCounter.id == usage_pk))
        s.execute(delete(ElfisQuota).where(ElfisQuota.id == quota_pk))
        s.execute(
            delete(OrganizationMember).where(OrganizationMember.organization_id == org_id)
        )
        s.execute(delete(Organization).where(Organization.id == org_id))
        s.commit()
    finally:
        s.close()
