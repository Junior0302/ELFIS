"""CONC-003 — Quota restant = 1 : une seule consommation (UPDATE conditionnel)."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.billing import billing_models  # noqa: F401
from app.billing.billing_exceptions import QuotaExceededError
from app.billing.billing_models import ElfisQuota, ElfisUsageCounter
from app.billing.billing_types import QuotaPeriods
from app.billing.quota_service import QuotaService
from app.config import settings
from app.database import Base
from app.models_saas import Organization


def test_conc_003_quota_atomicity(monkeypatch):
    monkeypatch.setattr(settings, "elfis_billing_enforce_quotas", True)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Organization(id=1, name="Quota Conc"))
    now = datetime.utcnow()
    start = datetime(now.year, now.month, 1)
    end = datetime(now.year, now.month, 28, 23, 59, 59)
    db.add(
        ElfisQuota(
            id=str(uuid4()),
            quota_id=str(uuid4()),
            organization_id=1,
            quota_code="emails.sent.month",
            limit_value=1,
            period=QuotaPeriods.MONTH,
            hard_limit=True,
            current_period_started_at=start,
            current_period_ends_at=end,
        )
    )
    usage_id = str(uuid4())
    db.add(
        ElfisUsageCounter(
            id=usage_id,
            usage_counter_id=str(uuid4()),
            organization_id=1,
            usage_code="emails.sent",
            period_started_at=start,
            period_ends_at=end,
            used_value=0,
            reserved_value=0,
        )
    )
    db.commit()

    s1, s2 = Session(), Session()
    try:
        QuotaService(s1).consume(1, "emails.sent.month", 1)
        s1.commit()
        denied = False
        try:
            QuotaService(s2).consume(1, "emails.sent.month", 1)
            s2.commit()
        except QuotaExceededError:
            s2.rollback()
            denied = True
        assert denied is True
        used = Session().get(ElfisUsageCounter, usage_id)
        assert int(used.used_value) == 1
    finally:
        s1.close()
        s2.close()
        db.close()
