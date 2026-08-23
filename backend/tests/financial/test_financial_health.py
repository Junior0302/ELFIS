"""Tests du Financial Health Score (0-100, barème documenté)."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.financial.engine import FinancialEngine
from app.financial.health import compute_health_score

from tests.financial.helpers import TODAY, make_financial_db, seed_finance_data, seed_org


def _health(db, org_id):
    snap = FinancialEngine(db, use_cache=False, publish_events=False).snapshot(
        org_id, today=TODAY
    )
    return compute_health_score(snap)


def test_score_is_bounded_and_graded():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    health = _health(db, org.id)

    assert health["state"] == "active"
    assert 0 <= health["score"] <= 100
    assert health["grade"] in {"A", "B", "C", "D", "E"}
    assert health["score"] == round(sum(c["score"] for c in health["components"]), 1)


def test_components_and_weights_documented():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    components = {c["id"]: c for c in _health(db, org.id)["components"]}

    assert set(components.keys()) == {"treasury", "overdue", "revenue", "expenses", "sync"}
    assert components["treasury"]["max_score"] == 30.0
    assert components["overdue"]["max_score"] == 20.0
    assert components["revenue"]["max_score"] == 20.0
    assert components["expenses"]["max_score"] == 15.0
    assert components["sync"]["max_score"] == 15.0
    assert sum(c["max_score"] for c in components.values()) == 100.0
    for c in components.values():
        assert 0.0 <= c["score"] <= c["max_score"]


def test_nominal_dataset_scores_high():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    health = _health(db, org.id)
    components = {c["id"]: c for c in health["components"]}

    # 6 mois d'autonomie → plein score trésorerie ; sync fraîche → plein score
    assert components["treasury"]["score"] == 30.0
    assert components["sync"]["score"] == 15.0
    assert components["revenue"]["score"] == 20.0  # CA en croissance
    assert health["grade"] in {"A", "B"}


def test_degraded_finances_lower_the_score():
    db = make_financial_db()
    org = seed_org(db)
    data = seed_finance_data(db, org.id)

    baseline = _health(db, org.id)["score"]

    data["account"].balance = 500.0  # trésorerie quasi nulle
    data["connection"].last_sync_at = datetime.utcnow() - timedelta(days=30)  # sync obsolète
    db.commit()

    degraded = _health(db, org.id)
    assert degraded["score"] < baseline
    components = {c["id"]: c for c in degraded["components"]}
    assert components["sync"]["score"] == 0.0
    assert components["treasury"]["score"] < 10.0


def test_mixed_currencies_do_not_score_treasury_as_empty():
    from app.models import BankAccount

    db = make_financial_db()
    org = seed_org(db)
    db.add(BankAccount(organization_id=org.id, currency="EUR", balance=100.0, connected=True))
    db.add(BankAccount(organization_id=org.id, currency="USD", balance=200.0, connected=True))
    db.commit()

    health = _health(db, org.id)
    components = {c["id"]: c for c in health["components"]}
    assert components["treasury"]["score"] == 15.0
    assert "nulle" not in components["treasury"]["detail"].lower()
    assert "négative" not in components["treasury"]["detail"].lower()
    assert "devises" in components["treasury"]["detail"].lower()


def test_setup_state_without_data():
    db = make_financial_db()
    org = seed_org(db)

    health = _health(db, org.id)

    assert health["state"] == "setup"
    assert health["score"] is None
    assert health["grade"] is None
    assert health["message"]
