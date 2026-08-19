"""Tests des tendances (mensuelle / hebdomadaire / annuelle + comparaisons)."""

from __future__ import annotations

from app.financial.engine import MONTHS_WINDOW, WEEKS_WINDOW, YEARS_WINDOW, FinancialEngine

from tests.financial.helpers import make_financial_db, seed_finance_data, seed_org


def _trends(db, org_id):
    return FinancialEngine(db, use_cache=False, publish_events=False).trends(org_id)


def test_trends_have_three_horizons_with_expected_windows():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    trends = _trends(db, org.id)

    assert set(trends.keys()) == {"monthly", "weekly", "yearly"}
    assert len(trends["monthly"]["points"]) == MONTHS_WINDOW
    assert len(trends["weekly"]["points"]) == WEEKS_WINDOW
    assert len(trends["yearly"]["points"]) == YEARS_WINDOW


def test_monthly_comparison_math():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    comparison = _trends(db, org.id)["monthly"]["comparison"]

    assert comparison["revenue"]["previous"] == 3000.0
    assert comparison["revenue"]["delta"] == 8000.0
    assert comparison["revenue"]["delta_pct"] == 266.7
    assert comparison["revenue"]["direction"] == "up"
    assert comparison["expenses"]["delta"] == 1000.0  # 2 500 vs 1 500
    assert comparison["result"]["delta"] == 7000.0  # 8 500 vs 1 500


def test_trend_points_structure_is_homogeneous():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    trends = _trends(db, org.id)
    for horizon in ("monthly", "weekly", "yearly"):
        for point in trends[horizon]["points"]:
            assert set(point.keys()) == {"period", "label", "revenue", "expenses", "result"}
            assert point["result"] == round(point["revenue"] - point["expenses"], 2)


def test_yearly_totals_accumulate_all_activity():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    yearly = _trends(db, org.id)["yearly"]["points"]
    current_year = yearly[-1]

    # tout le jeu de données est sur l'année courante (sauf bascule de mois en janvier)
    total_revenue = sum(p["revenue"] for p in yearly)
    total_expenses = sum(p["expenses"] for p in yearly)
    assert total_revenue == 14000.0
    assert total_expenses == 4000.0
    assert current_year["revenue"] >= 11000.0


def test_trends_empty_org_all_zero():
    db = make_financial_db()
    org = seed_org(db)

    trends = _trends(db, org.id)
    assert all(p["revenue"] == 0.0 for p in trends["monthly"]["points"])
    assert trends["monthly"]["comparison"]["revenue"]["direction"] == "flat"
