from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models_fiscal import FiscalPeriodRecord
from app.models_saas import Organization


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_fiscal_period_unique_kind():
    db = _session()
    db.add(Organization(id=1, name="Org"))
    db.add(
        FiscalPeriodRecord(
            organization_id=1,
            period_key="2026-07",
            kind="period_close",
            status="closed",
            closed_at=datetime.utcnow(),
        )
    )
    db.commit()
    rows = db.query(FiscalPeriodRecord).filter_by(organization_id=1).all()
    assert len(rows) == 1
    assert rows[0].kind == "period_close"
