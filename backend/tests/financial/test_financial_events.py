"""Tests des événements financial.* publiés pour l'AI Financial Assistant."""

from __future__ import annotations

from app.events.event_models import ElfisEvent
from app.financial.engine import FinancialEngine

from tests.financial.helpers import make_financial_db, seed_finance_data, seed_org


def _event_names(db, org_id) -> list[str]:
    rows = (
        db.query(ElfisEvent)
        .filter(
            ElfisEvent.organization_id == org_id,
            ElfisEvent.event_name.like("financial.%"),
        )
        .all()
    )
    return [r.event_name for r in rows]


def test_snapshot_publishes_kpi_health_and_alert_events():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    FinancialEngine(db).snapshot(org.id)

    names = _event_names(db, org.id)
    assert "financial.kpi.updated.v1" in names
    assert "financial.health.updated.v1" in names
    assert "financial.alert.created.v1" in names


def test_events_not_republished_when_values_unchanged():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    engine = FinancialEngine(db)
    engine.snapshot(org.id)
    count_first = len(_event_names(db, org.id))

    engine.snapshot(org.id, refresh=True)  # recalcul, mêmes valeurs
    assert len(_event_names(db, org.id)) == count_first


def test_events_republished_on_change():
    db = make_financial_db()
    org = seed_org(db)
    data = seed_finance_data(db, org.id)

    engine = FinancialEngine(db)
    engine.snapshot(org.id)
    kpi_events_before = _event_names(db, org.id).count("financial.kpi.updated.v1")

    data["account"].balance = 300.0  # change trésorerie, statut, alertes
    db.commit()
    engine.snapshot(org.id, refresh=True)

    names = _event_names(db, org.id)
    assert names.count("financial.kpi.updated.v1") == kpi_events_before + 1


def test_alert_event_payload_is_normalized():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    FinancialEngine(db).snapshot(org.id)

    row = (
        db.query(ElfisEvent)
        .filter(
            ElfisEvent.organization_id == org.id,
            ElfisEvent.event_name == "financial.alert.created.v1",
        )
        .first()
    )
    assert row is not None
    assert {"code", "severity", "title", "message"}.issubset(row.payload.keys())
